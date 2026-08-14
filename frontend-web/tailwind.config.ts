import type { Config } from 'tailwindcss';

/**
 * Tailwind — configuracion base (T-006).
 *
 * ⚠️ LA PALETA DE MARCA NO ESTA ACA, Y NO ES UN OLVIDO.
 *
 * T-006 pide "Tailwind con la paleta del design system (colores definidos en
 * T-036)". T-036 cae en C-07, que todavia no existe: es el riesgo R-4 del
 * proyecto — los primitivos del design system no estan especificados en
 * ninguno de los 11 documentos fuente.
 *
 * Mientras tanto se usa la paleta por defecto de Tailwind y se deja marcado el
 * punto de extension. Inventar colores ahora seria peor que no tenerlos:
 * quedarian regados por los componentes y despues habria que cazarlos uno por
 * uno.
 */
const config: Config = {
  content: ['./src/**/*.{ts,tsx,mdx}'],
  theme: {
    extend: {
      // TODO(C-07): reemplazar por la paleta del design system (T-036).
      // Hasta entonces, usar los colores por defecto de Tailwind.
      colors: {},
      fontFamily: {
        // TODO(C-07): tipografia del brand book.
      },
    },
  },
  plugins: [],
};

export default config;
