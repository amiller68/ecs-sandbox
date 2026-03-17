"""Docker container lifecycle management."""

import time

import docker
from docker.errors import NotFound


class DockerManager:
    def __init__(self, config):
        self.config = config
        self._client: docker.DockerClient | None = None

    async def connect(self):
        self._client = docker.from_env()

    def _docker(self) -> docker.DockerClient:
        assert self._client is not None, "DockerManager not connected"
        return self._client

    async def close(self):
        if self._client:
            self._client.close()

    async def create_container(
        self,
        session_id: str,
        image: str,
        memory_limit: str = "512m",
        cpu_limit: str = "0.5",
        pids_limit: int = 128,
    ) -> dict:
        """Create and start a sandbox container."""
        # On macOS, Docker bridge IPs aren't routable from the host.
        # Use published ports so the control plane can always reach the agent.
        container = self._docker().containers.run(
            image,
            detach=True,
            name=f"sandbox-{session_id[:12]}",
            labels={"ecs-sandbox.session_id": session_id},
            mem_limit=memory_limit,
            pids_limit=pids_limit,
            ports={"2222/tcp": None},  # random host port
            remove=False,
        )
        # Wait for port binding to appear (takes ~500ms on Docker Desktop)
        binding = []
        for _ in range(20):
            container.reload()
            binding = (
                container.attrs.get("NetworkSettings", {})
                .get("Ports", {})
                .get("2222/tcp")
                or []
            )
            if binding:
                break
            time.sleep(0.25)

        if binding:
            host_port = binding[0]["HostPort"]
            ip = f"127.0.0.1:{host_port}"
        else:
            ip = container.attrs["NetworkSettings"]["IPAddress"] + ":2222"

        print(f"[docker] container {session_id[:12]} → {ip}")
        return {"container_id": container.id, "container_ip": ip}

    async def remove_container(self, container_id: str):
        """Stop and remove a container."""
        try:
            container = self._docker().containers.get(container_id)
            container.stop(timeout=10)
            container.remove()
        except NotFound:
            pass

    async def list_sandbox_containers(self) -> list[dict]:
        """List all running sandbox containers."""
        containers = self._docker().containers.list(
            filters={"label": "ecs-sandbox.session_id"}
        )
        return [
            {
                "container_id": c.id,
                "session_id": c.labels.get("ecs-sandbox.session_id"),
                "status": c.status,
            }
            for c in containers
        ]
