"""Check whether the current Python runtime is suitable for the server."""

import platform
import struct
import sys


def main():
    bits = struct.calcsize("P") * 8
    version = sys.version_info
    print("python={}.{}.{}".format(version.major, version.minor, version.micro))
    print("bits={}".format(bits))
    print("implementation={}".format(platform.python_implementation()))

    server_ok = bits == 64 and (version.major, version.minor) >= (3, 11)
    if server_ok:
        print("SERVER_RUNTIME=OK")
    else:
        print("SERVER_RUNTIME=LEGACY_OR_DEV_ONLY")
        print("Recommended server runtime: Python 3.11+ 64-bit")

    if bits == 32 and (version.major, version.minor) <= (3, 7):
        print("KIWOOM_LEGACY_RUNTIME=OK")
    else:
        print("KIWOOM_LEGACY_RUNTIME=NOT_DEDICATED")


if __name__ == "__main__":
    main()
