import json

from tests.helpers import load_repo_module, make_lambda_context


def load_api_manager():
    return load_repo_module(
        "backend/lambda/api/api_manager.py",
        "test_api_manager_module",
        clear_modules=["common.dynamodb_helper"],
    )


def test_healthz_route_returns_ok(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "test")
    module = load_api_manager()

    response = module.lambda_handler(
        {
            "requestContext": {
                "http": {
                    "method": "GET",
                }
            },
            "rawPath": "/healthz",
        },
        make_lambda_context("req-123"),
    )

    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body == {
        "status": "ok",
        "service": "api-manager",
        "environment": "test",
    }


def test_validate_generation_request_requires_user_prefix():
    module = load_api_manager()

    error = module.validate_generation_request(
        "user-123", "uploads/other-user/file.png", "studio portrait"
    )

    assert error == "Invalid file key for current user"
