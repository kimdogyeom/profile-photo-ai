import pytest


@pytest.fixture(autouse=True)
def clear_runtime_env(monkeypatch):
    for key in (
        "AWS_ENDPOINT_URL",
        "AWS_REGION",
        "DAILY_LIMIT",
        "ENVIRONMENT",
        "IMAGE_JOBS_TABLE",
        "JOB_DOWNLOAD_EXPIRY_SECONDS",
        "PRESIGNED_URL_EXPIRATION",
        "RESULT_BUCKET",
        "SQS_QUEUE_URL",
        "UPLOAD_BUCKET",
        "USAGE_LOG_TABLE",
        "USERS_TABLE",
        "WEBSOCKET_ENDPOINT",
    ):
        monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("POWERTOOLS_TRACE_DISABLED", "true")
    monkeypatch.setenv("AWS_XRAY_SDK_ENABLED", "false")
    monkeypatch.setenv("AWS_XRAY_CONTEXT_MISSING", "LOG_ERROR")
