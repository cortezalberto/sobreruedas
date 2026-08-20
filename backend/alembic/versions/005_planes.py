"""catalogo de planes comerciales, con su seed

Por que existe (C-04): `plans` es el catalogo del SaaS y `tenants.plan_id` lo
referencia, asi que va antes que `tenants`.

TABLA COMPARTIDA, SIN `tenant_id` Y SIN RLS
────────────────────────────────────────────
`plans` es el mismo catalogo para todas las agencias y no contiene dato de
ninguna. Por eso no lleva `tenant_id` y esta declarada en `EXENTAS_DE_RLS`
(`RN-MT-09`), donde ya figuraba antes de que la tabla existiera. Ver design.md
D-1: la exencion es estructural, no una concesion.

DE DONDE SALEN LOS NUMEROS — Y POR QUE DE DOS DOCUMENTOS DISTINTOS
───────────────────────────────────────────────────────────────────
  - LIMITES: de `plan-gtm` (decision de Direccion, IN-03, design.md D-2)
  - PRECIOS: de `mejoras-y-saas` (design.md D-3)

No es un descuido. `IN-04` se resolvio conservando `price_ars`, y `plan-gtm`
cotiza en USD 49/149/399 — una columna en pesos no puede guardarlos. La unica
cifra en pesos del corpus es la de `mejoras-y-saas`. A cualquier tipo de cambio
razonable USD 49 y ARS 45.000 no son el mismo precio: son dos propuestas
comerciales distintas, y el seed toma una de cada una a sabiendas.

`0 = ILIMITADO`, Y NO `NULL`
─────────────────────────────
Es la convencion de spec-tecnica 3.3 ("Limite de usuarios. 0 = ilimitado"), y
se conserva. Enterprise tiene `max_vehicles = 0`. El modo de fallar de esto es
silencioso —leer el 0 como "cero permitidos" y bloquear todo el plan mas caro—
y por eso `PlanLimitsService` tiene un test dedicado a ese caso.

EL SEED NO PISA LO QUE YA ESTA
───────────────────────────────
`ON CONFLICT (code) DO NOTHING`, no `DO UPDATE`. Si fuera `DO UPDATE`, cada
despliegue devolveria los precios a los de este archivo y borraria en silencio
cualquier ajuste comercial hecho sobre la base. Un seed que sobrescribe datos de
facturacion es una perdida de datos con permiso.

Revision ID: 005
Revises: 004
"""

from __future__ import annotations

import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLA = "plans"

# (code, name, price_ars, max_users, max_vehicles, max_branches, max_wa, modules)
PLANES: tuple[tuple[str, str, str, int, int, int, int, list[str]], ...] = (
    (
        "starter",
        "Starter",
        "45000.00",
        2,
        80,
        1,
        1500,
        ["stock", "crm", "whatsapp", "portal", "reports_basic"],
    ),
    (
        "pro",
        "Pro",
        "95000.00",
        5,
        300,
        2,
        5000,
        [
            "stock",
            "crm",
            "whatsapp",
            "portal",
            "reports_advanced",
            "trade_in",
            "finance",
            "pipeline_custom",
            "api_readonly",
        ],
    ),
    (
        "enterprise",
        "Enterprise",
        "195000.00",
        15,
        0,  # sin techo — ver el encabezado
        5,
        20000,
        [
            "stock",
            "crm",
            "whatsapp",
            "portal",
            "reports_advanced",
            "trade_in",
            "finance",
            "pipeline_custom",
            "api_full",
            "multi_branch",
            "sso",
            "accounting_integration",
        ],
    ),
)


def upgrade() -> None:
    op.create_table(
        TABLA,
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("code", sa.String(40), nullable=False, unique=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("price_ars", sa.Numeric(18, 2), nullable=False),
        sa.Column("max_users", sa.Integer(), nullable=False),
        sa.Column("max_vehicles", sa.Integer(), nullable=False),
        sa.Column("max_branches", sa.Integer(), nullable=False),
        # Columna que el modelo de datos no tenia: `plan-gtm` cuota los mensajes
        # de WhatsApp por mes y no habia donde ponerlo. Nace sin uso; la
        # consumen C-29 y C-30. Agregarla hoy cuesta una linea; agregarla en la
        # Ola 1.5 cuesta una migracion sobre datos de facturacion.
        sa.Column("max_whatsapp_messages_month", sa.Integer(), nullable=False),
        sa.Column("modules", sa.dialects.postgresql.JSONB(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # Los limites son cantidades: negativas no significan nada, y `0` ya
        # tiene el significado de "sin techo". Sin este CHECK, un -1 cargado a
        # mano deja el plan permitiendo todo sin que nada lo denuncie.
        sa.CheckConstraint("max_users >= 0", name="ck_plans_max_users_no_negativo"),
        sa.CheckConstraint("max_vehicles >= 0", name="ck_plans_max_vehicles_no_negativo"),
        sa.CheckConstraint("max_branches >= 0", name="ck_plans_max_branches_no_negativo"),
        sa.CheckConstraint("max_whatsapp_messages_month >= 0", name="ck_plans_max_wa_no_negativo"),
        sa.CheckConstraint("price_ars >= 0", name="ck_plans_price_no_negativo"),
    )

    _seed()


def _seed() -> None:
    """Carga los planes vigentes sin tocar los que ya existan.

    Se usa SQL parametrizado y no un f-string: los valores son constantes de
    este archivo, pero la regla dura 9 no admite excepciones "porque este caso
    es seguro" — la excepcion es lo que despues se copia a un caso que no lo es.
    """
    conexion = op.get_bind()
    # La sentencia va LITERAL, sin f-string. `TABLA` es una constante de este
    # archivo y interpolarla seria inofensivo hoy — pero la regla dura 9 no
    # admite excepciones "porque este caso es seguro": la excepcion es lo que
    # despues se copia a un caso que no lo es. Y `ruff` lo marca (S608), con
    # razon: un linter no puede saber que la constante nunca vendra de afuera.
    insercion = sa.text("""
        INSERT INTO plans (
            code, name, price_ars, max_users, max_vehicles,
            max_branches, max_whatsapp_messages_month, modules
        ) VALUES (
            :code, :name, :price_ars, :max_users, :max_vehicles,
            :max_branches, :max_wa, CAST(:modules AS jsonb)
        )
        ON CONFLICT (code) DO NOTHING
        """)
    for code, name, precio, usuarios, vehiculos, sucursales, wa, modulos in PLANES:
        conexion.execute(
            insercion,
            {
                "code": code,
                "name": name,
                "price_ars": precio,
                "max_users": usuarios,
                "max_vehicles": vehiculos,
                "max_branches": sucursales,
                "max_wa": wa,
                "modules": json.dumps(modulos),
            },
        )


def downgrade() -> None:
    op.drop_table(TABLA)
