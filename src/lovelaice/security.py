from pathlib import Path
from typing import List, Union

class SecurityManager:
    def __init__(
        self,
        read_paths: List[Path],
        write_paths: List[Path],
        execute: Union[bool, List[str]] = False
    ):
        self.read_paths = [p.resolve() for p in read_paths]
        self.write_paths = [p.resolve() for p in write_paths]
        self.execute = execute

    def can_read(self, path: str) -> bool:
        target = Path(path).resolve()
        return any(target == base or base in target.parents for base in self.read_paths)

    def can_write(self, path: str) -> bool:
        target = Path(path).resolve()
        return any(target == base or base in target.parents for base in self.write_paths)

    def can_execute(self, command: str) -> bool:
        """
        Checks if a command is allowed based on the whitelist or global flag.
        """
        if self.execute is True:
            return True
        if not self.execute:
            return False

        # Whitelist check: extract the base command (e.g., 'git' from 'git commit')
        return command in self.execute