"""CLI entry point for the offline server MVP."""

import argparse
import json

from server.services import run_mock_analysis


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default=None)
    parser.add_argument("--use-gpt", action="store_true")
    args = parser.parse_args()

    results = run_mock_analysis(db_path=args.db_path, use_gpt=args.use_gpt)
    print(json.dumps({
        "status": "ok",
        "symbols": len(results),
        "events": sum(len(item["events"]) for item in results),
        "notifications": sum(len(item["notifications"]) for item in results),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
