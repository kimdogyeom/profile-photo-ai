import pytest

from tests.helpers import load_repo_module


def load_helper():
    return load_repo_module(
        "backend/common/dynamodb_helper.py",
        "common.dynamodb_helper",
        clear_modules=["common.dynamodb_helper"],
    )


def test_import_does_not_require_table_env_vars():
    helper = load_helper()

    assert helper.UsageService.DAILY_LIMIT == 15


def test_table_access_requires_env_vars():
    helper = load_helper()

    with pytest.raises(RuntimeError, match="Missing required DynamoDB table env vars"):
        helper.get_image_jobs_table()
