from dataclasses import dataclass

import docker


@dataclass(frozen=True)
class DockerExecResult:
    exit_code: int
    stdout: str
    stderr: str


def exec_in_container(container_name: str, cmd: list[str]) -> DockerExecResult:
    client = docker.from_env()
    container = client.containers.get(container_name)
    exit_code, (stdout, stderr) = container.exec_run(cmd, demux=True)
    return DockerExecResult(
        exit_code=exit_code,
        stdout=(stdout or b"").decode(errors="replace"),
        stderr=(stderr or b"").decode(errors="replace"),
    )
