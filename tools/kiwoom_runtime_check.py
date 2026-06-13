"""Check the dedicated Kiwoom OpenAPI+ runtime prerequisites.

Run this inside the 32-bit `py37_32` environment on the Windows PC that has
Kiwoom OpenAPI+ installed.
"""

import os
import platform
import struct
import sys
from pathlib import Path


def print_check(name, ok, detail=""):
    status = "OK" if ok else "WARN"
    suffix = " {}".format(detail) if detail else ""
    print("{}={}{}".format(name, status, suffix))
    return ok


def try_import_pyqt():
    try:
        from PyQt5.QAxContainer import QAxWidget  # noqa: F401
        from PyQt5.QtWidgets import QApplication  # noqa: F401

        return True, "PyQt5 QAxContainer import succeeded"
    except Exception as exc:
        return False, "{}: {}".format(exc.__class__.__name__, exc)


def try_create_ocx():
    try:
        from PyQt5.QAxContainer import QAxWidget
        from PyQt5.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])
        widget = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        ok = not widget.isNull()
        detail = "created" if ok else "QAxWidget isNull"
        widget.clear()
        app.quit()
        return ok, detail
    except Exception as exc:
        return False, "{}: {}".format(exc.__class__.__name__, exc)


def main():
    bits = struct.calcsize("P") * 8
    version = sys.version_info
    openapi_dir = Path(r"C:\OpenAPI")
    ocx_path = openapi_dir / "khopenapi.ocx"

    print("PYTHON={}.{}.{}".format(version.major, version.minor, version.micro))
    print("PYTHON_BITS={}".format(bits))
    print("PLATFORM={}".format(platform.platform()))
    print("CONDA_DEFAULT_ENV={}".format(os.getenv("CONDA_DEFAULT_ENV", "")))

    checks = []
    checks.append(print_check("KIWOOM_PYTHON_32BIT", bits == 32))
    checks.append(print_check("KIWOOM_PYTHON_37_COMPAT", version.major == 3 and version.minor <= 7))
    checks.append(print_check("OPENAPI_DIR_EXISTS", openapi_dir.exists(), str(openapi_dir)))
    checks.append(print_check("KHOPENAPI_OCX_EXISTS", ocx_path.exists(), str(ocx_path)))

    pyqt_ok, pyqt_detail = try_import_pyqt()
    checks.append(print_check("PYQT_QAX_IMPORT", pyqt_ok, pyqt_detail))

    ocx_ok, ocx_detail = try_create_ocx()
    checks.append(print_check("KIWOOM_OCX_CREATE", ocx_ok, ocx_detail))

    print("KIWOOM_RUNTIME_CHECK_RESULT={}".format("PASS" if all(checks) else "WARN"))


if __name__ == "__main__":
    main()
