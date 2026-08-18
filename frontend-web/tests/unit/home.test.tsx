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

  it('sigue diciendo en que ola esta el producto', () => {
    render(<HomePage />);
    expect(screen.getByText(/Ola 0/i)).toBeInTheDocument();
  });

  it('lleva al catalogo de planes', () => {
    // Hasta el 18-ago-2026 esta pagina afirmaba que "todavia no hay
    // funcionalidad de negocio". Desde que existe `/planes` eso es falso, y
    // este test fija que la home ofrezca lo que el sistema ya sabe hacer.
    render(<HomePage />);
    expect(screen.getByRole('link', { name: /planes/i })).toHaveAttribute('href', '/planes');
  });

  it('no ofrece inicio de sesion todavia', () => {
    // La home NO redirige a /login: eso es C-05. Este test fija ese limite
    // para que nadie lo agregue a medias sin darse cuenta.
    render(<HomePage />);
    expect(screen.queryByRole('link', { name: /iniciar sesion/i })).toBeNull();
  });
});
