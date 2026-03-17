import sys
import uvicorn

from src.config import Config
from src.server import create_app

config = Config()
app = create_app(config)


def main() -> int:
    try:
        print(f"Starting ecs-sandbox on {config.listen_address}:{config.listen_port}")

        if config.dev_mode:
            uvicorn.run(
                "src.__main__:app",
                host=config.listen_address,
                port=config.listen_port,
                reload=True,
                reload_dirs=["src", "../../packages/ecs-sandbox-client/src"],
            )
        else:
            uvicorn.run(
                app,
                host=config.listen_address,
                port=config.listen_port,
            )
        return 0
    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
