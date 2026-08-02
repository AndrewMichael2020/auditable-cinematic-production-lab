from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

from .errors import PolicyError


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe(path: str | Path) -> dict:
    if not shutil.which("ffprobe"):
        raise PolicyError("ffprobe is required for media validation")
    result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format",
                             "-of", "json", str(path)], check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def contact_sheet(video: str | Path, output: str | Path) -> None:
    if not shutil.which("ffmpeg"):
        raise PolicyError("ffmpeg is required for contact sheets")
    subprocess.run(["ffmpeg", "-y", "-i", str(video), "-vf",
                    "fps=1,scale=320:-1,tile=5x1", "-frames:v", "1", str(output)],
                   check=True, capture_output=True)

