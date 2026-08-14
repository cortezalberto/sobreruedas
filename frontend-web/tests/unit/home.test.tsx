import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import HomePage from '@/app/page';

describe('HomePage', () => {
  it('muestra el nombre del producto como encabezado principal', () => {
    render(<HomePage />);
    // Se busca por ROL y no por clase ni por id: es lo que ve un lector de
    // pantalla. Un test que pasa con un <div> estilado no prueba nada de
    // accesibilidad.
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('deRuedas Gestion');
  });

  it('avisa que todavia no hay funcionalidad de negocio', () => {
    render(<HomePage />);
    expect(screen.getByText(/Ola 0/i)).toBeInTheDocument();
  });

  it('no ofrece inicio de sesion todavia', () => {
    // La home NO redirige a /login: eso es C-05. Este test fija ese limite
    // para que nadie lo agregue a medias sin darse cuenta.
    render(<HomePage />);
    expect(screen.queryByRole('link', { name: /iniciar sesion/i })).toBeNull();
  });
});
