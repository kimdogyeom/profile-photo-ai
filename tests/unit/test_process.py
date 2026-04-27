import json

from tests.helpers import load_repo_module, make_lambda_context


def load_process_module():
    return load_repo_module(
        "backend/lambda/process/process.py",
        "test_process_module",
        clear_modules=["common.dynamodb_helper"],
    )


def test_lambda_handler_reports_batch_item_failures_for_failed_records(monkeypatch):
    monkeypatch.setenv("RESULT_BUCKET", "profile-photo-ai-results")
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "ProfilePhotoAI")
    monkeypatch.setenv("POWERTOOLS_METRICS_NAMESPACE", "ProfilePhotoAI/Metrics")
    module = load_process_module()

    job_updates = []
    increment_calls = []

    monkeypatch.setattr(
        module.ImageJobService,
        "update_job_status",
        lambda job_id, status, **kwargs: job_updates.append(
            {"job_id": job_id, "status": status, "metadata": kwargs}
        ),
    )
    monkeypatch.setattr(
        module.UserService,
        "increment_total_images",
        lambda user_id: increment_calls.append(user_id),
    )

    monkeypatch.setattr(module, "parse_s3_uri", lambda *_: ("upload-bucket", "input.png"))
    monkeypatch.setattr(
        module,
        "download_source_image",
        lambda *_: (b"source-bytes", 12.0, "PNG"),
    )
    monkeypatch.setattr(
        module, "generate_with_bedrock", lambda *_: (b"generated-bytes", 34.0)
    )
    monkeypatch.setattr(module, "upload_result_image", lambda *_: 56.0)

    event = {
        "Records": [
            {
                "messageId": "record-success",
                "body": json.dumps(
                    {
                        "jobId": "job-success",
                        "userId": "user-1",
                        "prompt": "portrait",
                        "s3Uri": "s3://upload-bucket/input.png",
                    }
                ),
            },
            {
                "messageId": "record-failed",
                "body": json.dumps({"jobId": "job-failed", "userId": "user-2"}),
            },
        ]
    }

    response = module.lambda_handler(event, make_lambda_context("req-process"))
    body = json.loads(response["body"])

    assert response["batchItemFailures"] == [{"itemIdentifier": "record-failed"}]
    assert body["processed"] == 1
    assert body["failed"] == 1
    assert any(update["status"] == "processing" for update in job_updates)
    assert any(update["status"] == "completed" for update in job_updates)
    assert increment_calls == ["user-1"]


def test_lambda_handler_reports_empty_batch_item_failures_when_all_records_succeed(monkeypatch):
    monkeypatch.setenv("RESULT_BUCKET", "profile-photo-ai-results")
    monkeypatch.setenv("POWERTOOLS_SERVICE_NAME", "ProfilePhotoAI")
    monkeypatch.setenv("POWERTOOLS_METRICS_NAMESPACE", "ProfilePhotoAI/Metrics")
    module = load_process_module()

    job_updates = []
    increment_calls = []

    monkeypatch.setattr(
        module.ImageJobService,
        "update_job_status",
        lambda job_id, status, **kwargs: job_updates.append(
            {"job_id": job_id, "status": status, "metadata": kwargs}
        ),
    )
    monkeypatch.setattr(
        module.UserService,
        "increment_total_images",
        lambda user_id: increment_calls.append(user_id),
    )

    monkeypatch.setattr(module, "parse_s3_uri", lambda *_: ("upload-bucket", "input.png"))
    monkeypatch.setattr(
        module,
        "download_source_image",
        lambda *_: (b"source-bytes", 11.0, "PNG"),
    )
    monkeypatch.setattr(
        module, "generate_with_bedrock", lambda *_: (b"generated-bytes", 33.0)
    )
    monkeypatch.setattr(module, "upload_result_image", lambda *_: 55.0)

    event = {
        "Records": [
            {
                "messageId": "record-1",
                "body": json.dumps(
                    {
                        "jobId": "job-1",
                        "userId": "user-1",
                        "prompt": "portrait",
                        "s3Uri": "s3://upload-bucket/input.png",
                    }
                ),
            },
            {
                "messageId": "record-2",
                "body": json.dumps(
                    {
                        "jobId": "job-2",
                        "userId": "user-2",
                        "prompt": "stylized",
                        "s3Uri": "s3://upload-bucket/input-2.png",
                    }
                ),
            },
        ]
    }

    response = module.lambda_handler(event, make_lambda_context("req-process-all-ok"))
    body = json.loads(response["body"])

    assert response["batchItemFailures"] == []
    assert body["processed"] == 2
    assert body["failed"] == 0
    assert len([update for update in job_updates if update["status"] == "completed"]) == 2
    assert increment_calls == ["user-1", "user-2"]
