"""Build the Vite frontend into api/static for Vercel Python hosting."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
STATIC = ROOT / "api" / "static"
PUBLIC = ROOT / "public"


def _copy_tree(src: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    shutil.copytree(src, dest, dirs_exist_ok=True)


def main() -> int:
    subprocess.check_call(["npm", "ci"], cwd=FRONTEND)
    subprocess.check_call(["npm", "run", "build"], cwd=FRONTEND)

    dist = FRONTEND / "dist"
    _copy_tree(dist, STATIC)
    _copy_tree(dist, PUBLIC)
    print(f"Copied {dist} -> {STATIC} and {PUBLIC}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
