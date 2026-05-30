"""Phase 17 PDF layout helpers."""

from app.exporters.package_pdf_exporter import PackagePdfExporter
from app.models.fabrication import EdgeTreatment, EdgeType, Part, PartType, Position
from app.models.fabrication import Dimensions
import uuid


def test_edge_compact_codes():
    part = Part(
        assembly_id=uuid.uuid4(),
        part_type=PartType.MAIN_TOP,
        name="A",
        dimensions=Dimensions(length=24, depth=25),
        edges=[
            EdgeTreatment(part_id=uuid.uuid4(), position=Position.BACK, edge_type=EdgeType.POLISHED),
            EdgeTreatment(part_id=uuid.uuid4(), position=Position.FRONT, edge_type=EdgeType.RAW),
            EdgeTreatment(part_id=uuid.uuid4(), position=Position.LEFT, edge_type=EdgeType.POLISHED),
            EdgeTreatment(part_id=uuid.uuid4(), position=Position.RIGHT, edge_type=EdgeType.POLISHED),
        ],
    )
    compact = PackagePdfExporter()._edge_compact(part)
    assert "B=P" in compact
    assert "F=R" in compact
    assert "L=P" in compact
