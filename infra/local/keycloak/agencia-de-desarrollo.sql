-- Una agencia de desarrollo con su sucursal.
--
-- ⚠️ SOLO DESARROLLO. En un entorno real las agencias las crea el onboarding
-- (C-10) y el alta pasa por la validación de CUIT y los límites de plan.
--
-- POR QUE HACE FALTA
-- ───────────────────
-- El token de `usuario-de-desarrollo.sh` trae un `tenant_id`, pero `vehicles`
-- tiene FK a `tenants` y a `branches`: sin estas dos filas, el primer POST
-- devuelve un error de clave foránea que no dice nada útil.
--
-- El UUID es el mismo que usa ese script. Fijo a propósito: si fuera aleatorio
-- habría que sincronizarlo a mano con el atributo del usuario cada vez.
--
-- Se corre con el rol PROPIETARIO —`tenants` no tiene política RLS y el rol de
-- aplicación no la escribe (design.md D-1 de C-04)—:
--
--     docker compose exec -T postgres psql -U deruedas -d deruedas \
--       -f /dev/stdin < infra/local/keycloak/agencia-de-desarrollo.sql

INSERT INTO tenants (id, name, slug, cuit, billing_email, status)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    'Agencia Demo',
    'agencia-demo',
    -- CUIT con dígito verificador válido: el validador de la aplicación lo
    -- rechazaría si se inventara, y entonces el alta por API fallaría con un
    -- error que parecería del endpoint y sería del dato.
    '30111111118',
    'facturacion@agencia-demo.test',
    'active'
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO branches (id, tenant_id, name, city, province)
VALUES (
    '22222222-2222-2222-2222-222222222222',
    '11111111-1111-1111-1111-111111111111',
    'Casa central',
    'Mendoza',
    'Mendoza'
)
ON CONFLICT (id) DO NOTHING;

SELECT t.name AS agencia, t.slug, b.name AS sucursal, b.id AS branch_id
FROM tenants t
JOIN branches b ON b.tenant_id = t.id
WHERE t.id = '11111111-1111-1111-1111-111111111111';
