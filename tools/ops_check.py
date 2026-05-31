"""One-command operational readiness check."""

import argparse
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_step(name, args, live_openai=False):
    print("== {} ==".format(name))
    env = os.environ.copy()
    if not live_openai:
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
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live-openai",
        action="store_true",
        help="include a real OpenAI API smoke test using OPENAI_API_KEY",
    )
    args = parser.parse_args()

    os.environ.setdefault("CREDENTIAL_MASTER_KEY", "local-ops-check-master-key")
    run_step("runtime", ["tools/runtime_check.py"])
    run_step("env", ["tools/env_check.py"], live_openai=args.live_openai)
    run_step("migrations", ["tools/migration_check.py"])
    run_step("compile", ["-m", "compileall", "-q", "."])
    run_step("kiwoom-spool", ["tools/kiwoom_spool_smoke_test.py"])
    run_step("stability", ["tools/stability_check.py"])
    run_step("http", ["tools/server_smoke_test.py"])
    run_step("fastapi", ["tools/fastapi_smoke_test.py"])
    run_step("admin-ui", ["tools/admin_ui_smoke_test.py"])
    run_step("client-ui", ["tools/client_ui_smoke_test.py"])
    if args.live_openai:
        run_step("openai", ["tools/openai_smoke_test.py"], live_openai=True)
    print("OPS_CHECK_OK")


if __name__ == "__main__":
    main()
