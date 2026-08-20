/**
 * Las secciones del producto se declaran UNA vez, y todo lo demas las deriva.
 *
 * QUE VINO A ARREGLAR ESTO
 * ─────────────────────────
 * El conocimiento de "que secciones hay" vivia repartido en TRES listas que
 * nadie obligaba a coincidir:
 *
 *   1. `SECCIONES` en `NavegacionPrincipal` — lo que se ve en la barra
 *   2. `ATAJOS` en `AtajosDeTeclado`        — la tabla de la ayuda con `?`
 *   3. `destinoDelAcorde()`                 — el `switch` que navega de verdad
 *
 * La 2 y la 3 estan en el mismo archivo y aun asi podian mentirse: la tabla
 * declaraba un `destino` que **nadie leia para navegar**. `G luego C` podia
 * decir "Ir al catálogo" en la ayuda y el `switch` mandar a otro lado, o a
 * ningun lado, sin que nada lo delatara.
 *
 * Ahora las tres salen de `lib/secciones.ts`. Estos tests defienden lo que esa
 * unica fuente tiene que cumplir para que derivarla sea seguro.
 */
import { existsSync } from 'node:fs';
import { resolve } from 'node:path';

import { describe, expect, it } from 'vitest';

import { SECCIONES, destinoDelAcorde, seccionesVisibles } from '@/lib/secciones';

describe('el catalogo de secciones', () => {
  it('no repite teclas de acorde', () => {
    // Dos secciones con la misma tecla hacen que una sea inalcanzable, y cual
    // de las dos depende del orden del array — o sea, del azar.
    const teclas = SECCIONES.filter((s) => s.tecla).map((s) => s.tecla);

    expect(teclas).toHaveLength(new Set(teclas).size);
  });

  it('no repite rutas', () => {
    const rutas = SECCIONES.map((s) => s.href);

    expect(rutas).toHaveLength(new Set(rutas).size);
  });

  it('declara las teclas en mayuscula', () => {
    // `destinoDelAcorde` recibe `evento.key.toLowerCase()`. Si el catalogo
    // mezclara mayusculas y minusculas, la comparacion fallaria para unas y
    // andaria para otras — y el sintoma seria "el atajo a veces no anda".
    for (const seccion of SECCIONES) {
      if (seccion.tecla) expect(seccion.tecla).toBe(seccion.tecla.toUpperCase());
    }
  });

  it('toda seccion con tecla explica su atajo', () => {
    // Sin `ayuda`, la tabla de `?` cae al `Ir a ${etiqueta}` generico y se lee
    // "Ir a Stock". La frase se escribe a mano; lo que no se puede es olvidarla.
    for (const seccion of SECCIONES.filter((s) => s.tecla)) {
      expect(seccion.ayuda, `${seccion.etiqueta} tiene tecla y no tiene ayuda`).toBeTruthy();
    }
  });

  it('declara las seis secciones del menu del producto', () => {
    // `knowledge-base/15` §Navegacion del producto define el menu principal.
    //
    // Esta afirmacion no envejece, y por eso sobrevive a que las seis pasaran a
    // tener pantalla: no dice cuales existen —de eso se ocupa el cruce contra
    // `src/app`—, dice cuales el producto se comprometio a tener. Borrar una de
    // `SECCIONES` seguiria siendo un incumplimiento aunque todo lo demas pase.
    const etiquetas = SECCIONES.map((s) => s.etiqueta);

    for (const seccion of ['Dashboard', 'Stock', 'Leads', 'Mensajes', 'Reportes', 'Configuración'])
      expect(etiquetas, `falta ${seccion} del menu de knowledge-base/15`).toContain(seccion);
  });
});

/**
 * El invariante que de verdad importa, y el unico que no envejece.
 *
 * `existe` es una afirmacion sobre el sistema de archivos: "esta seccion tiene
 * pantalla". Escrita a mano, se desincroniza en las dos direcciones y ninguna
 * duele hasta produccion:
 *
 *   - encendida de mas → la barra ofrece un item que da 404
 *   - encendida de menos → alguien construyo la pantalla y quedo inalcanzable,
 *     sin item en el menu y sin atajo
 *
 * Cruzarla contra `src/app` cierra las dos. Y no hay que acordarse de venir a
 * actualizar este archivo el dia que `/stock` exista: el test lo reclama solo.
 */
describe('`existe` contra las rutas de verdad', () => {
  const APP = resolve(__dirname, '../../src/app');

  /** Donde Next busca la pantalla de una ruta. `/` es `app/page.tsx`. */
  function pagina(href: string): string {
    return resolve(APP, href === '/' ? 'page.tsx' : `${href.slice(1)}/page.tsx`);
  }

  /**
   * `eslint-plugin-security` marca todo `existsSync` con argumento no literal.
   * Acá la ruta se arma desde `SECCIONES`, que es una constante de este
   * repositorio, y el proceso es un test que solo LEE. No hay entrada de
   * usuario en el camino — que es lo que la regla existe para atrapar.
   */
  function hayPantalla(href: string): boolean {
    // eslint-disable-next-line security/detect-non-literal-fs-filename -- ruta derivada de una constante del repo, no de entrada de usuario
    return existsSync(pagina(href));
  }

  it('toda seccion visible tiene su pantalla', () => {
    for (const seccion of seccionesVisibles()) {
      expect(hayPantalla(seccion.href), `${seccion.href} se muestra y no existe`).toBe(true);
    }
  });

  /**
   * Reemplaza a `ninguna seccion pendiente tiene pantalla ya construida`.
   *
   * Aquel test recorria `SECCIONES.filter((s) => !s.existe)`, y desde que el
   * menu entero tiene pantalla ese filtro da vacio: un `for` de cero vueltas
   * pasa sin afirmar nada. Esta forma dice lo mismo en las dos direcciones y no
   * se vacia nunca — mientras haya secciones declaradas, hay algo que verificar.
   */
  it('`existe` dice exactamente si hay pantalla, en las dos direcciones', () => {
    expect(SECCIONES.length).toBeGreaterThan(0);

    for (const seccion of SECCIONES) {
      expect(
        hayPantalla(seccion.href),
        seccion.existe
          ? `${seccion.href} se declara existente y no tiene pantalla`
          : `${seccion.href} ya tiene pantalla: falta encenderla en SECCIONES`,
      ).toBe(seccion.existe);
    }
  });

  it('el menu del producto esta entero en pantalla', () => {
    // Lo que se pidio: que la barra izquierda ofrezca los nueve items, tengan o
    // no funcionalidad. Una seccion declarada y sin pantalla queda invisible, y
    // la promesa del menu es justamente que estan todas.
    const sinPantalla = SECCIONES.filter((s) => !hayPantalla(s.href)).map((s) => s.href);

    expect(sinPantalla, `estas secciones no tienen pantalla: ${sinPantalla.join(', ')}`).toEqual(
      [],
    );
  });
});

describe('destinoDelAcorde', () => {
  /**
   * Antes esto eran dos tests: uno recorria las secciones que existen y otro
   * las pendientes, y el segundo se apoyaba en que hubiera al menos una
   * pendiente. Desde que el menu entero tiene pantalla no hay ninguna, y aquel
   * `expect(pendientes.length).toBeGreaterThan(0)` pasaba a fallar por una
   * razon que no era un defecto.
   *
   * La regla que hay que defender no era "hay pendientes": era que el acorde
   * lleve exactamente a lo que existe y a nada mas. Escrita asi cubre los dos
   * casos con un solo recorrido, sigue afirmando algo el dia que alguien
   * declare una seccion nueva sin pantalla, y no depende de que ese dia llegue.
   */
  it('lleva exactamente a las secciones que existen, y a ninguna otra', () => {
    const conTecla = SECCIONES.filter((s) => s.tecla);

    // Sin esto el test seria vacuo: con el array vacio, un `for` de cero
    // vueltas pasa igual y no habria afirmado nada.
    expect(conTecla.length).toBeGreaterThan(0);

    for (const seccion of conTecla) {
      // El error que este proyecto ya se marco solo: "un redirect a una ruta que
      // no existe seria un 404 disfrazado de feature".
      expect(
        destinoDelAcorde(seccion.tecla!.toLowerCase()),
        `${seccion.etiqueta} existe=${seccion.existe}`,
      ).toBe(seccion.existe ? seccion.href : undefined);
    }
  });

  it('ignora una tecla que no es de nadie', () => {
    expect(destinoDelAcorde('z')).toBeUndefined();
  });

  it('no se deja engañar por una propiedad del prototipo', () => {
    // Por esto la busqueda es un `find` sobre el array y no un objeto indexado:
    // con un objeto plano, apretar `G` y despues `constructor` devuelve algo.
    expect(destinoDelAcorde('constructor')).toBeUndefined();
    expect(destinoDelAcorde('__proto__')).toBeUndefined();
  });
});

describe('seccionesVisibles', () => {
  it('deja afuera lo que no existe', () => {
    // Mismo criterio que los atajos: navegacion muerta no se muestra. Un item
    // de menu que lleva a un 404 le enseña al usuario a desconfiar del menu.
    expect(seccionesVisibles().every((s) => s.existe)).toBe(true);
  });

  it('conserva el orden del catalogo', () => {
    const esperado = SECCIONES.filter((s) => s.existe).map((s) => s.href);

    expect(seccionesVisibles().map((s) => s.href)).toEqual(esperado);
  });
});
