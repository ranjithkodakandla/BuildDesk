/**
 * Pure utility functions for reading and writing dot-notation keys in the
 * BuilderConfig object (e.g. "splash.back", "sink.type", "width").
 *
 * These are plain functions with no React dependencies, making them
 * easy to test in isolation.
 */

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyObj = Record<string, any>;

/** Read a nested value by dot-notation key. Returns undefined if any segment is missing. */
export function getNestedValue(obj: AnyObj, key: string): unknown {
  return key.split('.').reduce<unknown>((cur, k) => {
    if (cur !== null && typeof cur === 'object') {
      return (cur as AnyObj)[k];
    }
    return undefined;
  }, obj);
}

/** Return a new object with the dot-notation key set to value (immutable). */
export function setNestedValue<T extends AnyObj>(obj: T, key: string, value: unknown): T {
  const parts = key.split('.');
  const result = { ...obj } as AnyObj;
  let current = result;

  for (let i = 0; i < parts.length - 1; i++) {
    const segment = parts[i];
    current[segment] = { ...(current[segment] as AnyObj) };
    current = current[segment] as AnyObj;
  }

  current[parts[parts.length - 1]] = value;
  return result as T;
}

/**
 * Build the API request body from a BuilderConfig.
 * Separates the project_id concern: caller passes it optionally.
 */
export function buildRequestBody(config: AnyObj, projectId?: string): AnyObj {
  const body: AnyObj = {
    template_id: config.template_id,
    name:        config.name || '',
    width:       config.width,
    depth:       config.depth,
    thickness:   config.thickness,
    mirror:      config.mirror,
    edge_finish: config.edge_finish,
    splash:      config.splash,
    sink:        config.sink,
  };
  if (projectId) body.project_id = projectId;
  return body;
}

// Templates that use a kitchen sink by default (rectangle, center)
const _KITCHEN_TEMPLATES = new Set([
  'KITCHEN_STRAIGHT', 'KITCHEN_STRAIGHT_REF', 'KITCHEN_L',
]);

/** Build initial config from template defaults (maps backend field names to simple config). */
export function defaultConfigFromTemplate(
  templateId: string,
  defaults: AnyObj,
): AnyObj {
  const sinkDefaults = (defaults.sink as Record<string, unknown>) ?? {};
  const splashDefaults = (defaults.splash as Record<string, unknown>) ?? {};

  // Infer sensible sink type when backend default is "none"
  // (production evidence: vanities → oval, kitchens → rectangle, islands → none)
  const backendShape = sinkDefaults.shape as string | undefined;
  let sinkType = mapShape(backendShape);
  if (sinkType === 'none') {
    if (_KITCHEN_TEMPLATES.has(templateId)) sinkType = 'rectangle';
    else if (templateId !== 'PLAIN_ISLAND')  sinkType = 'oval';
  }

  return {
    template_id: templateId,
    name:        '',
    width:       (defaults.width as number) ?? 62,
    depth:       (defaults.depth as number) ?? 22,
    thickness:   (defaults.thickness as number) ?? 1.25,
    mirror:      (defaults.mirror as boolean) ?? false,
    edge_finish: (defaults.edge_finish as string) ?? 'polished',
    splash: {
      back:   (splashDefaults.back  as boolean) ?? true,
      left:   (splashDefaults.left  as boolean) ?? false,
      right:  (splashDefaults.right as boolean) ?? false,
      height: (splashDefaults.height as number) ?? 4.0,
    },
    sink: {
      // backend defaults use "shape"/"alignment"; API request uses "type"/"position"
      type:     sinkType,
      position: mapAlignment(sinkDefaults.alignment as string | undefined),
      size:     'standard',
    },
  };
}

function mapShape(shape?: string): string {
  if (!shape || shape === 'none') return 'none';
  return shape; // "oval" | "rectangle" — same in both systems
}

function mapAlignment(alignment?: string): string {
  if (!alignment) return 'center';
  return alignment; // "center" | "left" | "right" — same in both systems
}
