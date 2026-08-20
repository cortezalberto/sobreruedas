import type { Config } from 'tailwindcss';

import { ESTADO, MARCA, NEUTRO } from './src/lib/tokens';

/**
 * Tailwind — C-07, `T-036`.
 *
 * LOS COLORES SE IMPORTAN, NO SE ESCRIBEN ACA. La fuente unica es
 * `src/lib/tokens.ts`, y el motivo es que la auditoria de contraste de `T-038`
 * los mide en cada corrida de tests: desde esta config habria que parsearla o
 * duplicar los valores, y un duplicado es exactamente como una paleta se
 * desincroniza del gate que deberia protegerla.
 *
 * Hasta el 18-ago-2026 este archivo tenia la paleta por defecto de Tailwind y un
 * TODO apuntando a C-07, con un motivo que ya no aplica: "inventar colores ahora
 * seria peor que no tenerlos". Ahora no se inventan — salen del brand book, con
 * un unico desvio registrado en `ADR-028` (el token de error).
 *
 * ⚠️ La tipografia queda pendiente. El brand book pide **Inter**, y servirla
 * exige decidir si se empaqueta con `next/font` o se sirve desde el VPS: son
 * bytes en el bundle contra una dependencia de red en el primer render, y esa
 * decision no se toma de paso en un archivo de configuracion.
 */
const config: Config = {
  content: ['./src/**/*.{ts,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        marca: {
          DEFAULT: MARCA.principal,
          acento: MARCA.acento,
          destacado: MARCA.destacado,
        },
        estado: {
          exito: ESTADO.exito,
          advertencia: ESTADO.advertencia,
          error: ESTADO.error,
          meta: ESTADO.meta,
        },
        neutro: {
          fondo: NEUTRO.fondo,
          borde: NEUTRO.borde,
          suave: NEUTRO.textoSecundario,
          texto: NEUTRO.texto,
          enfasis: NEUTRO.enfasis,
        },
      },
      // El brand book pide interlineado 1,4-1,6x y medida de columna de 50-75
      // caracteres. Lo segundo es lo que evita parrafos que cruzan la pantalla
      // entera en un monitor ancho.
      maxWidth: {
        lectura: '68ch',
      },
      fontFamily: {
        // Inter la carga `next/font` en el layout raiz y expone la variable CSS.
        // El fallback no es decorativo: cubre el rato entre el primer pintado y
        // la carga de la fuente, y el sistema operativo de quien mira.
        sans: ['var(--fuente-inter)', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};

export default config;
