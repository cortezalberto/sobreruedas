/**
 * El `accessToken` en la sesion, tipado.
 *
 * Sin esto habria que castear en cada uso, y la regla dura 7 prohibe `any`. Un
 * `.d.ts` que extiende el modulo es la forma de agregarle un campo a un tipo
 * ajeno sin mentir sobre lo que trae.
 */
import type { DefaultSession } from 'next-auth';

declare module 'next-auth' {
  interface Session extends DefaultSession {
    accessToken?: string;
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    accessToken?: string;
    expiresAt?: number;
  }
}
