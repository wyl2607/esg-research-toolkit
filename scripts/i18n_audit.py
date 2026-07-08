#!/usr/bin/env python3
"""
i18n key audit script for ESG Toolkit frontend locales.

Scans en/de/zh.json for key differences (missing/extra keys in nested objects).
Reports counts and lists. Exits non-zero if diffs found (for CI).

Usage:
  python scripts/i18n_audit.py
  python scripts/i18n_audit.py --json  # machine readable

Run from project root.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, Set

LOCALES_DIR = Path("frontend/src/i18n/locales")
LANGS = ["en", "de", "zh"]


def collect_keys(obj: Any, prefix: str = "") -> Set[str]:
    """Recursively collect dotted keys from nested dict."""
    keys: Set[str] = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            full = f"{prefix}.{k}" if prefix else k
            keys.add(full)
            keys.update(collect_keys(v, full))
    return keys


def load_locale(lang: str) -> Dict[str, Any]:
    path = LOCALES_DIR / f"{lang}.json"
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def audit() -> Dict[str, Any]:
    all_keys: Dict[str, Set[str]] = {}
    for lang in LANGS:
        data = load_locale(lang)
        all_keys[lang] = collect_keys(data)

    common = set.intersection(*all_keys.values())
    report = {
        "total_common": len(common),
        "per_lang": {},
        "has_diffs": False,
    }

    for lang in LANGS:
        others = set.union(*(all_keys[l] for l in LANGS if l != lang))
        missing = sorted(others - all_keys[lang])
        extra = sorted(all_keys[lang] - others)
        lang_report = {
            "count": len(all_keys[lang]),
            "missing": missing,
            "extra": extra,
        }
        report["per_lang"][lang] = lang_report
        if missing or extra:
            report["has_diffs"] = True

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit i18n keys across en/de/zh")
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    args = parser.parse_args()

    report = audit()

    if args.json:
        # Pure JSON for machines/CI parsing. No extra text.
        print(json.dumps(report, indent=2, ensure_ascii=False))
        sys.exit(1 if report["has_diffs"] else 0)
    else:
        print(f"i18n key audit: {report['total_common']} common keys across {LANGS}")
        for lang, info in report["per_lang"].items():
            miss = len(info["missing"])
            ext = len(info["extra"])
            print(f"  {lang}: {info['count']} keys, missing={miss}, extra={ext}")
            if miss:
                print(f"    missing e.g.: {info['missing'][:5]}")
            if ext:
                print(f"    extra e.g.: {info['extra'][:5]}")

        if report["has_diffs"]:
            print("\nDIFFS DETECTED — i18n keys are not aligned.")
            sys.exit(1)
        else:
            print("\nAll i18n keys aligned. Good.")
            sys.exit(0)


if __name__ == "__main__":
    main()
