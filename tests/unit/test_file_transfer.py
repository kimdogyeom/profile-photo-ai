import json

from tests.helpers import load_repo_module, make_lambda_context


def load_file_transfer():
    return load_repo_module(
        "backend/lambda/file_transfer/file_transfer.py", "test_file_transfer_module"
    )


def test_lambda_handler_returns_presigned_upload(monkeypatch):
    module = load_file_transfer()
    monkeypatch.setenv("UPLOAD_BUCKET", "profile-photo-ai-uploads")
    monkeypatch.setenv("PRESIGNED_URL_EXPIRATION", "900")
    monkeypatch.setattr(
        module,
        "generate_presigned_upload_post",
        lambda **kwargs: {
            "url": "https://profile-photo-ai-uploads.s3.amazonaws.com",
            "fields": {"key": kwargs["key"], "Content-Type": kwargs["content_type"]},
        },
    )

    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                    }
                }
            }
        },
        "body": json.dumps(
            {
                "fileName": "portrait.jpg",
                "fileSize": 1024,
                "contentType": "image/jpeg",
            }
        ),
    }

    response = module.lambda_handler(event, make_lambda_context("req-upload"))
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["uploadUrl"] == "https://profile-photo-ai-uploads.s3.amazonaws.com"
    assert body["expiresIn"] == 900
    assert body["fileKey"].startswith("uploads/user-123/")
    assert "bucket" not in body
    assert response["headers"]["Access-Control-Allow-Origin"] == "*"


def test_lambda_handler_respects_cors_allowlist(monkeypatch):
    module = load_file_transfer()
    monkeypatch.setenv("UPLOAD_BUCKET", "profile-photo-ai-uploads")
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS", '["https://allowed.example.com", "https://other.example.com"]'
    )
    monkeypatch.setattr(
        module,
        "generate_presigned_upload_post",
        lambda **kwargs: {
            "url": "https://profile-photo-ai-uploads.s3.amazonaws.com",
            "fields": {"key": kwargs["key"], "Content-Type": kwargs["content_type"]},
        },
    )

    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                    }
                }
            }
        },
        "headers": {"Origin": "https://allowed.example.com"},
        "body": json.dumps(
            {
                "fileName": "portrait.jpg",
                "fileSize": 1024,
                "contentType": "image/jpeg",
            }
        ),
    }

    response = module.lambda_handler(event, make_lambda_context("req-upload"))
    body = json.loads(response["body"])

    assert body["uploadUrl"] == "https://profile-photo-ai-uploads.s3.amazonaws.com"
    assert (
        response["headers"]["Access-Control-Allow-Origin"]
        == "https://allowed.example.com"
    )


def test_lambda_handler_disallows_disallowed_origin(monkeypatch):
    module = load_file_transfer()
    monkeypatch.setenv("UPLOAD_BUCKET", "profile-photo-ai-uploads")
    monkeypatch.setenv(
        "CORS_ALLOWED_ORIGINS",
        '["https://allowed.example.com"]',
    )
    monkeypatch.setattr(
        module,
        "generate_presigned_upload_post",
        lambda **kwargs: {
            "url": "https://profile-photo-ai-uploads.s3.amazonaws.com",
            "fields": {"key": kwargs["key"], "Content-Type": kwargs["content_type"]},
        },
    )

    event = {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "sub": "user-123",
                    }
                }
            }
        },
        "headers": {"Origin": "https://evil.example.com"},
        "body": json.dumps(
            {
                "fileName": "portrait.jpg",
                "fileSize": 1024,
                "contentType": "image/jpeg",
            }
        ),
    }

    response = module.lambda_handler(event, make_lambda_context("req-upload"))

    assert "Access-Control-Allow-Origin" not in response["headers"]


def test_validate_upload_request_rejects_unsupported_content_type():
    module = load_file_transfer()

    error = module.validate_upload_request("portrait.gif", "image/gif", 1024)

    assert (
        error == "Unsupported content type. Allowed: image/jpeg, image/png, image/webp"
    )
