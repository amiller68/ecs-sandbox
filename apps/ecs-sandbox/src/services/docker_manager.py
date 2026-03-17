"""Docker container lifecycle management via aiodocker."""

from __future__ import annotations

import os

import aiodocker

from src.config import Config


class DockerManager:
    """Manages sandbox container creation, exec, and teardown."""

    def __init__(self, config: Config):
        self.config = config
        self._docker: aiodocker.Docker | None = None

    async def connect(self) -> None:
        self._docker = aiodocker.Docker()

    async def close(self) -> None:
        if self._docker:
            await self._docker.close()

    @property
    def docker(self) -> aiodocker.Docker:
        assert self._docker is not None, "DockerManager not connected"
        return self._docker

    async def create_container(
        self,
        session_id: str,
        image: str | None = None,
        workspace_path: str | None = None,
    ) -> tuple[str, str]:
        """Create and start a sandbox container.

        Returns (container_id, container_ip).
        """
        image = image or self.config.sandbox_image

        host_config: dict = {
            "Memory": _parse_memory(self.config.sandbox_memory_limit),
            "NanoCpus": int(float(self.config.sandbox_cpu_limit) * 1e9),
            "PidsLimit": self.config.sandbox_pids_limit,
        }

        binds = []
        if workspace_path:
            os.makedirs(workspace_path, exist_ok=True)
            binds.append(f"{workspace_path}:/workspace")
            host_config["Binds"] = binds

        container_config = {
            "Image": image,
            "Labels": {"ecs-sandbox.session_id": session_id},
            "ExposedPorts": {"2222/tcp": {}},
            "HostConfig": {
                **host_config,
                "PublishAllPorts": True,
            },
        }

        container = await self.docker.containers.create_or_replace(
            name=f"sandbox-{session_id[:12]}",
            config=container_config,
        )
        await container.start()

        # Get the container IP
        info = await container.show()
        container_id = info["Id"]

        # Try bridge network first, fall back to first available
        networks = info.get("NetworkSettings", {}).get("Networks", {})
        container_ip = "127.0.0.1"
        for net_name, net_info in networks.items():
            ip = net_info.get("IPAddress")
            if ip:
                container_ip = ip
                break

        # If no network IP, get the mapped port on host
        if container_ip == "127.0.0.1":
            ports = info.get("NetworkSettings", {}).get("Ports", {})
            port_bindings = ports.get("2222/tcp", [])
            if port_bindings:
                host_port = port_bindings[0].get("HostPort", "2222")
                container_ip = f"127.0.0.1:{host_port}"

        return container_id, container_ip

    async def stop_container(self, container_id: str) -> None:
        """Stop and remove a container."""
        try:
            container = self.docker.containers.container(container_id)
            await container.stop()
            await container.delete(force=True)
        except aiodocker.exceptions.DockerError:
            pass  # Already stopped/removed

    async def list_sandbox_containers(self) -> list[dict]:
        """List all running containers with ecs-sandbox labels."""
        containers = await self.docker.containers.list(
            filters={"label": ["ecs-sandbox.session_id"]}
        )
        result = []
        for c in containers:
            info = await c.show()
            labels = info.get("Config", {}).get("Labels", {})
            result.append(
                {
                    "container_id": info["Id"],
                    "session_id": labels.get("ecs-sandbox.session_id"),
                }
            )
        return result


def _parse_memory(mem_str: str) -> int:
    """Convert memory string like '512m' to bytes."""
    mem_str = mem_str.strip().lower()
    if mem_str.endswith("g"):
        return int(float(mem_str[:-1]) * 1024 * 1024 * 1024)
    if mem_str.endswith("m"):
        return int(float(mem_str[:-1]) * 1024 * 1024)
    if mem_str.endswith("k"):
        return int(float(mem_str[:-1]) * 1024)
    return int(mem_str)
