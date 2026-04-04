import base64
import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get("LOG_LEVEL", "INFO"))


def _resource_kwargs() -> Dict[str, str]:
    kwargs = {"region_name": os.environ.get("AWS_REGION", "ap-northeast-1")}
    endpoint_url = os.environ.get("AWS_ENDPOINT_URL")
    if endpoint_url:
        kwargs["endpoint_url"] = endpoint_url
    return kwargs


@lru_cache(maxsize=1)
def get_dynamodb_resource():
    return boto3.resource("dynamodb", **_resource_kwargs())


def _missing_table_env_vars() -> List[str]:
    return [
        name
        for name in ("USERS_TABLE", "USAGE_LOG_TABLE", "IMAGE_JOBS_TABLE")
        if not os.environ.get(name)
    ]


def _assert_required_table_env_vars() -> None:
    missing = _missing_table_env_vars()
    if missing:
        raise RuntimeError(
            f"Missing required DynamoDB table env vars: {', '.join(missing)}"
        )


def get_users_table():
    _assert_required_table_env_vars()
    return get_dynamodb_resource().Table(os.environ["USERS_TABLE"])


def get_usage_log_table():
    _assert_required_table_env_vars()
    return get_dynamodb_resource().Table(os.environ["USAGE_LOG_TABLE"])


def get_image_jobs_table():
    _assert_required_table_env_vars()
    return get_dynamodb_resource().Table(os.environ["IMAGE_JOBS_TABLE"])


def _utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _to_decimal(value):
    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {key: _to_decimal(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_decimal(item) for item in value]
    return value


def encode_pagination_token(last_evaluated_key: Optional[Dict]) -> Optional[str]:
    if not last_evaluated_key:
        return None
    return base64.urlsafe_b64encode(
        json.dumps(last_evaluated_key).encode("utf-8")
    ).decode("utf-8")


def decode_pagination_token(token: Optional[str]) -> Optional[Dict]:
    if not token:
        return None
    decoded = base64.urlsafe_b64decode(token.encode("utf-8")).decode("utf-8")
    return json.loads(decoded)


class UserService:
    @staticmethod
    def create_or_update_user(user_data: Dict) -> Dict:
        user_id = user_data["userId"]
        existing = UserService.get_user(user_id) or {}
        users_table = get_users_table()

        item = {
            "userId": user_id,
            "email": user_data.get("email", existing.get("email", "")),
            "provider": "cognito",
            "displayName": user_data.get(
                "displayName", existing.get("displayName", "")
            ),
            "profileImage": user_data.get(
                "profileImage", existing.get("profileImage", "")
            ),
            "createdAt": existing.get("createdAt", _utc_now_iso()),
            "lastLoginAt": _utc_now_iso(),
            "totalImagesGenerated": int(existing.get("totalImagesGenerated", 0)),
        }

        users_table.put_item(Item=item)
        return item

    @staticmethod
    def get_user(user_id: str) -> Optional[Dict]:
        users_table = get_users_table()
        try:
            response = users_table.get_item(Key={"userId": user_id})
            return response.get("Item")
        except ClientError:
            logger.exception("Failed to fetch user", extra={"userId": user_id})
            return None

    @staticmethod
    def increment_total_images(user_id: str) -> None:
        users_table = get_users_table()
        users_table.update_item(
            Key={"userId": user_id},
            UpdateExpression="SET totalImagesGenerated = if_not_exists(totalImagesGenerated, :zero) + :inc",
            ExpressionAttributeValues={":inc": 1, ":zero": 0},
        )


class UsageService:
    DAILY_LIMIT = int(os.environ.get("DAILY_LIMIT", "15"))

    @staticmethod
    def _today_key(user_id: str) -> Tuple[str, str]:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return today, f"{user_id}#{today}"

    @staticmethod
    def get_today_usage(user_id: str) -> int:
        today, user_id_date = UsageService._today_key(user_id)
        del today
        usage_log_table = get_usage_log_table()
        try:
            response = usage_log_table.get_item(Key={"userIdDate": user_id_date})
            if "Item" not in response:
                return 0
            return int(response["Item"].get("count", 0))
        except ClientError:
            logger.exception("Failed to fetch usage", extra={"userId": user_id})
            return 0

    @staticmethod
    def can_generate_image(user_id: str) -> Tuple[bool, int]:
        current_usage = UsageService.get_today_usage(user_id)
        remaining = max(UsageService.DAILY_LIMIT - current_usage, 0)
        return remaining > 0, remaining

    @staticmethod
    def try_consume_quota(user_id: str) -> Tuple[bool, int, int]:
        today, user_id_date = UsageService._today_key(user_id)
        ttl = int((datetime.utcnow() + timedelta(days=90)).timestamp())
        usage_log_table = get_usage_log_table()

        try:
            response = usage_log_table.update_item(
                Key={"userIdDate": user_id_date},
                UpdateExpression=(
                    "SET #count = if_not_exists(#count, :zero) + :inc, "
                    "userId = :userId, #date = :date, lastUpdated = :lastUpdated, #ttl = :ttl"
                ),
                ConditionExpression="attribute_not_exists(#count) OR #count < :limit",
                ExpressionAttributeNames={
                    "#count": "count",
                    "#date": "date",
                    "#ttl": "ttl",
                },
                ExpressionAttributeValues={
                    ":inc": 1,
                    ":zero": 0,
                    ":limit": UsageService.DAILY_LIMIT,
                    ":userId": user_id,
                    ":date": today,
                    ":lastUpdated": _utc_now_iso(),
                    ":ttl": ttl,
                },
                ReturnValues="UPDATED_NEW",
            )
            new_usage = int(response["Attributes"]["count"])
            return True, new_usage, max(UsageService.DAILY_LIMIT - new_usage, 0)
        except ClientError as error:
            if error.response["Error"]["Code"] != "ConditionalCheckFailedException":
                logger.exception("Quota consume failed", extra={"userId": user_id})
                raise
            current_usage = UsageService.get_today_usage(user_id)
            return (
                False,
                current_usage,
                max(UsageService.DAILY_LIMIT - current_usage, 0),
            )

    @staticmethod
    def release_quota(user_id: str) -> int:
        today, user_id_date = UsageService._today_key(user_id)
        del today
        usage_log_table = get_usage_log_table()
        try:
            response = usage_log_table.update_item(
                Key={"userIdDate": user_id_date},
                UpdateExpression="SET #count = #count - :dec, lastUpdated = :lastUpdated",
                ConditionExpression="attribute_exists(#count) AND #count >= :dec",
                ExpressionAttributeNames={"#count": "count"},
                ExpressionAttributeValues={":dec": 1, ":lastUpdated": _utc_now_iso()},
                ReturnValues="UPDATED_NEW",
            )
            return int(response["Attributes"]["count"])
        except ClientError:
            logger.exception("Quota release failed", extra={"userId": user_id})
            raise

    @staticmethod
    def get_usage_history(user_id: str, days: int = 7) -> List[Dict]:
        usage_log_table = get_usage_log_table()
        try:
            response = usage_log_table.query(
                IndexName="UserIdIndex",
                KeyConditionExpression="userId = :userId",
                ExpressionAttributeValues={":userId": user_id},
                ScanIndexForward=False,
                Limit=days,
            )
            return response.get("Items", [])
        except ClientError:
            logger.exception("Failed to fetch usage history", extra={"userId": user_id})
            return []


class ImageJobService:
    @staticmethod
    def create_job(user_id: str, style: str, input_url: str, prompt: str) -> str:
        job_id = f"job_{uuid.uuid4().hex[:12]}"
        timestamp = _utc_now_iso()
        image_jobs_table = get_image_jobs_table()

        image_jobs_table.put_item(
            Item={
                "jobId": job_id,
                "userId": user_id,
                "status": "pending",
                "style": style,
                "inputImageUrl": input_url,
                "prompt": prompt,
                "createdAt": timestamp,
                "updatedAt": timestamp,
            }
        )
        return job_id

    @staticmethod
    def update_job_status(job_id: str, status: str, **kwargs) -> None:
        update_expression = "SET #status = :status, updatedAt = :updatedAt"
        expression_values = {":status": status, ":updatedAt": _utc_now_iso()}
        expression_names = {"#status": "status"}
        image_jobs_table = get_image_jobs_table()

        if "output_url" in kwargs:
            update_expression += ", outputImageUrl = :outputUrl"
            expression_values[":outputUrl"] = kwargs["output_url"]

        if "error" in kwargs:
            update_expression += ", #error = :error"
            expression_values[":error"] = kwargs["error"]
            expression_names["#error"] = "error"

        if "processing_time" in kwargs:
            update_expression += ", processingTime = :processingTime"
            expression_values[":processingTime"] = Decimal(
                str(kwargs["processing_time"])
            )

        if "metadata" in kwargs:
            update_expression += ", metadata = :metadata"
            expression_values[":metadata"] = _to_decimal(kwargs["metadata"])

        image_jobs_table.update_item(
            Key={"jobId": job_id},
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_names,
            ExpressionAttributeValues=expression_values,
        )

    @staticmethod
    def get_job(job_id: str) -> Optional[Dict]:
        image_jobs_table = get_image_jobs_table()
        try:
            response = image_jobs_table.get_item(Key={"jobId": job_id})
            return response.get("Item")
        except ClientError:
            logger.exception("Failed to fetch job", extra={"jobId": job_id})
            return None

    @staticmethod
    def get_user_jobs(
        user_id: str,
        limit: int = 20,
        status: Optional[str] = None,
        next_token: Optional[str] = None,
    ) -> Dict:
        image_jobs_table = get_image_jobs_table()
        query_params = {
            "IndexName": "UserIdCreatedAtIndex",
            "KeyConditionExpression": "userId = :userId",
            "ExpressionAttributeValues": {":userId": user_id},
            "ScanIndexForward": False,
            "Limit": limit,
        }

        if status and status != "all":
            query_params["FilterExpression"] = "#status = :status"
            query_params["ExpressionAttributeNames"] = {"#status": "status"}
            query_params["ExpressionAttributeValues"][":status"] = status

        decoded_token = decode_pagination_token(next_token)
        if decoded_token:
            query_params["ExclusiveStartKey"] = decoded_token

        try:
            response = image_jobs_table.query(**query_params)
            return {
                "jobs": response.get("Items", []),
                "nextToken": encode_pagination_token(response.get("LastEvaluatedKey")),
            }
        except ClientError:
            logger.exception("Failed to fetch user jobs", extra={"userId": user_id})
            return {"jobs": [], "nextToken": None}
