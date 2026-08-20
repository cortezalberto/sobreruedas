/**
 * Next.js — configuracion base (T-006).
 *
 * El nombre del archivo es `next.config.js` y no `.mjs` porque la seccion 4.1
 * del plan lo nombra asi, y ese arbol es vinculante.
 *
 * @type {import('next').NextConfig}
 */
const nextConfig = {
  reactStrictMode: true,

  // Oculta la cabecera `X-Powered-By: Next.js`. Es superficie de
  // reconocimiento gratis: le dice a cualquiera que escanee que framework y
  // que familia de vulnerabilidades probar.
  poweredByHeader: false,

  // `standalone` deja un build que corre sin node_modules completo. Lo usa la
  // imagen de produccion, que define C-07.
  output: 'standalone',
};

module.exports = nextConfig;
