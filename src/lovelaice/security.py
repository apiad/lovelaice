from pathlib import Path
from typing import List


class SecurityManager:
    def __init__(
        self, read_paths: List[Path], write_paths: List[Path], allow_execute: bool
    ):
        # Normalize paths to absolute for reliable comparison
        self.read_paths = [p.resolve() for p in read_paths]
        self.write_paths = [p.resolve() for p in write_paths]
        self.allow_execute = allow_execute

    def _is_subpath(self, path: str, allowed_bases: List[Path]) -> bool:
        try:
            target = Path(path).resolve()
            return any(
                target == base or base in target.parents for base in allowed_bases
            )
        except Exception:
            return False

    def can_read(self, path: str) -> bool:
        """Checks if reading from the given path is permitted."""
        return self._is_subpath(path, self.read_paths)

    def can_write(self, path: str) -> bool:
        """Checks if writing to the given path is permitted."""
        return self._is_subpath(path, self.write_paths)

    def can_execute(self) -> bool:
        """Checks if shell command execution is permitted."""
        return self.allow_execute
