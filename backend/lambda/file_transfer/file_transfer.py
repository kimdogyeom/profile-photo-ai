import base64
import json
import os
import time
import uuid
from datetime import UTC, datetime
from functools import lru_cache
from typing import Optional

import boto3
from aws_lambda_powertools import Logger, Tracer
from aws_lambda_powertools.logging import correlation_paths

logger = Logger()


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
def _get_s3_client():
    return boto3.client("s3", **_client_kwargs())


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _get_upload_bucket() -> str:
    return _require_env("UPLOAD_BUCKET")


def _get_presigned_url_expiration() -> int:
    return int(os.environ.get("PRESIGNED_URL_EXPIRATION", "3600"))


def _get_cors_allowed_origins() -> list[str]:
    raw = os.environ.get("CORS_ALLOWED_ORIGINS", "*")
    if not raw:
        return ["*"]

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass

    return [item.strip() for item in raw.split(",") if item.strip()]


def _get_request_origin(headers=None) -> Optional[str]:
    if not headers:
        return None
    for key, value in headers.items():
        if key.lower() == "origin":
            return value
    return None


def _select_allow_origin(request_origin):
    allowed_origins = _get_cors_allowed_origins()
    if "*" in allowed_origins:
        return "*"
    if request_origin in allowed_origins:
        return request_origin
    return None


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_CONTENT_TYPES = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024


@logger.inject_lambda_context(correlation_id_path=correlation_paths.API_GATEWAY_HTTP)
@tracer.capture_lambda_handler
def lambda_handler(event, context):
    request_start = time.time()
    request_origin = _get_request_origin(event.get("headers") or {})

    try:
        user_id = extract_user_id(event)
        if not user_id:
            return error_response(401, "Unauthorized: User ID not found", request_origin)

        body = parse_request_body(event)
        if not body:
            return error_response(400, "Invalid request body", request_origin)

        file_name = body.get("fileName")
        content_type = body.get("contentType")
        file_size = body.get("fileSize", 0)

        validation_error = validate_upload_request(file_name, content_type, file_size)
        if validation_error:
            return error_response(400, validation_error, request_origin)

        file_key = generate_file_key(
            user_id, get_file_extension(file_name, content_type)
        )
        presigned_post = generate_presigned_upload_post(
            bucket=_get_upload_bucket(),
            key=file_key,
            content_type=content_type,
            expiration=_get_presigned_url_expiration(),
        )

        logger.info(
            "Presigned upload prepared",
            extra={
                "userId": user_id,
                "fileKey": file_key,
                "processingMs": int((time.time() - request_start) * 1000),
            },
        )

        return {
            "statusCode": 200,
            "headers": cors_headers(request_origin),
            "body": json.dumps(
                {
                    "uploadUrl": presigned_post["url"],
                    "uploadMethod": "POST",
                    "uploadFields": presigned_post["fields"],
                    "fileKey": file_key,
                    "expiresIn": _get_presigned_url_expiration(),
                    "maxFileSize": MAX_FILE_SIZE,
                }
            ),
        }
    except Exception as error:
        logger.exception(
            "Failed to generate presigned upload", extra={"error": str(error)}
        )
        return error_response(500, "Internal server error", request_origin)


def extract_user_id(event):
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


def parse_request_body(event):
    try:
        body = event.get("body", "{}")
        if event.get("isBase64Encoded"):
            body = base64.b64decode(body).decode("utf-8")
        return json.loads(body) if isinstance(body, str) else body
    except Exception:
        logger.exception("Failed to parse upload request")
        return None


def validate_upload_request(file_name, content_type, file_size):
    if not file_name:
        return "fileName is required"
    if not content_type:
        return "contentType is required"
    if content_type not in ALLOWED_CONTENT_TYPES:
        return f"Unsupported content type. Allowed: {', '.join(ALLOWED_CONTENT_TYPES.keys())}"

    file_ext = os.path.splitext(file_name.lower())[1]
    if file_ext not in ALLOWED_EXTENSIONS:
        return f"Unsupported file extension. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
    if not isinstance(file_size, int):
        return "fileSize must be an integer"
    if file_size <= 0:
        return "Invalid file size"
    if file_size > MAX_FILE_SIZE:
        return f"File size exceeds maximum allowed size of {MAX_FILE_SIZE // (1024 * 1024)}MB"
    return None


def get_file_extension(file_name, content_type):
    file_ext = os.path.splitext(file_name.lower())[1]
    if not file_ext or file_ext not in ALLOWED_EXTENSIONS:
        file_ext = "." + ALLOWED_CONTENT_TYPES.get(content_type, "jpg")
    return file_ext


def generate_file_key(user_id, file_extension):
    unique_id = uuid.uuid4().hex[:12]
    timestamp = datetime.now(UTC).strftime("%Y%m%d")
    return f"uploads/{user_id}/{timestamp}_{unique_id}{file_extension}"


def generate_presigned_upload_post(bucket, key, content_type, expiration):
    return _get_s3_client().generate_presigned_post(
        Bucket=bucket,
        Key=key,
        Fields={
            "Content-Type": content_type,
            "success_action_status": "204",
            "x-amz-server-side-encryption": "AES256",
        },
        Conditions=[
            {"Content-Type": content_type},
            {"success_action_status": "204"},
            {"x-amz-server-side-encryption": "AES256"},
            ["content-length-range", 1, MAX_FILE_SIZE],
        ],
        ExpiresIn=expiration,
    )


def cors_headers(origin):
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "POST,OPTIONS",
    }
    allow_origin = _select_allow_origin(origin)
    if allow_origin:
        headers["Access-Control-Allow-Origin"] = allow_origin
    return headers


def error_response(status_code, message, request_origin):
    return {
        "statusCode": status_code,
        "headers": cors_headers(request_origin),
        "body": json.dumps({"error": message}),
    }
