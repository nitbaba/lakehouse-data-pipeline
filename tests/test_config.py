import pytest

from lakehouse.common.config import Settings


def test_from_env_builds_warehouse_path(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LAKEHOUSE_BUCKET_NAME", "lakehouse-dev-123456789012")
    monkeypatch.setenv("AWS_REGION", "us-east-1")

    settings = Settings.from_env()

    assert settings.bucket_name == "lakehouse-dev-123456789012"
    assert settings.aws_region == "us-east-1"
    assert settings.warehouse_path == "s3://lakehouse-dev-123456789012/warehouse/"


def test_from_env_requires_bucket_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LAKEHOUSE_BUCKET_NAME", raising=False)

    with pytest.raises(KeyError):
        Settings.from_env()
