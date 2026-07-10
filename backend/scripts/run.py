from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def configure_utf8_output() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            reconfigure(encoding="utf-8", errors="replace")


def venv_python() -> Path:
    if os.name == "nt":
        return BACKEND_ROOT / ".venv" / "Scripts" / "python.exe"
    return BACKEND_ROOT / ".venv" / "bin" / "python"


def ensure_virtual_environment() -> None:
    expected_python = venv_python()
    if not expected_python.exists():
        raise SystemExit(
            "Crowscap's virtual environment was not found. Create it with:\n"
            "  python -m venv .venv\n"
            '  .venv/Scripts/python -m pip install -e ".[dev]"'
        )

    if Path(sys.executable).resolve() == expected_python.resolve():
        return

    print(f"🔁 Switching to Crowscap virtual environment: {expected_python}")
    command = [str(expected_python), "-X", "utf8", str(Path(__file__).resolve()), *sys.argv[1:]]
    raise SystemExit(subprocess.call(command, cwd=BACKEND_ROOT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Crowscap FastAPI development server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--no-reload", action="store_true")
    return parser.parse_args()


def main() -> None:
    configure_utf8_output()
    ensure_virtual_environment()
    os.chdir(BACKEND_ROOT)

    import uvicorn

    args = parse_args()
    print(
        "🚀 Starting Crowscap backend "
        f"python={sys.executable} host={args.host} port={args.port} reload={not args.no_reload}"
    )
    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=not args.no_reload,
        reload_dirs=[str(BACKEND_ROOT)],
    )


if __name__ == "__main__":
    main()
