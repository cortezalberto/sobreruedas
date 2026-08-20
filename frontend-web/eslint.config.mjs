/**
 * ESLint 9 — flat config (T-006).
 *
 * `eslint-config-next` 16 declara `eslint: ">=9.0.0"` como peer, y ESLint 9
 * abandono el formato `.eslintrc`. No es una preferencia: es la unica forma.
 *
 * Ojo con `FlatCompat`: envolver `next/core-web-vitals` con el shim revienta
 * con "Converting circular structure to JSON". Desde la 16 el paquete exporta
 * flat config nativa y hay que importarla directo.
 */
import nextCoreWebVitals from 'eslint-config-next/core-web-vitals';
import nextTypeScript from 'eslint-config-next/typescript';
import prettier from 'eslint-config-prettier';
import jsxA11y from 'eslint-plugin-jsx-a11y';
import security from 'eslint-plugin-security';

const config = [
  { ignores: ['.next/**', 'node_modules/**', 'next-env.d.ts'] },

  ...nextCoreWebVitals,
  ...nextTypeScript,

  // SAST del frontend (ADR-027). `plan-seguridad` §1415 pide "eslint con
  // plugin seguridad", y hasta el 17-ago-2026 solo estaba `jsx-a11y`.
  //
  // Entra AHORA, con el frontend casi vacio, justamente por eso: agregarlo hoy
  // es una linea; agregarlo despues de C-07 y C-08 es corregir codigo ya
  // escrito. Mismo criterio con el que C-04 creo `max_whatsapp_messages_month`
  // antes de que la usara nadie.
  security.configs.recommended,

  // Va al final: apaga las reglas de formato que pisarian a Prettier.
  prettier,

  {
    rules: {
      // Se toman las REGLAS de jsx-a11y sin re-registrar el plugin: la config
      // de Next ya lo declara, y declararlo dos veces falla con
      // 'Cannot redefine plugin "jsx-a11y"'.
      ...jsxA11y.flatConfigs.recommended.rules,
      // Regla dura 7 del proyecto: `any` prohibido. Si no sabes el tipo, es
      // `unknown` y lo estrechas.
      '@typescript-eslint/no-explicit-any': 'error',
      // Accesibilidad. El plan de UX exige WCAG y estas tres son las que mas
      // se rompen sin que nadie se de cuenta.
      'jsx-a11y/alt-text': 'error',
      'jsx-a11y/anchor-is-valid': 'error',
      'jsx-a11y/label-has-associated-control': 'error',
    },
  },
];

export default config;
