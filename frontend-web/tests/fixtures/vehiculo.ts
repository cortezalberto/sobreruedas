/**
 * Un vehículo con los 23 campos que el backend manda de verdad.
 *
 * POR QUE ES COMPARTIDO Y NO UNO POR ARCHIVO. Cuando la ficha extendió la
 * interfaz `Vehiculo` de 11 campos a 23, el único fixture que existía dejó de
 * compilar — y eso estuvo bien: es exactamente lo que su comentario prometía,
 * *"los campos que no importan acá se rellenan igual porque el tipo los exige"*.
 * Lo que no está bien es tener que arreglar esa lista en cada archivo de test el
 * día que el backend agregue un campo. Con un solo fixture, `tsc` marca un lugar.
 *
 * ⚠️ `acquisition_cost_ars` NO ESTA, y su ausencia es el default a propósito: es
 * lo que recibe un `salesperson` por `RN-ST-12`, y es el caso que más fácil se
 * escapa. Quien necesite el otro lo pasa por `extra`.
 */
import type { Vehiculo } from '@/lib/api';

export function vehiculo(extra: Partial<Vehiculo> = {}): Vehiculo {
  return {
    id: '00000000-0000-4000-8000-000000000001',
    tenant_id: '00000000-0000-4000-8000-0000000000t1',
    branch_id: '00000000-0000-4000-8000-0000000000s1',
    assigned_user_id: null,
    domain_plate: 'AB123CD',
    chassis_number: null,
    brand_id: '00000000-0000-4000-8000-0000000000b1',
    model_id: '00000000-0000-4000-8000-0000000000m1',
    version_id: null,
    year: 2021,
    mileage_km: 30000,
    color: 'Blanco',
    fuel_type: 'gasoline',
    transmission: 'manual',
    body_type: 'sedan',
    status: 'available',
    price_ars: '15000000.00',
    price_usd: null,
    description: null,
    features: [],
    acquired_at: null,
    sold_at: null,
    created_at: '2026-08-01T13:45:00Z',
    ...extra,
  };
}
