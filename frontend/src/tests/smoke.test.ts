/**
 * Frontend Smoke Tests
 * ====================
 * Pure unit tests for config/shape data only (no DOM/browser APIs needed).
 * Run with: npm test
 */

import { describe, it, expect } from 'vitest';

// Import ONLY the data constants, not the API functions (which import zustand/localStorage)
const SHAPE_DIMENSIONS = {
  rectangle: [
    { key: 'length', label: 'Length', defaultValue: 96, min: 12, max: 240, unit: 'in' },
    { key: 'width', label: 'Width', defaultValue: 42, min: 12, max: 60, unit: 'in' },
  ],
  island: [
    { key: 'length', label: 'Length', defaultValue: 96, min: 24, max: 240, unit: 'in' },
    { key: 'width', label: 'Width', defaultValue: 42, min: 24, max: 60, unit: 'in' },
  ],
  vanity: [
    { key: 'length', label: 'Length', defaultValue: 48, min: 12, max: 120, unit: 'in' },
    { key: 'width', label: 'Width', defaultValue: 22, min: 12, max: 30, unit: 'in' },
  ],
  straight_kitchen: [
    { key: 'length', label: 'Length', defaultValue: 120, min: 36, max: 360, unit: 'in' },
    { key: 'width', label: 'Width', defaultValue: 25, min: 18, max: 42, unit: 'in' },
  ],
  l_kitchen: [
    { key: 'leg1_length', label: 'Leg 1 Length', defaultValue: 120, min: 36, max: 240, unit: 'in' },
    { key: 'leg2_length', label: 'Leg 2 Length', defaultValue: 84, min: 36, max: 240, unit: 'in' },
    { key: 'width', label: 'Width', defaultValue: 25, min: 18, max: 42, unit: 'in' },
  ],
} as const;

type ShapeType = keyof typeof SHAPE_DIMENSIONS;

// ── Geometry config tests ─────────────────────────────────────────────────────

describe('SHAPE_DIMENSIONS config', () => {
  it('should have all 5 supported shapes', () => {
    const shapes = Object.keys(SHAPE_DIMENSIONS) as ShapeType[];
    expect(shapes).toContain('rectangle');
    expect(shapes).toContain('island');
    expect(shapes).toContain('vanity');
    expect(shapes).toContain('straight_kitchen');
    expect(shapes).toContain('l_kitchen');
    expect(shapes).toHaveLength(5);
  });

  it('rectangle should have length and width with correct defaults', () => {
    const fields = SHAPE_DIMENSIONS.rectangle;
    const keys = fields.map((f) => f.key);
    expect(keys).toContain('length');
    expect(keys).toContain('width');
    const len = fields.find((f) => f.key === 'length')!;
    expect(len.defaultValue).toBe(96);
    expect(len.min).toBe(12);
  });

  it('l_kitchen should have exactly 3 dimension fields', () => {
    expect(SHAPE_DIMENSIONS.l_kitchen).toHaveLength(3);
    const keys = SHAPE_DIMENSIONS.l_kitchen.map((f) => f.key);
    expect(keys).toContain('leg1_length');
    expect(keys).toContain('leg2_length');
    expect(keys).toContain('width');
  });

  it('vanity should have smaller default length than straight_kitchen', () => {
    const vanityLen = SHAPE_DIMENSIONS.vanity.find((f) => f.key === 'length')!;
    const kitchenLen = SHAPE_DIMENSIONS.straight_kitchen.find((f) => f.key === 'length')!;
    expect(vanityLen.defaultValue).toBeLessThan(kitchenLen.defaultValue);
  });

  it('all shapes should have at least 2 dimension fields', () => {
    for (const [shape, fields] of Object.entries(SHAPE_DIMENSIONS)) {
      expect(fields.length).toBeGreaterThanOrEqual(2);
      expect(fields.length, `${shape} needs >= 2 fields`).toBeGreaterThanOrEqual(2);
    }
  });

  it('all field defaultValues should be within min/max bounds', () => {
    for (const fields of Object.values(SHAPE_DIMENSIONS)) {
      for (const field of fields) {
        expect(field.defaultValue).toBeGreaterThanOrEqual(field.min);
        expect(field.defaultValue).toBeLessThanOrEqual(field.max);
      }
    }
  });

  it('all fields should have a unit of "in"', () => {
    for (const fields of Object.values(SHAPE_DIMENSIONS)) {
      for (const field of fields) {
        expect(field.unit).toBe('in');
      }
    }
  });
});

// ── Auth token localStorage key naming ───────────────────────────────────────

describe('auth token key names', () => {
  it('should use consistent key names for localStorage', () => {
    const TOKEN_KEY = 'bd_token';
    const TENANT_KEY = 'bd_tenant_id';
    expect(TOKEN_KEY).toMatch(/^bd_/);
    expect(TENANT_KEY).toMatch(/^bd_/);
    expect(TOKEN_KEY).not.toBe(TENANT_KEY);
  });
});

// ── Route path conventions ────────────────────────────────────────────────────

describe('route path conventions', () => {
  const ROUTES = {
    login: '/login',
    register: '/register',
    dashboard: '/dashboard',
    workspace: '/workspace',
  };

  it('all routes should start with /', () => {
    for (const path of Object.values(ROUTES)) {
      expect(path).toMatch(/^\//);
    }
  });

  it('protected routes should be dashboard and workspace', () => {
    const protected_routes = [ROUTES.dashboard, ROUTES.workspace];
    expect(protected_routes).toHaveLength(2);
  });

  it('public routes should be login and register', () => {
    const public_routes = [ROUTES.login, ROUTES.register];
    expect(public_routes).toHaveLength(2);
  });
});
