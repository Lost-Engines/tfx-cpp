#!/usr/bin/env python3
"""Compare hardware-x87 vs SoftFloat acos/bank oracle probe dumps."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def parse(path: Path) -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    for line in path.read_text().splitlines():
        if not line or line.startswith("SKIP"):
            continue
        label, *fields = line.split()
        entry = {}
        for field in fields:
            key, _, value = field.partition("=")
            entry[key] = value
        rows[label] = entry
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hardware", type=Path)
    parser.add_argument("softfloat", type=Path)
    parser.add_argument(
        "--fields",
        # Guidance uses pi/2-asin acos and double(acos*bank_margin). asin /
        # atan2 dumps remain available via --fields for FPATAN chase work.
        default="acos_pi2,mid_pi2,mid_pi2_dbl",
        help="Comma-separated fields to compare (default: guidance bank path)",
    )
    args = parser.parse_args()
    fields = [f.strip() for f in args.fields.split(",") if f.strip()]

    hw = parse(args.hardware)
    soft = parse(args.softfloat)
    if not hw or not soft:
        print("empty oracle dump", file=sys.stderr)
        return 2
    if hw.keys() != soft.keys():
        only_hw = sorted(set(hw) - set(soft))
        only_soft = sorted(set(soft) - set(hw))
        print(f"label mismatch hw_only={only_hw[:5]} soft_only={only_soft[:5]}", file=sys.stderr)
        return 2

    mismatches = 0
    by_field: dict[str, int] = {f: 0 for f in fields}
    for label in hw:
        for field in fields:
            left = hw[label].get(field)
            right = soft[label].get(field)
            if left is None or right is None:
                print(f"missing field {field} on {label}", file=sys.stderr)
                return 2
            if left != right:
                mismatches += 1
                by_field[field] += 1
                if by_field[field] <= 8:
                    print(f"MISMATCH {label} {field} hw={left} soft={right}")

    print(f"labels={len(hw)} mismatches={mismatches}")
    for field, count in by_field.items():
        print(f"  {field}: {count}")
    if mismatches:
        print(
            "SoftFloat acos/bank path does not yet match hardware x87 extended bits.",
            file=sys.stderr,
        )
        return 1
    print("SoftFloat matches hardware x87 on the acos/bank oracle set.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
