import os
from pathlib import Path


async def read(path: str) -> str:
    """
    Read the entire contents of a text file and return it as a string.

    Use this whenever you need to inspect a file's contents — source code,
    configuration, prose, anything text. Binary files are not supported.
    """
    return Path(path).read_text(encoding="utf-8")


async def write(path: str, content: str) -> str:
    """
    Write content to a file, overwriting it if it already exists.
    Creates parent directories as needed.

    Use this for full-file rewrites or for creating new files. For surgical
    changes inside an existing file, prefer `edit` so the rest of the file
    is preserved verbatim.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"wrote {len(content)} chars to {path}"


async def edit(path: str, old: str, new: str) -> str:
    """
    Replace the first exact occurrence of `old` with `new` in the file at
    `path`. Both `old` and `new` are matched literally (no regex).

    Fails if `old` does not appear in the file, or if it appears more than
    once — in that case, include more surrounding context in `old` so the
    match is unique.
    """
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count == 0:
        raise ValueError(f"`old` not found in {path}")
    if count > 1:
        raise ValueError(
            f"`old` appears {count} times in {path}; provide more context to disambiguate"
        )
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    return f"edited {path}"


async def list_dir(path: str = ".") -> list[str]:
    """
    List the entries in a directory. Returns a flat list of names
    (not recursive). Use `bash("find ...")` for recursive listings.
    """
    return sorted(os.listdir(path))
