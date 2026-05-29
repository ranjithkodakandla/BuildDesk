#!/usr/bin/env python3
"""Render reference vs BuildDesk PDF pages for fidelity comparison artifacts."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REF_PDF = ROOT / "artifacts/reference-pdf/BULL_OUTDOOR_Splashes_3sides_Polish.pdf"
BD_PDF = ROOT / "artifacts/reference-validation/builddesk_bull_outdoor_100-01.pdf"
OUT = ROOT / "artifacts/reference-validation"


def pdftoppm(pdf: Path, prefix: str, pages: str) -> None:
    if not pdf.exists():
        print(f"skip missing {pdf}", file=sys.stderr)
        return
    OUT.mkdir(parents=True, exist_ok=True)
    cmd = ["pdftoppm", "-png", "-r", "150"]
    if "-" in pages:
        a, b = pages.split("-")
        cmd.extend(["-f", a, "-l", b])
    cmd.extend([str(pdf), str(OUT / prefix)])
    subprocess.run(cmd, check=True)


def main() -> int:
    pdftoppm(REF_PDF, "reference-sheet", "1-1")
    pdftoppm(BD_PDF, "builddesk-v2-page", "1-5")
    print(f"Rendered comparison PNGs under {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
