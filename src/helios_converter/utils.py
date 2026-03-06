import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def read_file(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    try:
        content = path.read_text(encoding="utf-8")
        logger.info("Read %s (%d characters)", path, len(content))
        return content
    except OSError as e:
        raise RuntimeError(f"Error reading {path}") from e


def write_file(path: Path, content: str) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        logger.info("Saved to %s", path)
    except OSError as e:
        raise RuntimeError(f"Error writing {path}") from e


def scan_directory(directory: Path, extensions: list[str] | None = None) -> list[Path]:
    if not directory.exists() or not directory.is_dir():
        logger.error("Directory not found: %s", directory)
        return []
    files = [
        f for f in directory.rglob("*")
        if f.is_file() and (extensions is None or f.suffix in extensions)
    ]
    return sorted(files)
