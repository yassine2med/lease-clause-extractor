"""Command line interface for the lease clause extractor."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from . import core


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lease_clauses", description="Extract key terms from lease text files.")
    parser.add_argument("files", nargs="+", help="one or more .txt lease files")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    parser.add_argument("--csv", metavar="FILE", help="also write one row per lease to a CSV file")
    parser.add_argument("--show-source", action="store_true", help="print the sentence each value came from")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the extractor. Returns 0 on success, 1 when a file cannot be read."""
    args = build_parser().parse_args(argv)
    results: dict[str, dict[str, core.Found | None]] = {}
    for name in args.files:
        try:
            results[Path(name).name] = core.extract(Path(name).read_text(encoding="utf-8"))
        except OSError as error:
            print(f"error: {error}", file=sys.stderr)
            return 1
    if args.json:
        print(json.dumps({n: {k: (v.value if v else None) for k, v in r.items()} for n, r in results.items()}, indent=2))
    else:
        for name, found in results.items():
            print(name)
            for field in core.FIELDS:
                item = found[field]
                print(f"  {field:<24} {item.value if item else 'NOT FOUND'}")
                if args.show_source and item:
                    print(f"    from: {item.source}")
    if args.csv:
        with open(args.csv, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["file", *core.FIELDS])
            for name, found in results.items():
                writer.writerow([name, *[(found[f].value if found[f] else "") for f in core.FIELDS]])
    return 0
