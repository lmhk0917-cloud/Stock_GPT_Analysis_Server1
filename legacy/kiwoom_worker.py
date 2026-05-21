"""Kiwoom OpenAPI+ legacy worker placeholder.

Run this only in the dedicated 32-bit Python environment that can load
QAxWidget/OpenAPI+ COM controls. The main server runtime should not import this
module.
"""


def main():
    raise SystemExit(
        "Kiwoom legacy worker is intentionally isolated. "
        "Implement QAxWidget login/collection here only if Kiwoom OpenAPI+ is selected."
    )


if __name__ == "__main__":
    main()
