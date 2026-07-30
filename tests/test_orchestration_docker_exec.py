from unittest.mock import MagicMock, patch

from lakehouse.orchestration.docker_exec import exec_in_container


def test_exec_in_container_returns_success_result() -> None:
    mock_container = MagicMock()
    mock_container.exec_run.return_value = (0, (b"hello\n", b""))
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container

    with patch("lakehouse.orchestration.docker_exec.docker.from_env", return_value=mock_client):
        result = exec_in_container("spark-iceberg", ["echo", "hello"])

    mock_client.containers.get.assert_called_once_with("spark-iceberg")
    mock_container.exec_run.assert_called_once_with(["echo", "hello"], demux=True)
    assert result.exit_code == 0
    assert result.stdout == "hello\n"
    assert result.stderr == ""


def test_exec_in_container_returns_failure_result() -> None:
    mock_container = MagicMock()
    mock_container.exec_run.return_value = (1, (None, b"boom\n"))
    mock_client = MagicMock()
    mock_client.containers.get.return_value = mock_container

    with patch("lakehouse.orchestration.docker_exec.docker.from_env", return_value=mock_client):
        result = exec_in_container("spark-iceberg", ["false"])

    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr == "boom\n"
