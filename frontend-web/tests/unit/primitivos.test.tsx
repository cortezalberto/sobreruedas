/**
 * Los primitivos del design system — C-07, `T-037`.
 *
 * QUE SE PRUEBA Y QUE NO
 * ───────────────────────
 * NO se prueban clases de CSS. El estilo va a cambiar —los tokens son de hoy y
 * los primitivos van a evolucionar— y un test contra `className` se rompe sin
 * que nada haya dejado de funcionar. Peor: pasa a verde con un componente
 * roto mientras la clase siga ahi.
 *
 * Se prueba el CONTRATO accesible, que es lo que no puede cambiar sin romper a
 * alguien: el rol que expone cada pieza, cuando interrumpe a un lector de
 * pantalla y cuando no, y los defaults que evitan errores dificiles de ver.
 */
import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { Alerta, Boton, Esqueleto, EstadoVacio, Etiqueta, Tarjeta } from '@/components/ui';

describe('Boton', () => {
  it('es un boton y no un submit por defecto', () => {
    // El default del HTML es `submit`. Un boton suelto dentro de un formulario
    // que lo envia sin querer es de los errores mas dificiles de ver leyendo el
    // JSX, asi que el default se invierte a proposito.
    render(<Boton>Guardar</Boton>);

    expect(screen.getByRole('button', { name: 'Guardar' })).toHaveAttribute('type', 'button');
  });

  it('puede declararse submit explicitamente', () => {
    render(<Boton type="submit">Enviar</Boton>);

    expect(screen.getByRole('button', { name: 'Enviar' })).toHaveAttribute('type', 'submit');
  });

  it('no dispara la accion cuando esta deshabilitado', () => {
    const alHacerClic = vi.fn();
    render(
      <Boton onClick={alHacerClic} disabled>
        Borrar
      </Boton>,
    );

    screen.getByRole('button').click();

    expect(alHacerClic).not.toHaveBeenCalled();
  });
});

describe('Alerta', () => {
  it('interrumpe al lector cuando es un error', () => {
    render(<Alerta tono="error" titulo="No se pudo guardar" />);

    expect(screen.getByRole('alert')).toHaveTextContent('No se pudo guardar');
  });

  it('interrumpe tambien cuando es una advertencia', () => {
    render(<Alerta tono="advertencia" titulo="Estas por superar el limite" />);

    expect(screen.getByRole('alert')).toBeInTheDocument();
  });

  it('NO interrumpe cuando es un exito', () => {
    // `alert` corta la lectura en el momento. Para una confirmacion eso es
    // ruido: va `status`, que espera. Ponerle `alert` a todo hace que la gente
    // apague el lector, que es lo contrario de accesible.
    render(<Alerta tono="exito" titulo="Guardado" />);

    expect(screen.queryByRole('alert')).toBeNull();
    expect(screen.getByRole('status')).toHaveTextContent('Guardado');
  });

  it('el titulo viaja siempre, que es el canal de texto que WCAG 1.4.1 exige', () => {
    // Una alerta que solo se distingue por el color del borde no cumple para
    // quien no diferencia rojo de naranja — y ese es justo el par de estados.
    render(<Alerta tono="error" titulo="Fallo la carga" />);

    expect(screen.getByText('Fallo la carga')).toBeInTheDocument();
  });
});

describe('Tarjeta', () => {
  it('no es clickeable por si misma', () => {
    // Una tarjeta con `onClick` no es alcanzable por teclado ni anunciable. Lo
    // interactivo va adentro; la tarjeta solo envuelve.
    render(
      <Tarjeta interactiva>
        <a href="/planes">Ver planes</a>
      </Tarjeta>,
    );

    expect(screen.queryByRole('button')).toBeNull();
    expect(screen.getByRole('link', { name: 'Ver planes' })).toBeInTheDocument();
  });
});

describe('Etiqueta', () => {
  it('muestra el estado como texto y no solo como color', () => {
    render(<Etiqueta tono="exito">Activa</Etiqueta>);

    expect(screen.getByText('Activa')).toBeInTheDocument();
  });
});

describe('EstadoVacio', () => {
  it('ofrece una salida, porque un vacio sin accion deja al usuario parado', () => {
    render(
      <EstadoVacio
        titulo="Todavia no cargaste vehiculos"
        descripcion="Cuando cargues el primero va a aparecer acá."
        accion={<Boton>Cargar vehiculo</Boton>}
      />,
    );

    expect(screen.getByRole('button', { name: 'Cargar vehiculo' })).toBeInTheDocument();
  });

  it('funciona sin accion, para los vacios que no la tienen', () => {
    render(<EstadoVacio titulo="Sin resultados" />);

    expect(screen.getByText('Sin resultados')).toBeInTheDocument();
    expect(screen.queryByRole('button')).toBeNull();
  });
});

describe('Esqueleto', () => {
  it('se oculta de los lectores de pantalla', () => {
    // Quien anuncia la espera es el contenedor con `aria-busy`. Un esqueleto
    // leido en voz alta es una ristra de nada.
    const { container } = render(<Esqueleto />);

    expect(container.firstElementChild).toHaveAttribute('aria-hidden', 'true');
  });
});
