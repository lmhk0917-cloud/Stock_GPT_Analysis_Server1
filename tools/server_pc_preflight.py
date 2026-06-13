"""Preflight checks for moving this server to a dedicated Windows PC."""

import os
import platform
import socket
import struct
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import (  # noqa: E402
    ADMIN_API_TOKEN,
    CREDENTIAL_MASTER_KEY,
    OPENAI_API_KEY,
    PROJECT_ROOT,
    get_db_path,
)


def ok_line(name, ok, detail=""):
    status = "OK" if ok else "WARN"
    suffix = " {}".format(detail) if detail else ""
    print("{}={}{}".format(name, status, suffix))
    return ok


def command_exists(command):
    try:
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10,
        )
        return result.returncode == 0, result.stdout.strip().splitlines()[:3]
    except (OSError, subprocess.SubprocessError) as exc:
        return False, [str(exc)]


def can_bind(host, port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind((host, port))
        return True, ""
    except OSError as exc:
        return False, str(exc)
    finally:
        sock.close()


def main():
    bits = struct.calcsize("P") * 8
    db_path = get_db_path()
    data_dir = db_path.parent
    spool_dir = PROJECT_ROOT / "data" / "kiwoom_spool"
    scripts = [
        PROJECT_ROOT / "scripts" / "run_fastapi_server.ps1",
        PROJECT_ROOT / "scripts" / "run_kiwoom_legacy_worker.ps1",
        PROJECT_ROOT / "scripts" / "import_kiwoom_spool.ps1",
        PROJECT_ROOT / "scripts" / "run_kiwoom_live_probe.ps1",
    ]
    tools = [
        PROJECT_ROOT / "tools" / "ops_check.py",
        PROJECT_ROOT / "tools" / "kiwoom_runtime_check.py",
        PROJECT_ROOT / "tools" / "kiwoom_spool_status.py",
    ]

    print("PROJECT_ROOT={}".format(PROJECT_ROOT))
    print("DB_PATH={}".format(db_path))
    print("PLATFORM={}".format(platform.platform()))
    print("PYTHON={}.{}.{}".format(*sys.version_info[:3]))
    print("PYTHON_BITS={}".format(bits))

    checks = []
    checks.append(ok_line("SERVER_PYTHON_64BIT", bits == 64))
    checks.append(ok_line("SERVER_PYTHON_311_PLUS", sys.version_info[:2] >= (3, 11)))
    checks.append(ok_line("PROJECT_ROOT_MATCH", Path(PROJECT_ROOT).resolve() == ROOT.resolve()))
    checks.append(ok_line("ENV_LOCAL_EXISTS", (PROJECT_ROOT / ".env.local").exists()))
    checks.append(ok_line("CREDENTIAL_MASTER_KEY_SET", bool(CREDENTIAL_MASTER_KEY)))
    checks.append(ok_line("ADMIN_API_TOKEN_SET", bool(ADMIN_API_TOKEN)))
    checks.append(ok_line("OPENAI_API_KEY_SET", bool(OPENAI_API_KEY)))

    data_dir.mkdir(parents=True, exist_ok=True)
    spool_dir.mkdir(parents=True, exist_ok=True)
    checks.append(ok_line("DATA_DIR_WRITABLE", os.access(str(data_dir), os.W_OK), str(data_dir)))
    checks.append(ok_line("KIWOOM_SPOOL_DIR_WRITABLE", os.access(str(spool_dir), os.W_OK), str(spool_dir)))

    for path in scripts + tools:
        checks.append(ok_line("FILE_EXISTS:{}".format(path.relative_to(PROJECT_ROOT)), path.exists()))

    conda_ok, conda_lines = command_exists([r"C:\Users\lmhk2\anaconda3\Scripts\conda.exe", "--version"])
    checks.append(ok_line("CONDA_AVAILABLE", conda_ok, " ".join(conda_lines)))

    port_ok, port_error = can_bind("127.0.0.1", 8000)
    checks.append(ok_line("LOCAL_PORT_8000_AVAILABLE", port_ok, port_error))

    print("SERVER_PC_PREFLIGHT_RESULT={}".format("PASS" if all(checks) else "WARN"))


if __name__ == "__main__":
    main()
