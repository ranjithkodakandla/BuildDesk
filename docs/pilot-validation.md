# Pilot Validation Review (Phase 6)

## 1. Pilot Summary
A full 40-unit multifamily pilot project ("The Highland Residences") was successfully executed entirely through BuildDesk’s REST API, simulating the exact React frontend workflow.
- **Scale:** 1 Building, 5 Floors, 40 Units across 3 Unit Types (A1, A1-MIR, B1).
- **Assemblies:** 3 Kitchen variations with piece-level precision (Eased vs Raw edges, Undermount vs Drop-in cutouts, faucet/soap holes, splashes).
- **Outcome:** Successfully generated `artifacts/pilot_package.pdf`.

## 2. Usability Review
- **Project Authoring Speed:** API-first hierarchy authoring is extremely fast. Creating 40 units across 5 floors takes milliseconds. In the UI, this emphasizes the need for bulk-add tooling (e.g., "Add Units 101-108").
- **Workflow Friction:** Minimal. The path from `Project -> Hierarchy -> Assemblies -> Package` is logical and linear.
- **Hierarchy Usability:** Separating Unit Types from Units works perfectly for the countertop domain where pricing and design are driven by Type, not individual Units.
- **Assembly Editing Usability:** The nested JSON structure (Assembly -> Parts -> Edges/Cutouts/Holes) is deeply normalized. While great for the backend, the frontend UI requires careful state management to keep it feeling snappy and intuitive.
- **Preview Usefulness:** The live `/preview/svg` endpoint is critical. Without it, verifying coordinate math (like hole centers) would be impossible.
- **Package Quality:** High. The PDF correctly grouped the assemblies by Unit Type and tallied total units flawlessly.

## 3. Gap Inventory (Real Workflow Gaps)

**Critical**
- **Bulk Unit Creation UI:** A 150-unit project cannot be typed in unit-by-unit in the UI. We need a "Generate Units" bulk tool in the frontend.
- **Cloning/Duplication:** Assemblies must be easily copyable (e.g., copying "A1 Kitchen" to make "A1-MIR Kitchen" instead of rebuilding from scratch).

**Important**
- **Seam Overrides:** The engine assumes standard rectangular bounds. Non-standard seam geometries (like a curved dogleg) are not yet handled.
- **Material Assignment at Assembly Level:** Currently material is a global Project field. In reality, Kitchens might be Quartz, while Vanities are Granite.

**Nice-to-Have**
- **DXF Export:** Beyond PDF, the CNC machines eventually need DXF files for the individual parts.

## 4. Domain Confidence Assessment
**Would a builder, fabrication coordinator, or countertop operations team plausibly use this workflow?**
**YES.** The data model maps exactly to how shops receive architectural plans (Unit Types) and how they process them (Assemblies mapped to those Types). The resulting PDF is very close to standard shop drawings.

**Where would they struggle?**
They would struggle with the initial setup if there is no bulk-import or cloning feature. Data entry for a 300-unit project is too slow if done manually.

**What still feels "prototype"?**
The lack of per-assembly material overrides and the absence of a direct DXF export for the shop floor.

## 5. Architecture Review & Deferred Infra
**Do current backend + frontend architecture support next-stage growth?**
**YES.** 
- **Validated:** The FastAPI router structure, tenant scoping, and Pydantic validation are rock solid.
- **Questionable:** Generating PDFs inline synchronously. As the project grows to 500 units, the PDF generation might take >10 seconds, causing HTTP timeouts.
- **Deferred Infra Review:** *Are GCS storage and asyncpg truly next priorities?*
  - **GCS Storage + Background Jobs:** **YES.** Because generating large PDF packages is slow, it *must* move to a background job (e.g., Celery or native FastAPI BackgroundTasks) which then uploads the result to GCS. Returning bytes directly over HTTP is a prototype pattern.
  - **asyncpg:** **DEFER.** Database read/write time is currently negligible compared to PDF rendering time. We can defer `asyncpg` further.

## 6. Priority Recommendation
The next milestone must focus on **Asynchronous Package Generation & Cloud Storage (Phase 7)**. We need to detach the PDF generation from the HTTP request-response cycle.
