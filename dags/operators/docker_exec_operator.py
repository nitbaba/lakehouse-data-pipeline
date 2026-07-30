from airflow.exceptions import AirflowException
from airflow.models import BaseOperator

from lakehouse.orchestration.docker_exec import exec_in_container


class DockerExecOperator(BaseOperator):
    """Runs a command inside an already-running Docker container via `docker exec`
    semantics (not Airflow's built-in DockerOperator, which creates new containers).
    """

    template_fields = ("container_name", "command")

    def __init__(self, *, container_name: str, command: list[str], **kwargs: object) -> None:
        super().__init__(**kwargs)
        self.container_name = container_name
        self.command = command

    def execute(self, context: object) -> None:
        result = exec_in_container(self.container_name, self.command)
        if result.stdout:
            self.log.info("stdout:\n%s", result.stdout)
        if result.stderr:
            self.log.info("stderr:\n%s", result.stderr)
        if result.exit_code != 0:
            raise AirflowException(
                f"command {self.command!r} in container '{self.container_name}' "
                f"failed with exit code {result.exit_code}\nstderr:\n{result.stderr}"
            )
