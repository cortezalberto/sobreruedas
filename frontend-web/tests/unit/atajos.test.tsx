/**
 * Atajos de teclado y el Modal — C-07.
 *
 * Lo que se prueba es la MECANICA, que es donde estan los errores reales de esta
 * clase de componente: que un atajo no se dispare mientras alguien escribe, que
 * el acorde no quede armado para siempre, y que el dialogo sea anunciable.
 */
import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { AtajosDeTeclado } from '@/components/AtajosDeTeclado';

const { push } = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock('next/navigation', () => ({ useRouter: () => ({ push }) }));

beforeEach(() => {
  push.mockClear();
  vi.useFakeTimers({ shouldAdvanceTime: true });
});

afterEach(() => {
  vi.useRealTimers();
});

function teclear(tecla: string, opciones: KeyboardEventInit = {}): void {
  fireEvent.keyDown(window, { key: tecla, ...opciones });
}

describe('acorde G + tecla', () => {
  it('navega al catalogo con G y despues C', () => {
    render(<AtajosDeTeclado />);

    teclear('g');
    teclear('c');

    expect(push).toHaveBeenCalledWith('/catalogo');
  });

  it('una tecla sola no navega', () => {
    // Sin la `g` previa, la `c` es una letra cualquiera.
    render(<AtajosDeTeclado />);

    teclear('c');

    expect(push).not.toHaveBeenCalled();
  });

  it('el acorde se desarma solo', () => {
    // Sin esto la `G` queda armada indefinidamente, y la proxima `c` que alguien
    // apriete —minutos despues, en otra pantalla— navega sola.
    render(<AtajosDeTeclado />);

    teclear('g');
    // `act` porque el temporizador dispara un `setState`: sin el, React avisa
    // que la actualizacion quedo fuera del ciclo y el test no ve el efecto.
    act(() => vi.advanceTimersByTime(2000));
    teclear('c');

    expect(push).not.toHaveBeenCalled();
  });

  it('una segunda tecla sin destino no navega ni deja el acorde armado', () => {
    render(<AtajosDeTeclado />);

    teclear('g');
    teclear('z');
    teclear('c');

    expect(push).not.toHaveBeenCalled();
  });
});

describe('los atajos no interfieren con la escritura', () => {
  it('escribir en un campo no dispara el acorde', () => {
    // Tipear "gc" en un buscador no puede sacarte de la pagina.
    render(
      <>
        <input aria-label="Buscar" />
        <AtajosDeTeclado />
      </>,
    );
    const campo = screen.getByLabelText('Buscar');

    fireEvent.keyDown(campo, { key: 'g' });
    fireEvent.keyDown(campo, { key: 'c' });

    expect(push).not.toHaveBeenCalled();
  });

  it('un atajo con Ctrl no lo toma el acorde', () => {
    // `Ctrl+K` y compania son otra combinacion, todavia sin implementar.
    render(<AtajosDeTeclado />);

    teclear('g', { ctrlKey: true });
    teclear('c');

    expect(push).not.toHaveBeenCalled();
  });
});

describe('ayuda con ?', () => {
  it('abre el dialogo y lo anuncia con su nombre', () => {
    render(<AtajosDeTeclado />);

    teclear('?');

    expect(screen.getByRole('dialog', { name: /atajos de teclado/i })).toBeInTheDocument();
  });

  it('lista tambien los atajos que todavia no tienen destino', () => {
    // La ayuda dice la verdad sobre lo que hay: los pendientes se muestran
    // marcados en vez de esconderse, que seria prometer menos de lo que el
    // producto va a tener y mas de lo que hoy hace.
    render(<AtajosDeTeclado />);

    teclear('?');

    expect(screen.getByText(/Ir al stock/)).toBeInTheDocument();
    // `getAllByText`: hay ocho pendientes, no uno.
    expect(screen.getAllByText(/pendiente/).length).toBeGreaterThan(1);
  });

  it('no esta abierto antes de pedirlo', () => {
    render(<AtajosDeTeclado />);

    expect(screen.queryByRole('dialog')).toBeNull();
  });
});
