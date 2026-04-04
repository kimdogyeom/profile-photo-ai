import json

from tests.helpers import load_repo_module, make_lambda_context


def test_stage_prefixed_healthz_path_is_normalized(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "dev")
    module = load_repo_module(
        "backend/lambda/api/api_manager.py",
        "integration_api_manager_module",
        clear_modules=["common.dynamodb_helper"],
    )

    response = module.lambda_handler(
        {
            "requestContext": {
                "http": {
                    "method": "GET",
                },
                "stage": "dev",
            },
            "rawPath": "/dev/healthz",
        },
        make_lambda_context("req-healthz"),
    )

    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["status"] == "ok"
    assert body["environment"] == "dev"
