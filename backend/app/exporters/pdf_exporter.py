import io
import math
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor

from app.services.geometry_builder import GeometryBuildResult
from app.geometry.primitives import Point


class PdfExporter:
    """
    Exports GeometryBuildResult to a printable 8.5x11 landscape PDF.
    """

    def __init__(self):
        self.page_size = landscape(letter)  # 11 x 8.5 inches -> 792 x 612 pts
        self.width, self.height = self.page_size
        self.margin = 0.5 * inch

        # Colors similar to SVG
        self.bg_color = HexColor("#ffffff")
        self.fill_color = HexColor("#f0f4f8")
        self.stroke_color = HexColor("#1a2332")
        self.dim_color = HexColor("#4a7fb5")
        self.text_color = HexColor("#2d5f8a")
        self.seam_color = HexColor("#1a2332")

    def export(self, result: GeometryBuildResult, shape_type: str = "Geometry") -> bytes:
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=self.page_size)
        c.setTitle(f"BuildDesk Export - {shape_type}")

        # ── 1. Page Background & Title Block ──────────────────────────────────
        self._draw_title_block(c, result, shape_type)

        # ── 2. Calculate Scale & Transform ────────────────────────────────────
        # Drawing area inside margins and below the title block header (1 inch)
        draw_x = self.margin
        draw_y = self.margin
        draw_w = self.width - 2 * self.margin
        draw_h = self.height - 2 * self.margin - 1.0 * inch

        # Find geometry bounding box
        min_x, max_x, min_y, max_y = 0.0, 0.0, 0.0, 0.0
        points = []
        for rect in result.rectangles:
            points.extend([
                rect.origin,
                Point(x=rect.origin.x + rect.width, y=rect.origin.y),
                Point(x=rect.origin.x, y=rect.origin.y + rect.height),
                Point(x=rect.origin.x + rect.width, y=rect.origin.y + rect.height)
            ])
        for poly in result.polylines:
            points.extend(poly.points)
        for line in result.lines:
            points.extend([line.start, line.end])
        for dim in result.dimension_lines:
            points.extend([dim.start, dim.end])
        for circ in result.circles:
            points.extend([
                Point(x=circ.center.x - circ.radius, y=circ.center.y - circ.radius),
                Point(x=circ.center.x + circ.radius, y=circ.center.y + circ.radius)
            ])
            
        if points:
            min_x = min(p.x for p in points)
            max_x = max(p.x for p in points)
            min_y = min(p.y for p in points)
            max_y = max(p.y for p in points)
            
        # Ensure we have at least some size to avoid div by zero
        geom_w = max(max_x - min_x, 1.0)
        geom_h = max(max_y - min_y, 1.0)

        # We add 10% padding around the geometry within the drawing area
        geom_w_padded = geom_w * 1.2
        geom_h_padded = geom_h * 1.2

        scale = min(draw_w / geom_w_padded, draw_h / geom_h_padded)

        # Center offset
        cx = draw_x + (draw_w - (geom_w * scale)) / 2.0 - (min_x * scale)
        cy = draw_y + (draw_h - (geom_h * scale)) / 2.0 - (min_y * scale)

        c.saveState()
        # Translate to center, then we scale. Reportlab native is y-up.
        c.translate(cx, cy)
        c.scale(scale, scale)

        # ── 3. Draw Primitives ────────────────────────────────────────────────
        # A. Rectangles
        for rect in result.rectangles:
            c.setFillColor(self.fill_color)
            c.setStrokeColor(self.stroke_color)
            if rect.metadata.get("role") == "bounding_box":
                # Don't fill bounding boxes, just draw dashed or thin stroke
                c.setLineWidth(0.5 / scale)
                c.setDash([5 / scale, 5 / scale])
                c.setFillColor(HexColor("#ffffff")) # clear
            else:
                c.setLineWidth(1.0 / scale)
                c.setDash([])
            
            c.rect(rect.origin.x, rect.origin.y, rect.width, rect.height, stroke=1, fill=1)

        # B. Polylines
        for poly in result.polylines:
            c.setStrokeColor(self.stroke_color)
            c.setLineWidth(2.0 / scale)
            c.setDash([])
            
            path = c.beginPath()
            if poly.points:
                path.moveTo(poly.points[0].x, poly.points[0].y)
                for p in poly.points[1:]:
                    path.lineTo(p.x, p.y)
                if poly.closed:
                    path.close()
            c.drawPath(path, stroke=1, fill=0)

        # C. Circles
        for circ in result.circles:
            c.setStrokeColor(self.stroke_color)
            c.setLineWidth(1.0 / scale)
            if circ.metadata.get("dash"):
                c.setDash([5 / scale, 5 / scale])
            else:
                c.setDash([])
            c.circle(circ.center.x, circ.center.y, circ.radius, stroke=1, fill=0)

        # D. Lines (e.g. seams)
        for line in result.lines:
            c.setStrokeColor(self.seam_color)
            c.setLineWidth(1.5 / scale)
            dash = line.metadata.get("stroke_dasharray")
            if dash:
                parts = [float(x) / scale for x in dash.split(",")]
                c.setDash(parts)
            else:
                c.setDash([])
            c.line(line.start.x, line.start.y, line.end.x, line.end.y)

        # E. Dimension Lines
        c.setDash([])
        for dim in result.dimension_lines:
            c.setStrokeColor(self.dim_color)
            c.setLineWidth(1.0 / scale)
            c.line(dim.start.x, dim.start.y, dim.end.x, dim.end.y)
            
            # Simple tick marks
            dx = dim.end.x - dim.start.x
            dy = dim.end.y - dim.start.y
            length = math.hypot(dx, dy)
            if length > 0:
                ux, uy = dx / length, dy / length
                nx, ny = -uy, ux # normal
                tick_len = 4.0 / scale
                c.line(dim.start.x - nx * tick_len, dim.start.y - ny * tick_len,
                       dim.start.x + nx * tick_len, dim.start.y + ny * tick_len)
                c.line(dim.end.x - nx * tick_len, dim.end.y - ny * tick_len,
                       dim.end.x + nx * tick_len, dim.end.y + ny * tick_len)

            # Text
            cx_dim = (dim.start.x + dim.end.x) / 2.0
            cy_dim = (dim.start.y + dim.end.y) / 2.0
            # Offset text slightly
            cx_dim += nx * (6.0 / scale)
            cy_dim += ny * (6.0 / scale)
            
            c.saveState()
            c.translate(cx_dim, cy_dim)
            angle = math.degrees(math.atan2(dy, dx))
            # Keep text upright
            if angle > 90 or angle < -90:
                angle += 180
            c.rotate(angle)
            
            # Draw text
            c.setFillColor(self.text_color)
            font_size = 10.0 / scale
            c.setFont("Helvetica", font_size)
            c.drawCentredString(0, 0, dim.display_text)
            c.restoreState()

        # F. Annotations
        for ann in result.annotations:
            c.setFillColor(self.text_color)
            font_size = (ann.font_size or 12.0) / scale
            font_name = "Helvetica-Bold" if getattr(ann, "bold", False) else "Helvetica"
            c.setFont(font_name, font_size)
            
            c.saveState()
            c.translate(ann.position.x, ann.position.y)
            c.drawCentredString(0, -font_size * 0.3, ann.text)
            c.restoreState()

        c.restoreState()
        
        # Finish
        c.showPage()
        c.save()
        
        return buffer.getvalue()

    def _draw_title_block(self, c: canvas.Canvas, result: GeometryBuildResult, shape_type: str):
        # Top-left metadata
        c.setFillColor(self.stroke_color)
        c.setFont("Helvetica-Bold", 16)
        c.drawString(self.margin, self.height - self.margin - 12, "BuildDesk Production Drawing")
        
        c.setFont("Helvetica", 10)
        y = self.height - self.margin - 28
        c.drawString(self.margin, y, f"Shape: {shape_type.upper()}")
        y -= 14
        c.drawString(self.margin, y, f"Project: {result.geometry.project_id}")
        
        # Top-right summary
        c.setFont("Helvetica-Bold", 10)
        c.drawRightString(self.width - self.margin, self.height - self.margin - 12, "METADATA SUMMARY")
        
        c.setFont("Helvetica", 10)
        y = self.height - self.margin - 28
        c.drawRightString(self.width - self.margin, y, f"Total Area: {result.geometry.computed_area:.2f} sq in")
        y -= 14
        c.drawRightString(self.width - self.margin, y, f"Total Perimeter: {result.geometry.computed_perimeter:.2f} in")
        y -= 14
        pieces_count = len(result.geometry.pieces)
        c.drawRightString(self.width - self.margin, y, f"Pieces: {pieces_count}")
        
        # Watermark/footer
        c.setFont("Helvetica", 8)
        c.setFillColor(HexColor("#999999"))
        c.drawCentredString(self.width / 2.0, self.margin / 2.0, "Generated by BuildDesk - Confidential")
        
        # Divider line
        c.setStrokeColor(HexColor("#cccccc"))
        c.setLineWidth(1)
        c.line(self.margin, self.height - self.margin - 1.0 * inch + 10, 
               self.width - self.margin, self.height - self.margin - 1.0 * inch + 10)
