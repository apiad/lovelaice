import os
import shutil
from pathlib import Path
from typing import List, Union
from ..core import Lovelaice


def list_dir(path: str, agent: Lovelaice) -> Union[List[str], str]:
    """
    Lists the contents of a directory.
    """
    if not agent.security.can_read(path):
        return f"Permission Denied: Cannot read directory at '{path}'."

    try:
        return os.listdir(path)
    except Exception as e:
        return f"Error listing directory: {str(e)}"


def read_file(path: str, agent: Lovelaice) -> str:
    """
    Reads the content of a file from the specified path.
    """
    if not agent.security.can_read(path):
        return f"Permission Denied: Cannot read file at '{path}'."

    try:
        return Path(path).read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {str(e)}"


def write_file(path: str, content: str, agent: Lovelaice) -> str:
    """
    Writes content to a file. Overwrites if the file exists.
    """
    if not agent.security.can_write(path):
        return f"Permission Denied: Cannot write to file at '{path}'."

    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)  # Ensure parent exists
        p.write_text(content, encoding="utf-8")
        return f"Successfully wrote to '{path}'."
    except Exception as e:
        return f"Error writing file: {str(e)}"


def create_dir(path: str, agent: Lovelaice) -> str:
    """
    Creates a new directory and any necessary intermediate directories.
    """
    if not agent.security.can_write(path):
        return f"Permission Denied: Cannot create directory at '{path}'."

    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        return f"Directory '{path}' created successfully."
    except Exception as e:
        return f"Error creating directory: {str(e)}"


def delete_path(path: str, agent: Lovelaice) -> str:
    """
    Deletes a file or an empty directory.
    """
    if not agent.security.can_write(path):
        return f"Permission Denied: Cannot delete at '{path}'."

    try:
        p = Path(path)
        if p.is_file():
            p.unlink()
        elif p.is_dir():
            p.rmdir()
        return f"Successfully deleted '{path}'."
    except Exception as e:
        return f"Error deleting: {str(e)}"
