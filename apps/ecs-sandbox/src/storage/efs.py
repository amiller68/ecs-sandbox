"""EFS workspace storage backend."""

import shutil
from pathlib import Path


class EFSStorage:
    def __init__(self, root: str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def workspace_path(self, session_id: str) -> Path:
        path = self.root / session_id
        path.mkdir(parents=True, exist_ok=True)
        return path

    def cleanup(self, session_id: str):
        path = self.root / session_id
        if path.exists():
            shutil.rmtree(path)
