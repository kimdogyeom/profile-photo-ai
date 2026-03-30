import base64
import json
import os
import resource
import sys
import time
from datetime import datetime
from io import BytesIO
from urllib.parse import urlparse

import boto3
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from botocore.config import Config
from PIL import Image

BACKEND_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BACKEND_ROOT not in sys.path:
    sys.path.append(BACKEND_ROOT)

from common.dynamodb_helper import ImageJobService, UserService

logger = Logger()
tracer = Tracer()
metrics = Metrics()

endpoint_url = os.environ.get("AWS_ENDPOINT_URL")
s3_kwargs = {}
if endpoint_url:
    s3_kwargs["endpoint_url"] = endpoint_url

s3_client = boto3.client("s3", **s3_kwargs)
bedrock_client = boto3.client(
    "bedrock-runtime",
    region_name=os.environ.get("BEDROCK_REGION", "ap-northeast-1"),
    config=Config(read_timeout=300, retries={"max_attempts": 3, "mode": "standard"}),
)

RESULT_BUCKET = os.environ["RESULT_BUCKET"]
BEDROCK_MODEL_ID = os.environ.get("BEDROCK_MODEL_ID", "amazon.nova-canvas-v1:0")
BEDROCK_TASK_TYPE = os.environ.get("BEDROCK_IMAGE_TASK_TYPE", "IMAGE_VARIATION")
BEDROCK_IMAGE_WIDTH = int(os.environ.get("BEDROCK_IMAGE_WIDTH", "1024"))
BEDROCK_IMAGE_HEIGHT = int(os.environ.get("BEDROCK_IMAGE_HEIGHT", "1024"))
BEDROCK_IMAGE_QUALITY = os.environ.get("BEDROCK_IMAGE_QUALITY", "standard")
BEDROCK_CFG_SCALE = float(os.environ.get("BEDROCK_CFG_SCALE", "6.5"))
BEDROCK_NUMBER_OF_IMAGES = int(os.environ.get("BEDROCK_NUMBER_OF_IMAGES", "1"))
BEDROCK_SIMILARITY_STRENGTH = float(os.environ.get("BEDROCK_SIMILARITY_STRENGTH", "0.8"))
NEGATIVE_PROMPT = os.environ.get(
    "BEDROCK_NEGATIVE_PROMPT",
    "blurry, distorted face, extra fingers, multiple people, text, watermark, logo, cluttered background, low quality, overexposed, underexposed",
)
WEBSOCKET_ENDPOINT = os.environ.get("WEBSOCKET_ENDPOINT")

api_gateway_client = None
if WEBSOCKET_ENDPOINT:
    api_gateway_client = boto3.client("apigatewaymanagementapi", endpoint_url=WEBSOCKET_ENDPOINT)


@logger.inject_lambda_context
@tracer.capture_lambda_handler
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event, context):
    processed_count = 0
    failed_count = 0

    batch_size = len(event["Records"])
    metrics.add_metric(name="BatchSize", unit=MetricUnit.Count, value=batch_size)

    for record in event["Records"]:
        job_id = None
        user_id = None
        connection_id = None
        start_time = time.time()

        try:
            body = json.loads(record["body"])
            job_id = body.get("jobId")
            user_id = body.get("userId")
            prompt = body.get("prompt")
            style = body.get("style", "formal_interview")
            s3_uri = body.get("s3Uri")
            connection_id = body.get("connectionId")

            if not all([job_id, user_id, prompt, s3_uri]):
                raise ValueError("Missing required fields in SQS message")

            ImageJobService.update_job_status(job_id, "processing")

            source_bucket, source_key = parse_s3_uri(s3_uri)
            input_bytes, download_ms, source_format = download_source_image(source_bucket, source_key)
            generated_bytes, generation_ms = generate_with_bedrock(input_bytes, source_format, prompt)

            output_key = f"generated/{user_id}/{job_id}.png"
            upload_ms = upload_result_image(output_key, generated_bytes, user_id, job_id, style)
            output_s3_uri = f"s3://{RESULT_BUCKET}/{output_key}"
            processing_ms = (time.time() - start_time) * 1000

            ImageJobService.update_job_status(
                job_id=job_id,
                status="completed",
                output_url=output_s3_uri,
                processing_time=processing_ms,
                metadata={
                    "modelId": BEDROCK_MODEL_ID,
                    "taskType": BEDROCK_TASK_TYPE,
                    "outputKey": output_key,
                    "resultBucket": RESULT_BUCKET,
                    "s3Uri": output_s3_uri,
                    "generationTimeMs": generation_ms,
                    "downloadTimeMs": download_ms,
                    "uploadTimeMs": upload_ms,
                },
            )

            UserService.increment_total_images(user_id)

            memory_used_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
            logger.info(
                "Image generation completed",
                extra={
                    "jobId": job_id,
                    "userId": user_id,
                    "processingTimeMs": processing_ms,
                    "generationTimeMs": generation_ms,
                    "memoryUsedMb": memory_used_mb,
                },
            )

            metrics.add_metric(name="ImageGenerationSuccess", unit=MetricUnit.Count, value=1)
            metrics.add_metric(name="TotalProcessingTime", unit=MetricUnit.Milliseconds, value=processing_ms)
            metrics.add_metric(name="NovaAPIResponseTime", unit=MetricUnit.Milliseconds, value=generation_ms)

            if connection_id and api_gateway_client:
                send_websocket_notification(
                    connection_id,
                    {
                        "type": "image_completed",
                        "jobId": job_id,
                        "status": "completed",
                        "s3Uri": output_s3_uri,
                        "processingTime": processing_ms,
                    },
                )

            processed_count += 1
        except Exception as error:
            failed_count += 1
            processing_ms = (time.time() - start_time) * 1000
            metrics.add_metric(name="ImageGenerationFailure", unit=MetricUnit.Count, value=1)

            logger.exception(
                "Image generation failed",
                extra={"jobId": job_id, "userId": user_id, "processingTimeMs": processing_ms, "error": str(error)},
            )

            if job_id:
                try:
                    ImageJobService.update_job_status(
                        job_id=job_id, status="failed", error=str(error), processing_time=processing_ms
                    )
                except Exception:
                    logger.exception("Failed to persist failed job state", extra={"jobId": job_id})

            if connection_id and api_gateway_client:
                send_websocket_notification(
                    connection_id,
                    {"type": "image_failed", "jobId": job_id, "status": "failed", "error": str(error)},
                )

    logger.info(
        "Batch processing complete",
        extra={"totalRecords": len(event["Records"]), "processedCount": processed_count, "failedCount": failed_count},
    )
    metrics.add_metric(name="BatchProcessed", unit=MetricUnit.Count, value=processed_count)
    metrics.add_metric(name="BatchFailed", unit=MetricUnit.Count, value=failed_count)

    return {
        "statusCode": 200,
        "body": json.dumps({"message": "Processing complete", "processed": processed_count, "failed": failed_count}),
    }


def parse_s3_uri(s3_uri):
    parsed = urlparse(s3_uri)
    return parsed.netloc, parsed.path.lstrip("/")


def download_source_image(bucket, key):
    download_start = time.time()
    response = s3_client.get_object(Bucket=bucket, Key=key)
    image_bytes = response["Body"].read()

    with Image.open(BytesIO(image_bytes)) as image:
        source_format = (image.format or "PNG").upper()

    return image_bytes, (time.time() - download_start) * 1000, source_format


def generate_with_bedrock(image_bytes, source_format, prompt):
    image_format = "PNG" if source_format not in {"PNG", "JPEG", "JPG"} else source_format
    canonical_bytes = image_bytes

    if image_format == "JPG":
        image_format = "JPEG"

    if image_format not in {"PNG", "JPEG"}:
        with Image.open(BytesIO(image_bytes)) as image:
            converted = BytesIO()
            image.convert("RGB").save(converted, format="PNG")
            canonical_bytes = converted.getvalue()
        image_format = "PNG"

    request_body = {
        "taskType": BEDROCK_TASK_TYPE,
        "imageVariationParams": {
            "images": [base64.b64encode(canonical_bytes).decode("utf-8")],
            "similarityStrength": BEDROCK_SIMILARITY_STRENGTH,
            "text": prompt[:1024],
            "negativeText": NEGATIVE_PROMPT[:1024],
        },
        "imageGenerationConfig": {
            "width": BEDROCK_IMAGE_WIDTH,
            "height": BEDROCK_IMAGE_HEIGHT,
            "quality": BEDROCK_IMAGE_QUALITY,
            "cfgScale": BEDROCK_CFG_SCALE,
            "numberOfImages": BEDROCK_NUMBER_OF_IMAGES,
        },
    }

    generation_start = time.time()
    response = bedrock_client.invoke_model(
        modelId=BEDROCK_MODEL_ID,
        contentType="application/json",
        accept="application/json",
        body=json.dumps(request_body),
    )
    response_body = json.loads(response["body"].read())
    generation_ms = (time.time() - generation_start) * 1000

    if generation_ms > 30000:
        logger.warning("nova_api_slow_response", extra={"responseTimeMs": generation_ms})

    if response_body.get("error"):
        logger.error("nova_api_error", extra={"error": response_body["error"]})
        raise RuntimeError(response_body["error"])

    images = response_body.get("images") or []
    if not images:
        raise RuntimeError("Nova Canvas returned no images")

    generated_bytes = base64.b64decode(images[0])
    return generated_bytes, generation_ms


def upload_result_image(output_key, generated_bytes, user_id, job_id, style):
    upload_start = time.time()
    s3_client.put_object(
        Bucket=RESULT_BUCKET,
        Key=output_key,
        Body=generated_bytes,
        ContentType="image/png",
        ServerSideEncryption="AES256",
        Metadata={
            "userId": user_id,
            "jobId": job_id,
            "style": style,
            "generatedAt": datetime.utcnow().isoformat(),
            "modelId": BEDROCK_MODEL_ID,
        },
    )
    return (time.time() - upload_start) * 1000


def send_websocket_notification(connection_id, payload):
    try:
        api_gateway_client.post_to_connection(ConnectionId=connection_id, Data=json.dumps(payload).encode("utf-8"))
    except Exception:
        logger.exception("Failed to send websocket notification", extra={"connectionId": connection_id})
