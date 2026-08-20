/**
 * Auditoria de contraste del design system — C-07, `T-038`.
 *
 * POR QUE ES UN TEST Y NO UNA REVISION
 * ─────────────────────────────────────
 * `knowledge-base/15` fija WCAG 2.1 **AA** como estandar, y lo repiten
 * `spec-tecnica` §6.6 y la Definicion de Terminado de las historias. Un
 * estandar que se verifica a ojo se degrada en el primer apuro: alguien aclara
 * un gris para que "se vea mejor" y nadie mide.
 *
 * Estos tests miden los pares que el producto USA, no todos los pares posibles.
 * Auditar la matriz completa daria rojo por combinaciones que nadie va a poner
 * en pantalla, y un gate que reporta ruido se termina apagando.
 *
 * ⚠️ DOS METRICAS DISTINTAS, Y CONFUNDIRLAS COSTO UN ANALISIS EQUIVOCADO
 * ──────────────────────────────────────────────────────────────────────
 * `contraste()` mide legibilidad de TEXTO SOBRE FONDO — es lo que WCAG legisla.
 * `separacionDeTono()` mide si dos colores de ESTADO se distinguen entre si, que
 * es otra pregunta y WCAG no la cubre. Resolviendo `IN-45` se midio primero el
 * contraste entre el rojo y el amarillo (1.17:1) como si eso probara algo: no
 * prueba nada, porque esos dos colores nunca se apilan. Ver `ADR-028`.
 */
import { describe, expect, it } from 'vitest';

import {
  CONTRASTE_AA,
  CONTRASTE_AA_GRANDE,
  contraste,
  ESTADO,
  MARCA,
  NEUTRO,
  SEPARACION_DE_TONO_MINIMA,
  separacionDeTono,
} from '@/lib/tokens';

describe('contraste sobre fondo claro', () => {
  // Los pares que el producto pone en pantalla: texto y acentos sobre los dos
  // fondos reales (blanco y gris de seccion).
  const FONDOS = [
    ['blanco', NEUTRO.blanco],
    ['fondo de seccion', NEUTRO.fondo],
  ] as const;

  const TEXTOS = [
    ['texto principal', NEUTRO.texto],
    ['texto enfatico', NEUTRO.enfasis],
    ['azul institucional', MARCA.principal],
    ['error', ESTADO.error],
    ['exito', ESTADO.exito],
    ['advertencia', ESTADO.advertencia],
    ['meta', ESTADO.meta],
  ] as const;

  for (const [nombreFondo, fondo] of FONDOS) {
    for (const [nombreTexto, color] of TEXTOS) {
      it(`${nombreTexto} sobre ${nombreFondo} cumple AA`, () => {
        expect(contraste(color, fondo)).toBeGreaterThanOrEqual(CONTRASTE_AA);
      });
    }
  }

  it('el texto secundario cumple AA para texto grande, que es donde se usa', () => {
    // `#808080` sobre blanco da 3.95:1: NO cumple AA para texto normal. Se usa
    // solo en apoyo de tamano grande, y el test fija ese limite en vez de
    // dejarlo a criterio de quien escriba la proxima pantalla.
    const medido = contraste(NEUTRO.textoSecundario, NEUTRO.blanco);

    expect(medido).toBeGreaterThanOrEqual(CONTRASTE_AA_GRANDE);
    expect(medido).toBeLessThan(CONTRASTE_AA);
  });
});

describe('separacion entre colores de estado', () => {
  const PARES = [
    ['error', ESTADO.error, 'advertencia', ESTADO.advertencia],
    ['error', ESTADO.error, 'exito', ESTADO.exito],
    ['advertencia', ESTADO.advertencia, 'exito', ESTADO.exito],
    ['error', ESTADO.error, 'meta', ESTADO.meta],
  ] as const;

  for (const [nombreA, a, nombreB, b] of PARES) {
    it(`${nombreA} y ${nombreB} se distinguen por tono`, () => {
      expect(separacionDeTono(a, b)).toBeGreaterThanOrEqual(SEPARACION_DE_TONO_MINIMA);
    });
  }

  it('el rojo del brand book habria fallado este test', () => {
    // `ADR-028`. No es un test del sistema: es la evidencia de que este gate
    // sirve. Sin esto, los de arriba pasan y nadie sabe si detectan algo.
    const ROJO_DEL_BRAND_BOOK = '#974706';

    expect(separacionDeTono(ROJO_DEL_BRAND_BOOK, ESTADO.advertencia)).toBeLessThan(
      SEPARACION_DE_TONO_MINIMA,
    );
  });
});

describe('IN-44 — el azul institucional', () => {
  it('cruza AA y tambien AAA, asi que los dos documentos tenian razon', () => {
    // §5.6 decia "cumple AA" y §6.4.4 "cumple AAA". Son un piso y un piso mas
    // alto, y 11.62:1 los cruza a los dos. No habia contradiccion.
    const medido = contraste(MARCA.principal, NEUTRO.blanco);

    expect(medido).toBeGreaterThanOrEqual(7);
  });
});
