import client from './client';
import {
  AssemblyGenerateResponse,
  TemplateDetail,
  TemplateGenerateRequest,
} from '../types/templates';

export const templatesApi = {
  /** List all templates, optionally filtered by category. */
  listTemplates: async (category?: string): Promise<TemplateDetail[]> => {
    const params = category ? { category } : {};
    const res = await client.get('/templates', { params });
    return res.data;
  },

  /** Full template detail (definition + UI contract). */
  getTemplate: async (templateId: string): Promise<TemplateDetail> => {
    const res = await client.get(`/templates/${templateId}`);
    return res.data;
  },

  /** Generate an Assembly from a simple config. Returns JSON. */
  generate: async (body: TemplateGenerateRequest): Promise<AssemblyGenerateResponse> => {
    const res = await client.post('/templates/generate', body);
    return res.data;
  },

  /**
   * Generate an SVG preview.
   * Returns the raw SVG string (Content-Type: image/svg+xml).
   */
  preview: async (body: TemplateGenerateRequest): Promise<string> => {
    const res = await client.post('/templates/preview', body, {
      responseType: 'text',
    });
    return res.data as string;
  },

  /**
   * Generate a PDF drawing.
   * Returns a Blob suitable for triggering a file download.
   */
  pdf: async (body: TemplateGenerateRequest): Promise<Blob> => {
    const res = await client.post('/templates/pdf', body, {
      responseType: 'blob',
    });
    return res.data as Blob;
  },

  /**
   * Build an Assembly from a template config and persist it to the project DB.
   * Requires project_id in the body.  Returns the saved Assembly summary.
   * Phase 8 — Connected Workflow: bridges Basic Builder → Shop Drawings.
   */
  saveToProject: async (body: TemplateGenerateRequest): Promise<AssemblyGenerateResponse> => {
    const res = await client.post('/templates/save', body);
    return res.data;
  },

  /**
   * Generate an industry-standard A4-landscape shop drawing PDF.
   * Accepts raw drawing + project dicts per BUILDDESK_PDF_PROMPT.md spec.
   * Returns a Blob for file download.
   */
  drawingPdf: async (drawing: Record<string, unknown>, project: Record<string, unknown>): Promise<Blob> => {
    const res = await client.post('/templates/drawing-pdf', { drawing, project }, {
      responseType: 'blob',
    });
    return res.data as Blob;
  },
};
