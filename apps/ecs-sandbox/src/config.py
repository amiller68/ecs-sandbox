import os

from dotenv import load_dotenv


class Config:
    dev_mode: bool
    debug: bool
    listen_address: str
    listen_port: int

    # Auth
    sandbox_secret: str

    # Docker
    sandbox_image: str
    sandbox_memory_limit: str
    sandbox_cpu_limit: str
    sandbox_network: str
    sandbox_pids_limit: int

    # Session
    default_ttl_seconds: int
    max_containers: int

    # Storage
    db_path: str
    workspace_backend: str
    efs_workspace_root: str
    s3_workspace_bucket: str

    # Redis (for background jobs)
    redis_url: str

    def __init__(self):
        load_dotenv()

        self.dev_mode = os.getenv("DEV_MODE", "False") == "True"
        self.debug = os.getenv("DEBUG", "True") == "True"
        self.listen_address = os.getenv("LISTEN_ADDRESS", "0.0.0.0")
        self.listen_port = int(os.getenv("LISTEN_PORT", "8000"))

        # Auth
        self.sandbox_secret = os.getenv("SANDBOX_SECRET", "")
        if not self.sandbox_secret:
            import secrets

            self.sandbox_secret = secrets.token_urlsafe(32)
            print(f"Generated SANDBOX_SECRET: {self.sandbox_secret[:8]}...")

        # Docker
        self.sandbox_image = os.getenv("SANDBOX_IMAGE", "ecs-sandbox-agent:latest")
        self.sandbox_memory_limit = os.getenv("SANDBOX_MEMORY_LIMIT", "512m")
        self.sandbox_cpu_limit = os.getenv("SANDBOX_CPU_LIMIT", "0.5")
        self.sandbox_network = os.getenv("SANDBOX_NETWORK", "none")
        self.sandbox_pids_limit = int(os.getenv("SANDBOX_PIDS_LIMIT", "128"))

        # Session
        self.default_ttl_seconds = int(os.getenv("DEFAULT_TTL_SECONDS", "1800"))
        self.max_containers = int(os.getenv("MAX_CONTAINERS", "50"))

        # Storage
        self.db_path = os.getenv("DB_PATH", "/data/ecs-sandbox.db")
        self.workspace_backend = os.getenv("WORKSPACE_BACKEND", "none")
        self.efs_workspace_root = os.getenv("EFS_WORKSPACE_ROOT", "/data/workspaces")
        self.s3_workspace_bucket = os.getenv(
            "S3_WORKSPACE_BUCKET", "ecs-sandbox-workspaces"
        )

        # Redis
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
