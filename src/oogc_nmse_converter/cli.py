"""Command line interface for oogc-nmse-converter."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .converter import (
    ConversionError,
    convert_file,
    default_output_path,
    extract_members,
    member_metadata,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="oogc-nmse-convert",
        description="Convert OOGC / NMS Model IO .nmsship ZIP exports to NMSE wrapper JSON.",
    )
    parser.add_argument("input", type=Path, help="Input .nmsship or ZIP file")
    parser.add_argument("-o", "--output", type=Path, help="Output wrapper JSON path")
    parser.add_argument(
        "--format",
        choices=("json", "nmscorv"),
        default="json",
        help="Output format: json writes .nmse.json, nmscorv writes .nmscorv",
    )
    parser.add_argument(
        "--nmscorv",
        action="store_const",
        const="nmscorv",
        dest="format",
        help="Shortcut for --format nmscorv",
    )
    parser.add_argument("--compact", action="store_true", help="Write compact JSON instead of pretty JSON")
    parser.add_argument(
        "--omit-default-ccd",
        action="store_true",
        help="Omit ccd.json when it appears to contain only default/blank values",
    )
    parser.add_argument("--extract", type=Path, metavar="DIR", help="Extract known JSON members to DIR")
    parser.add_argument("--force", action="store_true", help="Allow overwriting output files")
    parser.add_argument(
        "--metadata",
        action="store_true",
        help="Print ZIP member sizes and top-level JSON keys to stderr",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    output_path = args.output if args.output is not None else default_output_path(args.input, args.format)
    if output_path.exists() and not args.force:
        parser.error(f"refusing to overwrite existing file: {output_path} (use --force)")

    try:
        if args.metadata:
            print(json.dumps(member_metadata(args.input), indent=2), file=sys.stderr)

        if args.extract is not None:
            extracted = extract_members(args.input, args.extract, force=args.force)
            for path in extracted:
                print(f"extracted {path}", file=sys.stderr)

        written = convert_file(
            args.input,
            output_path,
            output_format=args.format,
            pretty=not args.compact,
            include_default_ccd=not args.omit_default_ccd,
        )
    except ConversionError as exc:
        parser.exit(2, f"error: {exc}\n")

    print(written)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
