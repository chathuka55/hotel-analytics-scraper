"""Build the Vite frontend into ./public for Vercel static hosting."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FRONTEND = ROOT / "frontend"
PUBLIC = ROOT / "public"


def main() -> int:
    subprocess.check_call(["npm", "ci"], cwd=FRONTEND)
    subprocess.check_call(["npm", "run", "build"], cwd=FRONTEND)

    if PUBLIC.exists():
        shutil.rmtree(PUBLIC)
    PUBLIC.mkdir(parents=True)
    shutil.copytree(FRONTEND / "dist", PUBLIC, dirs_exist_ok=True)
    print(f"Copied {FRONTEND / 'dist'} -> {PUBLIC}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
