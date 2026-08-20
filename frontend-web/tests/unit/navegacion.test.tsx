/**
 * La navegacion marca donde estas, y lo hace de forma accesible.
 *
 * Se prueba `aria-current` y no la clase de CSS: el subrayado se lo lleva C-07
 * cuando llegue el design system, y el atributo es lo que un lector de pantalla
 * anuncia. Un test contra `className` se rompe con el primer cambio de estilo
 * sin que nada haya dejado de funcionar.
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { NavegacionPrincipal } from '@/components/NavegacionPrincipal';
import { SECCIONES } from '@/lib/secciones';

const { usePathname } = vi.hoisted(() => ({ usePathname: vi.fn() }));

vi.mock('next/navigation', () => ({ usePathname }));

function enRuta(pathname: string): void {
  usePathname.mockReturnValue(pathname);
}

describe('NavegacionPrincipal', () => {
  it('marca la seccion actual', () => {
    enRuta('/planes');
    render(<NavegacionPrincipal />);

    expect(screen.getByRole('link', { name: 'Planes' })).toHaveAttribute('aria-current', 'page');
  });

  it('no marca las secciones donde no estas', () => {
    enRuta('/planes');
    render(<NavegacionPrincipal />);

    expect(screen.getByRole('link', { name: 'Inicio' })).not.toHaveAttribute('aria-current');
  });

  it('inicio solo es actual en la raiz exacta', () => {
    // El caso que un `startsWith` ingenuo rompe: `'/planes'.startsWith('/')` es
    // verdadero, asi que Inicio quedaria marcado como actual en TODAS las rutas
    // y el indicador dejaria de significar nada.
    enRuta('/planes');
    render(<NavegacionPrincipal />);

    expect(screen.getByRole('link', { name: 'Inicio' })).not.toHaveAttribute('aria-current');
  });

  it('marca inicio cuando estas en la raiz', () => {
    enRuta('/');
    render(<NavegacionPrincipal />);

    expect(screen.getByRole('link', { name: 'Inicio' })).toHaveAttribute('aria-current', 'page');
  });

  it('muestra los nueve items del menu, tengan funcionalidad o no', () => {
    // El menu de `knowledge-base/15` completo. Cinco de estas secciones son
    // pantallas en construccion, y aun asi se ofrecen: la barra es el mapa del
    // producto, no la lista de lo que ya funciona. Lo que no se puede es que un
    // item lleve a un 404 — de eso se ocupa `secciones.test.ts`.
    enRuta('/');
    render(<NavegacionPrincipal />);

    for (const seccion of SECCIONES) {
      expect(
        screen.getByRole('link', { name: seccion.etiqueta }),
        `falta ${seccion.etiqueta} en la barra`,
      ).toHaveAttribute('href', seccion.href);
    }
  });

  it('no esconde ninguna seccion declarada', () => {
    // El conteo, aparte de los nombres: un item de mas —una ruta que la barra
    // ofrece y el catalogo no declara— no lo atrapa el test de arriba.
    enRuta('/');
    render(<NavegacionPrincipal />);

    expect(screen.getAllByRole('link')).toHaveLength(SECCIONES.length);
  });

  it('la barra se anuncia como navegacion con nombre', () => {
    enRuta('/');
    render(<NavegacionPrincipal />);

    expect(screen.getByRole('navigation', { name: /principal/i })).toBeInTheDocument();
  });
});
