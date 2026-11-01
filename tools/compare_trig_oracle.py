#!/usr/bin/env python3
"""Compare hardware-x87 vs SoftFloat FSIN/FCOS/FPTAN/FPATAN oracle dumps."""

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


def rate(matches: int, total: int) -> float:
    return 0.0 if total == 0 else 100.0 * matches / total


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hardware", type=Path)
    parser.add_argument("softfloat", type=Path)
    args = parser.parse_args()

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

    ext_fields = {
        "trig": ("sin", "cos", "tan"),
        "atan2": ("atan2",),
    }
    dbl_fields = {
        "trig": ("sin_dbl", "cos_dbl", "tan_dbl"),
        "atan2": ("atan2_dbl",),
    }

    totals = {"trig": 0, "atan2": 0}
    ext_ok = {f: 0 for group in ext_fields.values() for f in group}
    dbl_ok = {f: 0 for group in dbl_fields.values() for f in group}

    for label, row in hw.items():
        group = "atan2" if label.startswith("atan2_") else "trig"
        totals[group] += 1
        for field in ext_fields[group]:
            if soft[label].get(field) == row.get(field):
                ext_ok[field] += 1
        for field in dbl_fields[group]:
            if soft[label].get(field) == row.get(field):
                dbl_ok[field] += 1

    print(f"labels={len(hw)} trig={totals['trig']} atan2={totals['atan2']}")
    for field, count in ext_ok.items():
        total = totals["atan2"] if field.startswith("atan2") else totals["trig"]
        print(f"  ext80 {field}: {count}/{total} ({rate(count, total):.2f}%)")
    for field, count in dbl_ok.items():
        total = totals["atan2"] if field.startswith("atan2") else totals["trig"]
        print(f"  double {field}: {count}/{total} ({rate(count, total):.2f}%)")

    # Match soft_x87_transcendental_test gates (double agreement floors).
    sin_pct = rate(dbl_ok["sin_dbl"], totals["trig"])
    cos_pct = rate(dbl_ok["cos_dbl"], totals["trig"])
    atan_pct = rate(dbl_ok["atan2_dbl"], totals["atan2"])
    ok = sin_pct >= 99.0 and cos_pct >= 99.0 and atan_pct >= 90.0
    if not ok:
        print(
            "SoftFloat trig double match below transcendental floors "
            f"(sin>={99} cos>={99} atan2>={90}).",
            file=sys.stderr,
        )
        return 1
    print("SoftFloat meets dual-build trig double-match floors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
