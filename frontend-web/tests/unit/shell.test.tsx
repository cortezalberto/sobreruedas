/**
 * El shell: encabezado, barra lateral y un unico landmark de contenido.
 *
 * POR QUE HAY UN TEST QUE LEE ARCHIVOS
 * ─────────────────────────────────────
 * `RootLayout` devuelve `<html>`, y `@testing-library` no puede montarlo: lo
 * insertaria dentro del `<body>` del documento de prueba. Asi que la propiedad
 * que importa —"hay un solo `<main>` en la pagina"— no se puede afirmar
 * renderizando.
 *
 * Se afirma sobre el codigo fuente, que para esta propiedad alcanza: el
 * landmark es del shell, y ninguna pagina puede declarar el suyo.
 */
import { readFileSync, readdirSync } from 'node:fs';
import { join, resolve } from 'node:path';

import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { Encabezado } from '@/components/Encabezado';
import { NavegacionPrincipal } from '@/components/NavegacionPrincipal';
import { SECCIONES } from '@/lib/secciones';

const { usePathname } = vi.hoisted(() => ({ usePathname: vi.fn() }));

vi.mock('next/navigation', () => ({ usePathname }));

const APP = resolve(__dirname, '../../src/app');

/** Todo `.tsx` bajo `src/app`, incluidas las rutas dinamicas como `[marca]`. */
function archivosDeApp(directorio: string = APP): string[] {
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- ruta derivada de una constante del repo
  return readdirSync(directorio, { withFileTypes: true }).flatMap((entrada) => {
    const ruta = join(directorio, entrada.name);
    if (entrada.isDirectory()) return archivosDeApp(ruta);
    return entrada.name.endsWith('.tsx') ? [ruta] : [];
  });
}

/**
 * El fuente sin sus comentarios.
 *
 * Estos archivos EXPLICAN en sus comentarios por que el `<main>` es del shell,
 * y para explicarlo lo nombran. Un control que mira texto crudo rechazaria al
 * archivo que documenta la regla que el control defiende — y un test que da
 * falso positivo termina desactivado. Mismo criterio que
 * `_sin_comentarios_de_shell` en el control de `ci.yml` del backend.
 *
 * Alcanza con los bloques `/* *\/`: cubre tambien los `{​/* *\/}` de JSX, que es
 * la unica forma de comentar dentro del arbol. Los `//` de linea se sacan solo
 * al principio de una linea, para no romper un `https://`.
 */
function sinComentarios(fuente: string): string {
  return fuente.replace(/\/\*[\s\S]*?\*\//g, '').replace(/^\s*\/\/.*$/gm, '');
}

function contenido(ruta: string): string {
  // eslint-disable-next-line security/detect-non-literal-fs-filename -- ruta enumerada desde src/app
  return sinComentarios(readFileSync(ruta, 'utf8'));
}

describe('el landmark de contenido es del shell', () => {
  const archivos = archivosDeApp();

  it('encuentra las pantallas que tiene que revisar', () => {
    // Sin esto, un `filter` que no encuentra nada haria pasar el test de abajo
    // sin haber mirado un solo archivo.
    expect(archivos.length).toBeGreaterThan(5);
  });

  it('solo el layout declara un <main>', () => {
    // Antes lo declaraban nueve archivos, repitiendo `mx-auto max-w-4xl p-8`. Y
    // durante el streaming convivian dos: el del esqueleto de carga y el del
    // contenido. Dos landmarks `main` rompen la navegacion por landmarks de un
    // lector de pantalla, que es justo para quien existen.
    const culpables = archivos
      .filter((ruta) => contenido(ruta).includes('<main'))
      .filter((ruta) => !ruta.endsWith('layout.tsx'));

    expect(culpables, `estas pantallas declaran su propio <main>: ${culpables}`).toEqual([]);
  });

  it('el layout declara exactamente uno', () => {
    const layout = contenido(join(APP, 'layout.tsx'));

    expect(layout.match(/<main[\s>]/g)).toHaveLength(1);
    expect(layout).toContain('</main>');
  });
});

describe('Encabezado', () => {
  it('el nombre del producto lleva al inicio', () => {
    render(<Encabezado />);

    expect(screen.getByRole('link', { name: 'deRuedas' })).toHaveAttribute('href', '/');
  });

  it('es un landmark de encabezado, y uno solo', () => {
    const { container } = render(<Encabezado />);

    expect(container.querySelectorAll('header')).toHaveLength(1);
  });
});

describe('la barra lateral', () => {
  it('no trae su propio landmark de encabezado', () => {
    // Vivia adentro de un `<header>` propio cuando era barra superior. Con el
    // encabezado del shell, dos `<header>` competirian en la navegacion por
    // landmarks — y el `<aside>` que la contiene lo pone el layout.
    usePathname.mockReturnValue('/');
    const { container } = render(<NavegacionPrincipal />);

    expect(container.querySelectorAll('header')).toHaveLength(0);
    expect(container.querySelectorAll('nav')).toHaveLength(1);
  });

  it('no ofrece las secciones que todavia no existen', () => {
    usePathname.mockReturnValue('/');
    render(<NavegacionPrincipal />);

    for (const seccion of SECCIONES.filter((s) => !s.existe)) {
      expect(
        screen.queryByRole('link', { name: seccion.etiqueta }),
        `${seccion.etiqueta} no tiene pantalla y aparece en la barra`,
      ).toBeNull();
    }
  });
});
