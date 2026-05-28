"""
Demo PDF Generator
==================
Creates printable 8.5x11 PDF output files for demo shapes, saving them to tests/output/.
Useful for manual visual inspection of the exporter logic.

Usage:
    python tools/generate_demo_pdf.py rectangle
    python tools/generate_demo_pdf.py island
    python tools/generate_demo_pdf.py vanity
    python tools/generate_demo_pdf.py straight_kitchen
    python tools/generate_demo_pdf.py l_kitchen
    python tools/generate_demo_pdf.py all
"""

import argparse
import os
import sys
import uuid

# Ensure backend/ is in sys.path when run directly
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.api.demo import _DEMO_PAYLOADS
from app.exporters.pdf_exporter import PdfExporter
from app.geometry.shapes import SHAPE_REGISTRY
from app.services.geometry_builder import GeometryBuilder
from app.services.template_resolver import TemplateResolver

_DEMO_PROJECT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
_DEMO_TENANT_ID  = uuid.UUID("00000000-0000-0000-0000-000000000002")

def main():
    parser = argparse.ArgumentParser(description="Generate demo PDF files")
    parser.add_argument("shape", help="Shape type to generate (e.g. 'rectangle', 'island', 'all')")
    parser.add_argument("--out-dir", default="tests/output", help="Output directory")
    args = parser.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)

    targets = list(_DEMO_PAYLOADS.keys()) if args.shape == "all" else [args.shape]

    resolver = TemplateResolver()
    builder  = GeometryBuilder()
    exporter = PdfExporter()

    count = 0
    for shape_type in targets:
        if shape_type not in _DEMO_PAYLOADS:
            print(f"  ✗  Unknown demo shape: {shape_type}")
            continue

        template = SHAPE_REGISTRY.get(shape_type)
        dims = _DEMO_PAYLOADS[shape_type]
        
        res = resolver.resolve(template, dims)
        r_build = builder.build(template, res, _DEMO_PROJECT_ID, _DEMO_TENANT_ID)
        
        pdf_bytes = exporter.export(r_build, shape_type)
        
        out_path = os.path.join(args.out_dir, f"{shape_type}_demo.pdf")
        with open(out_path, "wb") as f:
            f.write(pdf_bytes)
            
        print(f"  ✓  {shape_type:<20} → {out_path}")
        count += 1

    print(f"\nGenerated {count} PDF(s).")

if __name__ == "__main__":
    main()
