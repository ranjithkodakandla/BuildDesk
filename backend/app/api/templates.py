"""
Template Generation API  (Phase 4)
====================================
REST endpoints for the template-driven fabrication workflow.

Routes:
    GET  /api/v1/templates
        → list all registered templates with metadata + UI contracts

    GET  /api/v1/templates/{template_id}
        → single template detail (defaults, UI contract, supported features)

    POST /api/v1/templates/generate
        → SimpleTemplateConfig body → Assembly JSON response (stateless)

    POST /api/v1/templates/preview
        → SimpleTemplateConfig body → SVG drawing (image/svg+xml)

    POST /api/v1/templates/pdf
        → SimpleTemplateConfig body → single-page PDF (application/pdf)

All generate/preview/pdf endpoints are stateless — no database writes.
Phase 5 will add persistence (save Assembly and return assembly_id).

Pipeline (shared by generate / preview / pdf):
    TemplateGenerateRequest
        → to_simple_config(tenant_id)
        → SimpleConfigMapper.to_template_config()
        → ConfigurationService.validate()          ← feature compatibility
        → registry.build(config)                   ← Assembly
        → [AssemblyResponse JSON | SVG | PDF]      ← via existing exporters
"""
from __future__ import annotations

import io
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen import canvas as rl_canvas
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_tenant, require_active_user
from app.dependencies import get_db
from app.exporters.assembly_svg_exporter import AssemblySvgExporter
from app.exporters.fabrication_drawing_engine import (
    DIM_INCH_MM,
    FabricationDrawingEngine,
)
from app.models.fabrication import Assembly
from app.models.user import User
from app.repositories.fabrication_repository import FabricationRepository
from app.repositories.hierarchy_repository import ProjectHierarchyRepository
from app.services.fabrication_service import FabricationService
from app.templates import registry
from app.templates.config_service import ConfigurationService, ConfigValidationResult
from app.templates.simple_config import (
    SimpleEdgeFinish,
    SimpleSinkConfig,
    SimpleSplashConfig,
    SimpleTemplateConfig,
)
from app.templates.simple_mapper import (
    TemplateUIContract,
    UIFieldSpec,
    get_ui_contract,
    mapper,
)
from app.api.template_schemas import TemplateDefinitionResponse

# ---------------------------------------------------------------------------
# Singleton services
# ---------------------------------------------------------------------------

_svc         = ConfigurationService(registry)
_svg_exp     = AssemblySvgExporter()
_draw_engine = FabricationDrawingEngine()

router = APIRouter(prefix="/templates", tags=["templates"])


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------

class TemplateGenerateRequest(BaseModel):
    """
    Shared request body for /generate, /preview, and /pdf endpoints.

    project_id is optional in Phase 4 (all endpoints are stateless).
    It will become required in Phase 5 when assemblies are persisted.

    tenant_id is NOT included — it is injected from the authenticated
    request context by the route handler.
    """
    template_id: str = Field(min_length=1, max_length=100)
    name:         str = Field(default="", max_length=200)
    project_id:   Optional[uuid.UUID] = Field(
        default=None,
        description="Project to associate the assembly with (required in Phase 5)",
    )
    unit_id:      Optional[uuid.UUID] = None
    unit_type_id: Optional[uuid.UUID] = None

    # Dimensions
    width:     float = Field(gt=0,    description="Horizontal span in inches")
    depth:     float = Field(gt=0,    description="Front-to-back depth in inches")
    thickness: float = Field(default=1.25, gt=0, le=6.0)

    # Options
    mirror:      bool               = False
    edge_finish: SimpleEdgeFinish   = SimpleEdgeFinish.POLISHED
    splash:      SimpleSplashConfig = Field(default_factory=SimpleSplashConfig)
    sink:        SimpleSinkConfig   = Field(default_factory=SimpleSinkConfig)

    def to_simple_config(self, tenant_id: uuid.UUID) -> SimpleTemplateConfig:
        return SimpleTemplateConfig(
            template_id=self.template_id,
            project_id=self.project_id or uuid.uuid4(),   # dummy for stateless build
            tenant_id=tenant_id,
            name=self.name,
            unit_id=self.unit_id,
            unit_type_id=self.unit_type_id,
            width=self.width,
            depth=self.depth,
            thickness=self.thickness,
            mirror=self.mirror,
            edge_finish=self.edge_finish,
            splash=self.splash,
            sink=self.sink,
        )


class UIFieldResponse(BaseModel):
    key:        str
    label:      str
    field_type: str
    visible:    bool
    required:   bool
    unit:       Optional[str]
    options:    Optional[List[str]]
    hint:       Optional[str]


class TemplateUIContractResponse(BaseModel):
    template_id:    str
    display_name:   str
    category:       str
    dimension_term: str
    fields:         List[UIFieldResponse]


class TemplateDetailResponse(BaseModel):
    """Full template detail returned by GET /templates/{id}."""
    definition:  TemplateDefinitionResponse
    ui_contract: TemplateUIContractResponse


class AssemblyPartResponse(BaseModel):
    part_id:    uuid.UUID
    part_type:  str
    name:       str
    length:     float   # Dimensions.length (horizontal span)
    depth:      float   # Dimensions.depth  (front-to-back)
    thickness:  Optional[float]
    cutout_count: int
    splash_count: int


class AssemblyGenerateResponse(BaseModel):
    """
    Assembly returned by POST /templates/generate.

    Intentionally simplified compared to AssemblyResponse — only the
    fabrication-relevant fields. Full Assembly JSON is available through
    the existing /assemblies/{id} endpoint once saved (Phase 5).
    """
    assembly_id:   uuid.UUID
    template_id:   str
    name:          str
    assembly_type: str
    variant:       str
    part_count:    int
    parts:         List[AssemblyPartResponse]
    warnings:      List[str]


class ValidationErrorResponse(BaseModel):
    detail:   str
    errors:   List[str]
    warnings: List[str]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _contract_response(contract: TemplateUIContract) -> TemplateUIContractResponse:
    return TemplateUIContractResponse(
        template_id=contract.template_id,
        display_name=contract.display_name,
        category=contract.category,
        dimension_term=contract.dimension_term,
        fields=[
            UIFieldResponse(
                key=f.key,
                label=f.label,
                field_type=f.field_type,
                visible=f.visible,
                required=f.required,
                unit=f.unit,
                options=f.options,
                hint=f.hint,
            )
            for f in contract.fields
        ],
    )


def _assembly_response(
    assembly: Assembly,
    template_id: str,
    warnings: List[str],
) -> AssemblyGenerateResponse:
    parts = [
        AssemblyPartResponse(
            part_id=p.part_id,
            part_type=p.part_type.value,
            name=p.name,
            length=p.dimensions.length,
            depth=p.dimensions.depth,
            thickness=p.dimensions.thickness,
            cutout_count=len(p.cutouts),
            splash_count=len(p.splashes),
        )
        for p in assembly.parts
    ]
    return AssemblyGenerateResponse(
        assembly_id=assembly.assembly_id,
        template_id=template_id,
        name=assembly.name,
        assembly_type=assembly.assembly_type.value,
        variant=assembly.variant.value,
        part_count=len(assembly.parts),
        parts=parts,
        warnings=warnings,
    )


def _build_assembly_from_request(
    body: TemplateGenerateRequest,
    tenant_id: uuid.UUID,
) -> tuple[Assembly, ConfigValidationResult]:
    """
    Core pipeline: TemplateGenerateRequest → Assembly.
    Returns (assembly, validation_result) so warnings can be surfaced.
    Raises HTTPException on validation failure.
    """
    simple = body.to_simple_config(tenant_id)

    # Map simple → internal TemplateConfig
    try:
        tc = mapper.to_template_config(simple)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Config mapping failed: {exc}",
        )

    # Validate template compatibility
    result = _svc.validate(tc)
    if not result.valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "message": "Template configuration validation failed.",
                "errors":  result.errors,
                "warnings": result.warnings,
            },
        )

    # Build assembly
    try:
        assembly = registry.build(tc)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Assembly build error: {exc}",
        )

    return assembly, result


def _render_pdf(assembly: Assembly) -> bytes:
    """Render a single-page A3-landscape PDF using FabricationDrawingEngine."""
    buf    = io.BytesIO()
    page   = landscape(letter)
    pw, ph = page
    margin = 40.0

    c = rl_canvas.Canvas(buf, pagesize=page)
    _draw_engine.draw_assembly(
        c,
        assembly,
        zone_x=margin,
        zone_y=margin,
        zone_w=pw - 2 * margin,
        zone_h=ph - 2 * margin,
        dim_style=DIM_INCH_MM,
    )
    # Scale notation
    if hasattr(_draw_engine, "_last_scale"):
        from app.exporters.fabrication_drawing_engine import format_scale_ratio
        scale_str = format_scale_ratio(_draw_engine._last_scale)
        c.setFont("Helvetica", 7)
        c.setFillColorRGB(0.2, 0.2, 0.2)
        c.drawString(margin, margin - 12, f"Scale: {scale_str}  |  BuildDesk Template Preview")

    c.showPage()
    c.save()
    return buf.getvalue()


# ---------------------------------------------------------------------------
# GET /templates
# ---------------------------------------------------------------------------

@router.get("", response_model=List[TemplateDetailResponse])
def list_templates(
    category: Optional[str] = Query(default=None,
                                    description="Filter by category: kitchen / vanity / island"),
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
):
    """
    List all registered fabrication templates.

    Returns template definition (id, category, defaults, supported features)
    plus the UI contract (field visibility per template) for each template.

    Optionally filter by category: ?category=vanity
    """
    definitions = registry.all_definitions()

    if category:
        definitions = [d for d in definitions if d.category.value == category.lower()]

    result = []
    for defn in definitions:
        try:
            contract = get_ui_contract(defn.id)
        except KeyError:
            continue
        result.append(TemplateDetailResponse(
            definition=TemplateDefinitionResponse.from_definition(defn),
            ui_contract=_contract_response(contract),
        ))
    return result


# ---------------------------------------------------------------------------
# GET /templates/{template_id}
# ---------------------------------------------------------------------------

@router.get("/{template_id}", response_model=TemplateDetailResponse)
def get_template(
    template_id: str,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
):
    """
    Get full detail for a single template by its ID.

    Returns defaults, editable fields, supported features, and UI contract.
    """
    if template_id not in registry:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template '{template_id}' not found. "
                   f"Available: {', '.join(registry.ids())}",
        )

    defn = registry.get(template_id).definition

    try:
        contract = get_ui_contract(template_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No UI contract for template '{template_id}'.",
        )

    return TemplateDetailResponse(
        definition=TemplateDefinitionResponse.from_definition(defn),
        ui_contract=_contract_response(contract),
    )


# ---------------------------------------------------------------------------
# POST /templates/generate
# ---------------------------------------------------------------------------

@router.post("/generate", response_model=AssemblyGenerateResponse,
             status_code=status.HTTP_200_OK)
def generate_assembly(
    body: TemplateGenerateRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
):
    """
    Generate an Assembly from a simple template configuration.

    Returns the Assembly structure as JSON.
    The assembly is not persisted in Phase 4 — Phase 5 will add saving.

    Flow:
        SimpleTemplateConfig → SimpleConfigMapper → TemplateConfig
        → ConfigurationService.validate() → registry.build() → Assembly JSON
    """
    assembly, result = _build_assembly_from_request(body, tenant_id)
    return _assembly_response(assembly, body.template_id, result.warnings)


# ---------------------------------------------------------------------------
# POST /templates/preview
# ---------------------------------------------------------------------------

@router.post("/preview")
def preview_assembly(
    body: TemplateGenerateRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
):
    """
    Generate an SVG shop drawing preview from a simple template configuration.

    Returns raw SVG (Content-Type: image/svg+xml).
    Reuses the existing AssemblySvgExporter — no duplicate rendering logic.

    Flow:
        SimpleTemplateConfig → Assembly → AssemblySvgExporter → SVG string
    """
    assembly, _ = _build_assembly_from_request(body, tenant_id)
    svg = _svg_exp.export(assembly)
    return Response(content=svg, media_type="image/svg+xml")


# ---------------------------------------------------------------------------
# POST /templates/pdf
# ---------------------------------------------------------------------------

@router.post("/pdf")
def generate_pdf(
    body: TemplateGenerateRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
):
    """
    Generate a single-page PDF shop drawing from a simple template configuration.

    Returns raw PDF bytes (Content-Type: application/pdf).
    Reuses FabricationDrawingEngine — no duplicate rendering logic.

    Flow:
        SimpleTemplateConfig → Assembly → FabricationDrawingEngine → PDF bytes
    """
    assembly, _ = _build_assembly_from_request(body, tenant_id)
    pdf_bytes = _render_pdf(assembly)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{assembly.name or body.template_id}.pdf"'},
    )


# ---------------------------------------------------------------------------
# POST /templates/drawing-pdf  (Industry-standard format — BUILDDESK_PDF_PROMPT.md)
# ---------------------------------------------------------------------------

class DrawingPdfRequest(BaseModel):
    """
    Request body for the industry-standard fabrication drawing PDF.
    Accepts the raw drawing + project dicts defined in BUILDDESK_PDF_PROMPT.md.
    """
    drawing: Dict[str, Any]
    project: Dict[str, Any]


@router.post("/drawing-pdf")
def generate_drawing_pdf_endpoint(
    body: DrawingPdfRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
):
    """
    Generate one A4-landscape shop drawing PDF matching the industry-standard
    format verified from reference PDFs (Concord, Haven, Deforest, Bulls Outdoor,
    Saltwell Springs).

    Returns raw PDF bytes (application/pdf).
    ONE page regardless of unit count — QTY in title block handles repetition.
    """
    from app.exporters.drawing_pdf import generate_drawing_pdf as _gen_pdf
    try:
        pdf_bytes = _gen_pdf(body.drawing, body.project)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Drawing PDF error: {exc}",
        )
    drawing_name = body.drawing.get("name", "drawing")
    filename = drawing_name.replace(" ", "_") + ".pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# POST /templates/save  (Phase 8 — Connected Workflow)
# ---------------------------------------------------------------------------

@router.post("/save", response_model=AssemblyGenerateResponse,
             status_code=status.HTTP_201_CREATED)
def save_assembly_from_template(
    body: TemplateGenerateRequest,
    tenant_id: uuid.UUID = Depends(get_current_tenant),
    _user: User = Depends(require_active_user),
    db: Session = Depends(get_db),
):
    """
    Build an Assembly from a template config and persist it to the database.

    Requires project_id in the request body.  Returns the saved Assembly summary
    (same shape as /generate) so the frontend can navigate to the new assembly.

    Flow:
        SimpleTemplateConfig → registry.build() → FabricationService.create_assembly()
        → AssemblyGenerateResponse (with persisted assembly_id)

    This is the connection layer between Basic Builder (stateless) and
    Shop Drawings (DB-persisted).  No renderer is invoked.
    """
    if not body.project_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="project_id is required to save an assembly to the project.",
        )

    assembly, result = _build_assembly_from_request(body, tenant_id)

    fab_repo      = FabricationRepository(db)
    hierarchy_repo = ProjectHierarchyRepository(db)
    svc           = FabricationService(fab_repo, hierarchy_repo)

    try:
        saved = svc.create_assembly(assembly)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    return _assembly_response(saved, body.template_id, result.warnings)
