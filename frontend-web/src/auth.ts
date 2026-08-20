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
import type { JWT } from 'next-auth/jwt';

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
        token.refreshToken = account.refresh_token;
        token.expiresAt = account.expires_at;
        return token;
      }

      // ⚠️ SIN ESTO LA SESIÓN MIENTE. La sesión de NextAuth dura 30 días y el
      // access token de Keycloak **15 minutos**. Sin refresco, a los quince
      // minutos la interfaz sigue mostrando al usuario adentro y TODAS las
      // llamadas al backend responden 401.
      //
      // Es el peor modo de falla posible para un login: no falla el login,
      // falla todo lo demás y sin señal — nadie mira los 401 de la consola
      // cuando el encabezado dice tu nombre.
      const expira = typeof token.expiresAt === 'number' ? token.expiresAt : 0;
      // 30 s de margen: un token que vence mientras viaja la petición ya venció.
      if (Date.now() / 1000 < expira - 30) {
        return token;
      }

      return await refrescar(token);
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
      // Que el refresco haya fallado tiene que llegar a la interfaz: es la
      // diferencia entre "reintentá" y "volvé a entrar".
      session.error = typeof token.error === 'string' ? token.error : undefined;
      return session;
    },
  },
});

/**
 * Canjea el refresh token por uno nuevo contra Keycloak.
 *
 * Si falla —el refresh token venció, o alguien cerró la sesión del lado de
 * Keycloak— se marca el JWT con `error` en vez de romper. La sesión sobrevive
 * lo suficiente para que la interfaz pueda mandar a iniciar sesión de nuevo, en
 * lugar de tirar una excepción en medio de un render.
 */
async function refrescar(token: JWT): Promise<JWT> {
  if (typeof token.refreshToken !== 'string') {
    return { ...token, error: 'SinRefreshToken' };
  }

  try {
    const respuesta = await fetch(`${EMISOR}/protocol/openid-connect/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        grant_type: 'refresh_token',
        // Cliente público: no hay secreto que mandar. Ver el encabezado.
        client_id: process.env.AUTH_KEYCLOAK_ID ?? 'frontend-web',
        refresh_token: token.refreshToken,
      }),
    });

    if (!respuesta.ok) {
      return { ...token, error: 'RefrescoRechazado' };
    }

    const datos: unknown = await respuesta.json();
    if (typeof datos !== 'object' || datos === null) {
      return { ...token, error: 'RefrescoIlegible' };
    }
    const d = datos as Record<string, unknown>;
    if (typeof d.access_token !== 'string' || typeof d.expires_in !== 'number') {
      return { ...token, error: 'RefrescoIlegible' };
    }

    return {
      ...token,
      accessToken: d.access_token,
      expiresAt: Math.floor(Date.now() / 1000) + d.expires_in,
      // Keycloak rota el refresh token: si no se guarda el nuevo, el siguiente
      // refresco usa uno ya consumido y falla.
      refreshToken: typeof d.refresh_token === 'string' ? d.refresh_token : token.refreshToken,
      error: undefined,
    };
  } catch {
    // Keycloak caido o red cortada. NO se invalida la sesion por eso: el
    // proximo intento puede andar.
    return { ...token, error: 'RefrescoSinRespuesta' };
  }
}
