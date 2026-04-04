import base64
import json
import os
import sys
import time
from decimal import Decimal
from functools import lru_cache
from typing import Dict, Optional, Tuple

import boto3
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.logging import correlation_paths
from botocore.exceptions import ClientError

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.append(BACKEND_ROOT)

from common.dynamodb_helper import ImageJobService, UsageService, UserService  # noqa: E402

logger = Logger()
metrics = Metrics()


class _NoOpTracer:
    @staticmethod
    def capture_lambda_handler(handler=None, **_kwargs):
        if handler is None:
            return lambda inner: inner
        return handler

    @staticmethod
    def capture_method(handler=None, **_kwargs):
        if handler is None:
            return lambda inner: inner
        return handler


def _create_tracer():
    trace_disabled = os.environ.get("POWERTOOLS_TRACE_DISABLED", "").lower() in {
        "1",
        "true",
        "yes",
    }
    if trace_disabled:
        return _NoOpTracer()

    try:
        return Tracer()
    except PermissionError:
        logger.warning(
            "Tracing disabled because X-Ray emitter could not be initialized"
        )
        return _NoOpTracer()


tracer = _create_tracer()


def _client_kwargs():
    kwargs = {}
    endpoint_url = os.environ.get("AWS_ENDPOINT_URL")
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
    return kwargs


@lru_cache(maxsize=1)
def _get_sqs_client():
    return boto3.client("sqs", **_client_kwargs())


@lru_cache(maxsize=1)
def _get_s3_client():
    return boto3.client("s3", **_client_kwargs())


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _get_environment() -> str:
    return os.environ.get("ENVIRONMENT", "unknown")


def _get_sqs_queue_url() -> str:
    return _require_env("SQS_QUEUE_URL")


def _get_upload_bucket() -> str:
    return _require_env("UPLOAD_BUCKET")


def _get_result_bucket() -> str:
    return _require_env("RESULT_BUCKET")


def _get_job_download_expiry_seconds() -> int:
    return int(os.environ.get("JOB_DOWNLOAD_EXPIRY_SECONDS", "86400"))


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_HTTP)
@tracer.capture_lambda_handler
@metrics.log_metrics
def lambda_handler(event, context):
    request_id = context.aws_request_id if context else "local-request"
    logger.append_keys(requestId=request_id)

    try:
        http_method = event.get("requestContext", {}).get("http", {}).get(
            "method"
        ) or event.get("requestContext", {}).get("httpMethod")
        raw_path = event.get("rawPath") or event.get("path", "")

        stage = event.get("requestContext", {}).get("stage", "")
        if stage and raw_path.startswith(f"/{stage}/"):
            raw_path = raw_path[len(f"/{stage}") :]

        logger.info(
            "Processing request", extra={"method": http_method, "path": raw_path}
        )

        if http_method == "OPTIONS":
            return cors_response(200, {})
        if http_method == "GET" and raw_path == "/healthz":
            return handle_healthz()
        if http_method == "POST" and raw_path == "/generate":
            return handle_generate_image(event)
        if http_method == "GET" and raw_path.startswith("/jobs/"):
            if raw_path.endswith("/download"):
                return handle_download_image(event)
            return handle_get_job(event)
        if http_method == "GET" and raw_path == "/user/me":
            return handle_get_user_info(event)
        if http_method == "GET" and raw_path == "/user/jobs":
            return handle_get_user_jobs(event)
        return cors_response(404, {"error": "Not Found"})
    except Exception as error:
        logger.exception("Unhandled API error", extra={"error": str(error)})
        return cors_response(500, {"error": "Internal server error"})


@tracer.capture_method
def handle_generate_image(event):
    start_time = time.time()
    job_id = None
    quota_reserved = False

    try:
        user_id = extract_user_id(event)
        if not user_id:
            return cors_response(401, {"error": "Unauthorized: User ID not found"})

        logger.append_keys(userId=user_id)
        body = parse_request_body(event)
        if not body:
            return cors_response(400, {"error": "Invalid request body"})

        file_key = body.get("fileKey")
        prompt = body.get("prompt", "")
        style = body.get("style", "formal_interview")

        validation_error = validate_generation_request(user_id, file_key, prompt)
        if validation_error:
            return cors_response(400, {"error": validation_error})

        upload_bucket = _get_upload_bucket()
        if not verify_s3_file_exists(upload_bucket, file_key):
            return cors_response(404, {"error": "Uploaded file not found in S3"})

        user = UserService.get_user(user_id)
        if not user:
            user = UserService.create_or_update_user(extract_user_data(event))

        quota_allowed, current_usage, remaining_quota = UsageService.try_consume_quota(
            user_id
        )
        if not quota_allowed:
            return cors_response(
                429,
                {
                    "error": "Daily quota exceeded",
                    "remainingQuota": remaining_quota,
                    "message": "You have reached your daily limit. Please try again tomorrow.",
                },
            )

        quota_reserved = True
        s3_uri = f"s3://{upload_bucket}/{file_key}"
        job_id = ImageJobService.create_job(
            user_id=user_id, style=style, input_url=s3_uri, prompt=prompt
        )

        sqs_response = _get_sqs_client().send_message(
            QueueUrl=_get_sqs_queue_url(),
            MessageBody=json.dumps(
                {
                    "jobId": job_id,
                    "userId": user_id,
                    "s3Uri": s3_uri,
                    "prompt": prompt,
                    "style": style,
                    "createdAt": int(time.time()),
                }
            ),
            MessageAttributes={
                "userId": {"StringValue": user_id, "DataType": "String"},
                "jobId": {"StringValue": job_id, "DataType": "String"},
            },
        )

        ImageJobService.update_job_status(
            job_id=job_id,
            status="queued",
            metadata={
                "sqsMessageId": sqs_response["MessageId"],
                "usageCount": current_usage,
            },
        )

        logger.info(
            "Job queued",
            extra={
                "jobId": job_id,
                "style": style,
                "remainingQuota": remaining_quota,
                "processingMs": int((time.time() - start_time) * 1000),
            },
        )

        return cors_response(
            200,
            {
                "jobId": job_id,
                "status": "queued",
                "remainingQuota": remaining_quota,
                "message": "Image generation request has been queued successfully",
            },
        )
    except Exception as error:
        logger.exception(
            "Failed to queue job", extra={"jobId": job_id, "error": str(error)}
        )

        if quota_reserved:
            try:
                UsageService.release_quota(extract_user_id(event))
            except Exception:
                logger.exception(
                    "Failed to release quota after queueing error",
                    extra={"jobId": job_id},
                )

        if job_id:
            ImageJobService.update_job_status(
                job_id=job_id, status="failed", error=str(error)
            )

        return cors_response(
            500, {"error": "Failed to queue image generation request", "jobId": job_id}
        )


@tracer.capture_method
def handle_healthz():
    return cors_response(
        200,
        {
            "status": "ok",
            "service": "api-manager",
            "environment": _get_environment(),
        },
    )


@tracer.capture_method
def handle_get_job(event):
    user_id = extract_user_id(event)
    if not user_id:
        return cors_response(401, {"error": "Unauthorized: User ID not found"})

    job_id = (event.get("rawPath") or event.get("path", "")).split("/")[-1]
    if not job_id:
        return cors_response(400, {"error": "jobId is required"})

    job = ImageJobService.get_job(job_id)
    if not job:
        return cors_response(404, {"error": "Job not found"})
    if job.get("userId") != user_id:
        return cors_response(403, {"error": "Forbidden: Access denied"})

    hydrated = hydrate_completed_job(job)
    return cors_response(200, hydrated)


@tracer.capture_method
def handle_get_user_info(event):
    user_id = extract_user_id(event)
    if not user_id:
        return cors_response(401, {"error": "Unauthorized: User ID not found"})

    user = UserService.get_user(user_id)
    if not user:
        user = UserService.create_or_update_user(extract_user_data(event))

    _, remaining = UsageService.can_generate_image(user_id)
    response = {
        "userId": user.get("userId"),
        "email": user.get("email", ""),
        "displayName": user.get("displayName", ""),
        "profileImage": user.get("profileImage", ""),
        "provider": "cognito",
        "dailyLimit": UsageService.DAILY_LIMIT,
        "remainingQuota": remaining,
        "usedToday": UsageService.DAILY_LIMIT - remaining,
        "totalImages": user.get("totalImagesGenerated", 0),
        "createdAt": user.get("createdAt", ""),
        "lastLoginAt": user.get("lastLoginAt", ""),
    }
    return cors_response(200, response)


@tracer.capture_method
def handle_get_user_jobs(event):
    user_id = extract_user_id(event)
    if not user_id:
        return cors_response(401, {"error": "Unauthorized: User ID not found"})

    query_params = event.get("queryStringParameters") or {}
    limit = min(int(query_params.get("limit", 20)), 100)
    status = query_params.get("status")
    next_token = query_params.get("nextToken")

    result = ImageJobService.get_user_jobs(
        user_id=user_id, limit=limit, status=status, next_token=next_token
    )
    jobs = [hydrate_completed_job(job) for job in result.get("jobs", [])]
    response = {
        "jobs": jobs,
        "total": len(jobs),
        "limit": limit,
        "nextToken": result.get("nextToken"),
        "hasMore": bool(result.get("nextToken")),
    }
    return cors_response(200, response)


@tracer.capture_method
def handle_download_image(event):
    user_id = extract_user_id(event)
    if not user_id:
        return cors_response(401, {"error": "Unauthorized: User ID not found"})

    raw_path = event.get("rawPath") or event.get("path", "")
    path_parts = raw_path.split("/")
    job_id = path_parts[-2] if len(path_parts) >= 3 else None
    if not job_id:
        return cors_response(400, {"error": "jobId is required"})

    job = ImageJobService.get_job(job_id)
    if not job:
        return cors_response(404, {"error": "Job not found"})
    if job.get("userId") != user_id:
        return cors_response(403, {"error": "Forbidden: Access denied"})
    if job.get("status") != "completed":
        return cors_response(400, {"error": "Job not completed yet"})

    download_url = generate_presigned_download_url(job, expires_in=3600)
    if not download_url:
        return cors_response(404, {"error": "Output image not found"})

    return cors_response(
        200, {"downloadUrl": download_url, "expiresIn": 3600, "jobId": job_id}
    )


def hydrate_completed_job(job: Dict) -> Dict:
    hydrated = dict(job)
    if hydrated.get("status") == "completed" and hydrated.get("outputImageUrl"):
        hydrated["outputImageUrl"] = generate_presigned_download_url(
            hydrated, _get_job_download_expiry_seconds()
        )
    return hydrated


def generate_presigned_download_url(job: Dict, expires_in: int) -> Optional[str]:
    bucket, key = parse_output_location(job)
    if not bucket or not key:
        return None

    try:
        return _get_s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key, "ResponseContentType": "image/png"},
            ExpiresIn=expires_in,
            HttpMethod="GET",
        )
    except ClientError:
        logger.exception(
            "Failed to create download URL", extra={"bucket": bucket, "key": key}
        )
        return None


def parse_output_location(job: Dict) -> Tuple[Optional[str], Optional[str]]:
    output_url = job.get("outputImageUrl")
    metadata = job.get("metadata") or {}

    if isinstance(metadata, dict) and metadata.get("outputKey"):
        return metadata.get("resultBucket", _get_result_bucket()), metadata["outputKey"]

    if output_url and output_url.startswith("s3://"):
        stripped = output_url.replace("s3://", "", 1)
        bucket, _, key = stripped.partition("/")
        return bucket, key or None

    if output_url:
        return _get_result_bucket(), output_url

    return None, None


def extract_user_id(event) -> Optional[str]:
    try:
        authorizer = event.get("requestContext", {}).get("authorizer", {})
        jwt_claims = authorizer.get("jwt", {}).get("claims", {})
        if jwt_claims:
            return jwt_claims.get("sub") or jwt_claims.get("cognito:username")

        claims = authorizer.get("claims", {})
        if claims:
            return claims.get("sub") or claims.get("cognito:username")

        return authorizer.get("principalId") or authorizer.get("userId")
    except Exception:
        logger.exception("Failed to extract user id")
        return None


def extract_user_data(event) -> Dict:
    authorizer = event.get("requestContext", {}).get("authorizer", {})
    claims = authorizer.get("jwt", {}).get("claims", {}) or authorizer.get("claims", {})
    return {
        "userId": claims.get("sub") or claims.get("cognito:username"),
        "email": claims.get("email", ""),
        "displayName": claims.get("name") or claims.get("email", ""),
        "profileImage": claims.get("picture", ""),
        "provider": "cognito",
    }


def parse_request_body(event) -> Optional[Dict]:
    try:
        body = event.get("body", "{}")
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode("utf-8")
        return json.loads(body) if isinstance(body, str) else body
    except Exception:
        logger.exception("Failed to parse request body")
        return None


def validate_generation_request(
    user_id: str, file_key: Optional[str], prompt: str
) -> Optional[str]:
    if not file_key:
        return "fileKey is required"
    if not prompt:
        return "prompt is required"
    if len(prompt) > 2000:
        return "prompt is too long (max 2000 characters)"
    expected_prefix = f"uploads/{user_id}/"
    if not file_key.startswith(expected_prefix):
        return "Invalid file key for current user"
    return None


def verify_s3_file_exists(bucket: str, key: str) -> bool:
    try:
        _get_s3_client().head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as error:
        if error.response["Error"]["Code"] in {"404", "NoSuchKey", "NotFound"}:
            return False
        raise


def cors_response(status_code: int, body: Dict) -> Dict:
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "POST,GET,OPTIONS",
        },
        "body": json.dumps(body, cls=DecimalEncoder),
    }


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return int(obj) if obj % 1 == 0 else float(obj)
        return super().default(obj)
