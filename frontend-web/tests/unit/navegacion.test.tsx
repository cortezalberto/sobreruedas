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

  it('la barra se anuncia como navegacion con nombre', () => {
    enRuta('/');
    render(<NavegacionPrincipal />);

    expect(screen.getByRole('navigation', { name: /principal/i })).toBeInTheDocument();
  });
});
