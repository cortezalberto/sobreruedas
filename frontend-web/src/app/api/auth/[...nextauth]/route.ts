/**
 * Los handlers de NextAuth. La configuracion vive en `src/auth.ts`.
 *
 * Es el unico endpoint propio del flujo: recibe el callback de Keycloak con el
 * codigo, lo canjea con el `code_verifier` de PKCE y arma la sesion.
 */
import { handlers } from '@/auth';

export const { GET, POST } = handlers;
