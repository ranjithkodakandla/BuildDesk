"""
BuildDesk Exporters Package
============================
Output generation services that consume GeometryBuildResult.

    from app.exporters import SvgExporter

Current exporters:
    SvgExporter  – generates SVG drawing from geometry primitives

Future exporters (Phase 2+):
    PdfExporter  – generates builder/installer/manufacturer PDFs
    DxfExporter  – generates DXF CAD files
"""

from app.exporters.svg_exporter import SvgExporter

__all__ = ["SvgExporter"]
