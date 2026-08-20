-- Agencia de desarrollo — se corre con `make seed`, junto con sembrar_dev.py.
--
-- Identificadores FIJOS y de una sola cifra repetida, a proposito: un UUID de
-- `1`s se distingue de un dato real de un vistazo, y hace que los ejemplos de
-- la documentacion y los `curl` de prueba no envejezcan.
--
-- Idempotente. Hay que volver a correrlo despues de `docker compose down -v`.

\set ON_ERROR_STOP on

INSERT INTO tenants (id, name, slug, cuit, billing_email, status, plan_id)
VALUES (
  '11111111-1111-1111-1111-111111111111',
  'Agencia Demo',
  'agencia-demo',
  '30-71234567-0',
  'demo@deruedas.test',
  'active',
  (SELECT id FROM plans WHERE code = 'pro')
)
ON CONFLICT (id) DO UPDATE
  SET status  = EXCLUDED.status,
      -- Sin plan, `PlanLimitsService` falla cerrado y no se puede cargar nada.
      plan_id = COALESCE(tenants.plan_id, EXCLUDED.plan_id);

INSERT INTO branches (id, tenant_id, name, city, province, is_active)
VALUES
  ('22222222-2222-2222-2222-222222222222',
   '11111111-1111-1111-1111-111111111111',
   'Casa central', 'Mendoza', 'Mendoza', true)
ON CONFLICT (id) DO UPDATE SET is_active = true;

SELECT t.name AS agencia, p.code AS plan,
       (SELECT count(*) FROM branches b WHERE b.tenant_id = t.id) AS sucursales,
       (SELECT count(*) FROM vehicles v
         WHERE v.tenant_id = t.id AND v.deleted_at IS NULL) AS vehiculos
FROM tenants t
LEFT JOIN plans p ON p.id = t.plan_id
WHERE t.id = '11111111-1111-1111-1111-111111111111';
