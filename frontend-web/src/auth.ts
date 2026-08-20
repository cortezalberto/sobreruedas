/**
 * Cliente OIDC contra Keycloak — C-08 (recorte de ESC-003).
 *
 * NO HAY FORMULARIO DE LOGIN NUESTRO, Y ESO ES EL PUNTO
 * ──────────────────────────────────────────────────────
 * `ADR-026` y la regla dura 2: la contraseña se escribe en la pantalla de
 * Keycloak y nunca pasa por acá. Este archivo no toca credenciales — arranca un
 * redirect y recibe un código.
 *
 * PKCE, y no es opcional
 * ───────────────────────
 * El cliente `frontend-web` es PÚBLICO: no tiene secreto, porque cualquier
 * secreto que viaje a un navegador deja de serlo. Lo que impide que un código
 * interceptado se canjee es el `code_verifier`, y por eso
 * `token_endpoint_auth_method: 'none'` va junto con PKCE y no sin él.
 *
 * QUÉ GUARDA LA SESIÓN
 * ─────────────────────
 * El `access_token` tal cual, para reenviarlo al backend. No se re-firma ni se
 * envuelve: el backend valida contra el JWKS de Keycloak, así que cualquier
 * transformación nuestra lo invalidaría.
 *
 * ⚠️ El backend exige `aud: backend`, `tenant_id` y `role` como claims planos.
 * Los tres los pone Keycloak con mappers colgados del cliente `frontend-web`,
 * que `make seed` mantiene al día. Sin ellos el login "funciona" y después todo
 * responde 401.
 */

import NextAuth from 'next-auth';
import Keycloak from 'next-auth/providers/keycloak';

/** El emisor. Tiene que ser el MISMO que espera el backend (`KEYCLOAK_ISSUER`). */
const EMISOR = process.env.AUTH_KEYCLOAK_ISSUER ?? 'http://localhost:8080/realms/deruedas-dev';

export const { handlers, signIn, signOut, auth } = NextAuth({
  providers: [
    Keycloak({
      clientId: process.env.AUTH_KEYCLOAK_ID ?? 'frontend-web',
      // Cliente público: sin secreto. Ver el encabezado.
      clientSecret: undefined,
      issuer: EMISOR,
      client: { token_endpoint_auth_method: 'none' },
      checks: ['pkce', 'state'],
    }),
  ],

  // JWT y no sesión en base: no hay tabla de sesiones nuestra, y no debería
  // haberla — `ADR-026` deja la sesión del lado de Keycloak.
  session: { strategy: 'jwt' },

  callbacks: {
    async jwt({ token, account }) {
      // `account` solo viene en el login. Después, el token ya lo tiene.
      if (account?.access_token) {
        token.accessToken = account.access_token;
        token.expiresAt = account.expires_at;
      }
      return token;
    },

    async session({ session, token }) {
      // El access token viaja al cliente para que el fetch al backend lo mande.
      //
      // ⚠️ Consecuencia asumida: queda accesible desde el navegador. Es lo que
      // permite que el mismo token sirva para las llamadas del cliente y las
      // del servidor. La alternativa —proxy en el servidor de Next— evita
      // exponerlo pero duplica cada endpoint del backend, y eso es C-08
      // completo, no este recorte.
      // Se ESTRECHA en vez de castear. El JWT es un contenedor de claims
      // arbitrarios: lo que le pusimos en el callback de arriba está, pero el
      // tipo no lo sabe, y afirmarlo con un cast sería exactamente el `any`
      // encubierto que la regla dura 7 prohíbe.
      session.accessToken = typeof token.accessToken === 'string' ? token.accessToken : undefined;
      return session;
    },
  },
});
