/**
 * El formulario de alta de vehículo.
 *
 * QUÉ SE PRUEBA ACÁ Y QUÉ NO. Las reglas de validación viven en
 * `lib/vehiculo-nuevo.ts` y se prueban ahí, sin montar React. Este archivo
 * prueba lo que SOLO existe cuando el componente está montado:
 *
 *   - que no se mande al backend un borrador que ya sabemos que está mal
 *   - que el error aparezca atado al campo que lo causó
 *   - que elegir una marca cargue sus modelos y limpie el modelo anterior
 *   - que el rechazo del backend se muestre y NO se pierda el borrador
 *
 * Lo último importa más de lo que parece: si un 403 limpiara el formulario, el
 * usuario perdería catorce campos por un error que no es suyo.
 */
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { FormularioDeVehiculo } from '@/components/FormularioDeVehiculo';
import type { Marca, Sucursal } from '@/lib/api';

const crearVehiculo = vi.fn();
const obtenerModelos = vi.fn();
const empujar = vi.fn();

vi.mock('@/app/stock/acciones', () => ({
  crearVehiculo: (...args: unknown[]) => crearVehiculo(...args),
}));

vi.mock('@/lib/api', async (original) => ({
  ...(await original<Record<string, unknown>>()),
  obtenerModelos: (...args: unknown[]) => obtenerModelos(...args),
}));

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: empujar, refresh: vi.fn() }),
}));

const SUCURSALES: Sucursal[] = [
  {
    id: 'suc-1',
    tenant_id: 'tenant-1',
    name: 'Casa central',
    city: 'Mendoza',
    province: 'Mendoza',
    address: null,
    phone: null,
    is_active: true,
    created_at: '2026-08-19T01:16:04Z',
  },
];

const MARCAS: Marca[] = [{ id: 'marca-1', name: 'Chery', slug: 'chery', origin_country: 'CN' }];

const MODELOS = [
  {
    id: 'modelo-1',
    brand_id: 'marca-1',
    name: 'Tiggo 2',
    body_type: 'suv',
    year_from: 2018,
    year_to: null,
  },
];

beforeEach(() => {
  crearVehiculo.mockReset();
  obtenerModelos.mockReset();
  empujar.mockReset();
  obtenerModelos.mockResolvedValue(MODELOS);
});

afterEach(() => {
  vi.clearAllMocks();
});

function montar() {
  return render(<FormularioDeVehiculo sucursales={SUCURSALES} marcas={MARCAS} />);
}

/** Completa el formulario entero con datos válidos. */
async function completarTodo() {
  fireEvent.change(screen.getByLabelText('Sucursal'), { target: { value: 'suc-1' } });
  fireEvent.change(screen.getByLabelText('Marca'), { target: { value: 'marca-1' } });
  await waitFor(() => expect(screen.getByLabelText('Modelo')).not.toBeDisabled());
  fireEvent.change(screen.getByLabelText('Modelo'), { target: { value: 'modelo-1' } });
  fireEvent.change(screen.getByLabelText(/Dominio/), { target: { value: 'AB123CD' } });
  fireEvent.change(screen.getByLabelText('Año'), { target: { value: '2020' } });
  fireEvent.change(screen.getByLabelText('Kilómetros'), { target: { value: '45000' } });
  fireEvent.change(screen.getByLabelText('Color'), { target: { value: 'Gris' } });
  fireEvent.change(screen.getByLabelText('Combustible'), { target: { value: 'gasoline' } });
  fireEvent.change(screen.getByLabelText('Transmisión'), { target: { value: 'manual' } });
  fireEvent.change(screen.getByLabelText('Carrocería'), { target: { value: 'sedan' } });
  fireEvent.change(screen.getByLabelText(/Precio de venta/), { target: { value: '18500000' } });
}

function guardar() {
  fireEvent.click(screen.getByRole('button', { name: /cargar veh/i }));
}

describe('antes de mandar', () => {
  it('NO llama al backend cuando el borrador está vacío', async () => {
    montar();

    guardar();

    await waitFor(() => expect(screen.getAllByRole('alert').length).toBeGreaterThan(0));
    expect(crearVehiculo).not.toHaveBeenCalled();
  });

  it('muestra el error ATADO al campo que lo causó', async () => {
    montar();
    await completarTodo();
    fireEvent.change(screen.getByLabelText('Año'), { target: { value: '1800' } });

    guardar();

    // Es la razón de ser de la validación del cliente: el backend manda este
    // mismo error con `field: "body"` y no se podría señalar el campo.
    await waitFor(() =>
      expect(screen.getByLabelText('Año')).toHaveAttribute('aria-invalid', 'true'),
    );
    expect(crearVehiculo).not.toHaveBeenCalled();
  });

  it('limpia el error del campo apenas el usuario lo corrige', async () => {
    montar();
    await completarTodo();
    fireEvent.change(screen.getByLabelText('Año'), { target: { value: '1800' } });
    guardar();
    await waitFor(() =>
      expect(screen.getByLabelText('Año')).toHaveAttribute('aria-invalid', 'true'),
    );

    fireEvent.change(screen.getByLabelText('Año'), { target: { value: '2020' } });

    // Dejar el rojo puesto mientras el usuario ya lo arregló entrena a
    // ignorarlo, y después el error que sí importa tampoco se ve.
    await waitFor(() => expect(screen.getByLabelText('Año')).not.toHaveAttribute('aria-invalid'));
  });
});

describe('la cascada marca → modelo', () => {
  it('deshabilita el modelo hasta que haya marca', () => {
    montar();

    expect(screen.getByLabelText('Modelo')).toBeDisabled();
  });

  it('carga los modelos de la marca elegida', async () => {
    montar();

    fireEvent.change(screen.getByLabelText('Marca'), { target: { value: 'marca-1' } });

    await waitFor(() => expect(obtenerModelos).toHaveBeenCalledWith('marca-1'));
    await waitFor(() => expect(screen.getByLabelText('Modelo')).not.toBeDisabled());
  });

  it('olvida el modelo elegido al cambiar de marca', async () => {
    montar();
    fireEvent.change(screen.getByLabelText('Marca'), { target: { value: 'marca-1' } });
    await waitFor(() => expect(screen.getByLabelText('Modelo')).not.toBeDisabled());
    fireEvent.change(screen.getByLabelText('Modelo'), { target: { value: 'modelo-1' } });

    fireEvent.change(screen.getByLabelText('Marca'), { target: { value: '' } });

    // Un modelo de la marca anterior con la marca nueva es un par que no
    // existe, y el backend lo aceptaría sin chistar: son dos ids sueltos.
    expect(screen.getByLabelText('Modelo')).toHaveValue('');
  });
});

describe('al mandar', () => {
  it('manda el cuerpo ya normalizado', async () => {
    crearVehiculo.mockResolvedValue({ ok: true, mensaje: 'Vehículo cargado.', id: 'v-1' });
    montar();
    await completarTodo();
    fireEvent.change(screen.getByLabelText(/Dominio/), { target: { value: 'ab-123-cd' } });

    guardar();

    await waitFor(() => expect(crearVehiculo).toHaveBeenCalledTimes(1));
    expect(crearVehiculo.mock.calls[0]?.[0]).toMatchObject({
      branch_id: 'suc-1',
      brand_id: 'marca-1',
      model_id: 'modelo-1',
      domain_plate: 'AB123CD',
      year: 2020,
      price_ars: '18500000',
    });
  });

  it('vuelve al stock cuando el alta sale bien', async () => {
    crearVehiculo.mockResolvedValue({ ok: true, mensaje: 'Vehículo cargado.', id: 'v-1' });
    montar();
    await completarTodo();

    guardar();

    await waitFor(() => expect(empujar).toHaveBeenCalledWith('/stock'));
  });

  it('muestra el rechazo del backend SIN perder lo cargado', async () => {
    crearVehiculo.mockResolvedValue({
      ok: false,
      mensaje: 'Ya hay un vehículo cargado con ese dominio.',
    });
    montar();
    await completarTodo();

    guardar();

    await waitFor(() => expect(screen.getByText(/Ya hay un vehículo cargado/)).toBeInTheDocument());
    // Lo que el usuario escribió sigue ahí: el rechazo no es culpa del
    // formulario y perder catorce campos por un 403 es inaceptable.
    expect(screen.getByLabelText('Color')).toHaveValue('Gris');
    expect(empujar).not.toHaveBeenCalled();
  });

  it('no manda dos veces si alguien hace doble clic', async () => {
    let resolver: (valor: unknown) => void = () => {};
    crearVehiculo.mockReturnValue(new Promise((r) => (resolver = r)));
    montar();
    await completarTodo();

    // Se toma el NODO una sola vez y se lo clickea dos. Buscarlo por su nombre
    // la segunda vez no serviría: apenas empieza el envío el botón pasa a decir
    // "Cargando…", así que el test fallaría por no encontrarlo y no por el
    // comportamiento que quiere fijar.
    const boton = screen.getByRole('button', { name: /cargar veh/i });
    fireEvent.click(boton);
    fireEvent.click(boton);

    // Sin el guard se cargan DOS vehículos, el segundo choca contra `RN-ST-01`
    // y el usuario ve un error de duplicado por un auto que cargó una vez.
    await waitFor(() => expect(crearVehiculo).toHaveBeenCalledTimes(1));
    resolver({ ok: true, mensaje: 'Vehículo cargado.' });
  });
});
