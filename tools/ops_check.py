"""One-command operational readiness check."""

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_step(name, args):
    print("== {} ==".format(name))
    env = os.environ.copy()
    if args != ["tools/openai_smoke_test.py"]:
        env["OPENAI_API_KEY"] = ""
    result = subprocess.run(
        [sys.executable] + args,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    print(result.stdout.rstrip())
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main():
    os.environ.setdefault("CREDENTIAL_MASTER_KEY", "local-ops-check-master-key")
    run_step("runtime", ["tools/runtime_check.py"])
    run_step("env", ["tools/env_check.py"])
    run_step("compile", ["-m", "compileall", "-q", "."])
    run_step("stability", ["tools/stability_check.py"])
    run_step("http", ["tools/server_smoke_test.py"])
    run_step("fastapi", ["tools/fastapi_smoke_test.py"])
    print("OPS_CHECK_OK")


if __name__ == "__main__":
    main()
