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
import { SUPERFICIE_DE_TARJETA } from '@/lib/tokens';
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

describe('la superficie de tarjeta sale del design system', () => {
  it('ninguna pantalla la copia a mano', () => {
    // Habia cuatro copias del string en `/` y `/catalogo`. Una copia no rompe
    // nada el dia que se escribe: rompe el dia que el design system cambia el
    // radio o el borde y estas cuatro se quedan con el anterior, sin que
    // ningun test se entere porque cada pantalla sigue renderizando igual.
    //
    // Se compara contra la constante y no contra un literal repetido acá: si
    // alguien cambia la superficie, este control sigue midiendo la vigente.
    //
    // ⚠️ Sin ancla. La primera version buscaba `"${SUPERFICIE_DE_TARJETA}` —con
    // la comilla adelante— para no marcar los usos legitimos. No hacia falta:
    // los usos legitimos son `${SUPERFICIE_DE_TARJETA}` en un template, que
    // nunca contiene el string literal. Y la comilla dejaba pasar el caso real,
    // que es la superficie en medio de otras clases (`mt-8 rounded-lg ...`).
    // El control pasaba con la copia puesta: lo delato la mutacion.
    const culpables = archivosDeApp().filter((ruta) =>
      contenido(ruta).includes(SUPERFICIE_DE_TARJETA),
    );

    expect(culpables, `estas pantallas copian la superficie a mano: ${culpables}`).toEqual([]);
  });

  it('el modulo que la declara sigue siendo seguro para el servidor', () => {
    /*
     * ⚠️ ESTE TEST EXISTE POR UN BUG QUE NINGUN TEST PODIA VER.
     *
     * Las superficies vivieron un rato en `components/ui/index.tsx`, que lleva
     * `'use client'`. Cuando un Server Component importa una CONSTANTE de un
     * modulo cliente, Next no le entrega el valor: le entrega una referencia al
     * cliente. Interpolarla en un template la convierte en el texto de un stub,
     * y el `className` renderizado quedaba:
     *
     *   "mt-8 p-4 function() { throw new Error(\"Attempted to call
     *    SUPERFICIE_DE_TARJETA() from the server ...\"); }"
     *
     * La tarjeta se quedaba sin borde y sin radio, en silencio.
     *
     * `vitest` importa los modulos directo, sin frontera RSC, asi que ahi la
     * constante es un string de verdad y todo pasa. `tsc` y `eslint` tampoco lo
     * ven. Lo encontro mirar la pagina corriendo — y por eso el unico control
     * posible es este: que el modulo NO se vuelva cliente.
     */
    // Sin comentarios, por segunda vez en este archivo: `tokens.ts` EXPLICA en
    // su encabezado por que no puede ser `'use client'`, y para explicarlo lo
    // escribe. La directiva de verdad es una sentencia y sobrevive al filtro.
    const tokens = sinComentarios(
      readFileSync(resolve(__dirname, '../../src/lib/tokens.ts'), 'utf8'),
    );

    expect(tokens).not.toContain('use client');
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
