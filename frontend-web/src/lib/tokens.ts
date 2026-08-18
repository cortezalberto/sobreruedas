/**
 * Tokens de color del design system — C-07, `T-036`.
 *
 * FUENTE Y DESVIOS
 * ─────────────────
 * La paleta sale de `knowledge-base/15` §Paleta de colores, que deriva del
 * brand book. Con **una** diferencia, y esta registrada: el token de error NO
 * es el `#974706` del brand book. Ese valor esta a 7 grados de tono del amarillo
 * de advertencia y los dos estados no se distinguen — ver `ADR-028`, que lo
 * verifico contra el `.docx` fuente y adopto `#A4161A` (35 grados de
 * separacion, 7.75:1 sobre blanco).
 *
 * POR QUE ES UN MODULO DE TypeScript Y NO SOLO LA CONFIG DE TAILWIND
 * ──────────────────────────────────────────────────────────────────
 * Porque los tokens tienen que ser AUDITABLES. La auditoria de contraste de
 * `T-038` los importa y los mide en cada corrida de tests; desde un objeto de
 * `tailwind.config.ts` habria que parsear la config o duplicar los valores, y
 * un duplicado es exactamente como una paleta se desincroniza.
 *
 * `tailwind.config.ts` importa de aca. Una sola fuente.
 */

/** Colores de marca. `principal` es el del logo y los CTA primarios. */
export const MARCA = {
  principal: '#1F3864',
  acento: '#2E75B6',
  /** Premium. El brand book pide usarlo en menos del 2 % de la composicion. */
  destacado: '#FFD966',
} as const;

/**
 * Colores de ESTADO.
 *
 * ⚠️ El color no es nunca el unico canal (WCAG 1.4.1). Todo estado lleva ademas
 * icono y texto. El eje rojo/naranja es justamente donde el daltonismo pega, asi
 * que separar los tonos es necesario pero no suficiente.
 */
export const ESTADO = {
  exito: '#375623',
  advertencia: '#9C5700',
  /** `ADR-028`: NO es el `#974706` del brand book. Ver el encabezado. */
  error: '#A4161A',
  meta: '#5B2D8C',
} as const;

/** Neutros. De fondo a texto enfatico. */
export const NEUTRO = {
  blanco: '#FFFFFF',
  fondo: '#F5F5F5',
  borde: '#BFBFBF',
  textoSecundario: '#808080',
  texto: '#404040',
  enfasis: '#1A1A1A',
} as const;

export const TOKENS = { ...MARCA, ...ESTADO, ...NEUTRO } as const;

// ── Utilidades de contraste, usadas por la auditoria ────────────────────────

function canalLineal(valor: number): number {
  const c = valor / 255;
  return c <= 0.04045 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

function componentes(hex: string): [number, number, number] {
  const limpio = hex.replace('#', '');
  return [
    parseInt(limpio.slice(0, 2), 16),
    parseInt(limpio.slice(2, 4), 16),
    parseInt(limpio.slice(4, 6), 16),
  ];
}

/** Luminancia relativa segun WCAG 2.1. */
export function luminancia(hex: string): number {
  const [r, g, b] = componentes(hex);
  return 0.2126 * canalLineal(r) + 0.7152 * canalLineal(g) + 0.0722 * canalLineal(b);
}

/**
 * Contraste entre dos colores, de 1 a 21.
 *
 * Mide legibilidad de TEXTO SOBRE FONDO. No sirve para saber si dos colores de
 * estado se distinguen entre si — para eso esta `separacionDeTono`. Confundir
 * las dos fue el primer error al resolver `IN-45` (`ADR-028`).
 */
export function contraste(a: string, b: string): number {
  const la = luminancia(a);
  const lb = luminancia(b);
  return (Math.max(la, lb) + 0.05) / (Math.min(la, lb) + 0.05);
}

/** Tono en grados (0-360). */
export function tono(hex: string): number {
  const [r, g, b] = componentes(hex).map((c) => c / 255) as [number, number, number];
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  if (max === min) return 0;

  const d = max - min;
  let h: number;
  if (max === r) h = ((g - b) / d) % 6;
  else if (max === g) h = (b - r) / d + 2;
  else h = (r - g) / d + 4;

  return (h * 60 + 360) % 360;
}

/** Distancia angular entre dos tonos, de 0 a 180. */
export function separacionDeTono(a: string, b: string): number {
  const d = Math.abs(tono(a) - tono(b));
  return Math.min(d, 360 - d);
}

/** Piso vinculante del proyecto: WCAG 2.1 nivel AA para texto normal. */
export const CONTRASTE_AA = 4.5;

/** AA para texto grande (18.66px negrita o 24px normal). */
export const CONTRASTE_AA_GRANDE = 3;

/**
 * Separacion de tono minima entre dos colores de estado.
 *
 * 20 grados no sale de una norma —WCAG no legisla sobre esto— sino del caso que
 * lo motivo: los 7 grados del brand book eran indistinguibles y los 35 del token
 * adoptado no lo son. Se fija en el medio, del lado seguro, y se documenta como
 * lo que es: un criterio del proyecto, no una cita.
 */
export const SEPARACION_DE_TONO_MINIMA = 20;
