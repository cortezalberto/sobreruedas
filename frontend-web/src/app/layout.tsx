import type { Metadata, Viewport } from 'next';
import { Inter } from 'next/font/google';

import { AtajosDeTeclado } from '@/components/AtajosDeTeclado';
import { NavegacionPrincipal } from '@/components/NavegacionPrincipal';

import './globals.css';

/**
 * Inter — la tipografia digital principal del brand book (`knowledge-base/15`
 * §Tipografia, licencia SIL OFL).
 *
 * `next/font/google` Y NO UN `<link>` A GOOGLE FONTS. La diferencia importa por
 * dos motivos, y ninguno es de moda:
 *
 *   - **No hay dependencia de red en tiempo de ejecucion.** Next descarga la
 *     fuente en el BUILD y la sirve desde el propio dominio. Un `<link>` a
 *     `fonts.googleapis.com` haria que cada visita dependa de un tercero, y
 *     ademas le filtra la IP del usuario — que con Ley 25.326 encima no es un
 *     detalle estetico.
 *   - **No hay salto de maquetado.** Next calcula el `size-adjust` de la fuente
 *     de respaldo, asi que el texto no se reacomoda cuando termina de cargar.
 *
 * ⚠️ A cambio, el BUILD pasa a necesitar red la primera vez (despues cachea).
 * Es un costo real y esta asumido: el pipeline ya descarga dependencias de npm y
 * de PyPI, asi que no introduce una clase de fallo nueva.
 *
 * `display: 'swap'`: el texto se ve con la fuente de respaldo mientras Inter
 * carga, en vez de quedar invisible. Un bloque de texto en blanco es peor que un
 * bloque con otra tipografia.
 */
const inter = Inter({
  subsets: ['latin'],
  display: 'swap',
  variable: '--fuente-inter',
});

/**
 * Layout raiz — T-006.
 *
 * Los metadatos Open Graph estan porque el plan los pide, pero apuntan a
 * placeholders: el brand book define el tono y las imagenes, y eso entra con
 * C-07.
 */
export const metadata: Metadata = {
  title: {
    default: 'deRuedas Gestion',
    template: '%s | deRuedas Gestion',
  },
  description: 'Sistema de gestion para agencias de vehiculos.',
  // El backoffice de una agencia no tiene por que aparecer en buscadores.
  robots: { index: false, follow: false },
  openGraph: {
    type: 'website',
    locale: 'es_AR',
    siteName: 'deRuedas Gestion',
    title: 'deRuedas Gestion',
    description: 'Sistema de gestion para agencias de vehiculos.',
  },
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  // lang="es-AR": el idioma del documento es lo que usan los lectores de
  // pantalla para elegir la voz. Sin esto, un lector en ingles pronuncia el
  // castellano y no se entiende nada.
  return (
    <html lang="es-AR" className={inter.variable}>
      <body className="min-h-screen bg-white text-neutro-enfasis antialiased">
        <NavegacionPrincipal />
        {children}
        {/* Sin salida visual propia: escucha el teclado y abre su ayuda. */}
        <AtajosDeTeclado />
      </body>
    </html>
  );
}
