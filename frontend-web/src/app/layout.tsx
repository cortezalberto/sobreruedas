import type { Metadata, Viewport } from 'next';

import { NavegacionPrincipal } from '@/components/NavegacionPrincipal';

import './globals.css';

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
    <html lang="es-AR">
      <body className="min-h-screen bg-white text-slate-900 antialiased">
        <NavegacionPrincipal />
        {children}
      </body>
    </html>
  );
}
