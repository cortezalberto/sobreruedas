"""catalogo de marcas y modelos de vehiculos, con su seed

Por que existe (C-13, `T-063` y `T-064`): el stock de una agencia referencia
marca y modelo, y esas tablas son catalogo COMPARTIDO. Van antes que
`vehicles`, que es C-14.

TABLAS COMPARTIDAS, SIN `tenant_id` Y SIN RLS
──────────────────────────────────────────────
`vehicle_brands` y `vehicle_models` son el mismo catalogo para todas las
agencias y no contienen dato de ninguna. `knowledge-base/04` las lista entre los
catalogos cross-tenant junto con `plans`, y ya figuraban en `EXENTAS_DE_RLS`
antes de que las tablas existieran. La exencion es estructural: no hay tenant al
que acotar una marca de auto.

⚠️ ESO NO LAS HACE ESCRIBIBLES. Que no tengan RLS significa que todos los
tenants las LEEN, no que puedan tocarlas. La escritura es del backoffice de
plataforma, y por ahora de nadie.

Y conseguir eso es REVOCAR, no otorgar: el init de la base tiene un
`ALTER DEFAULT PRIVILEGES ... GRANT SELECT, INSERT, UPDATE`, asi que toda tabla
nueva nace escribible. Ver `_revocar_escritura()`.

QUE TRAE EL SEED, Y QUE NO
───────────────────────────
`knowledge-base/04` §Seed data inicial pide **40 marcas, 300 modelos, 800
versiones**. Acá van las 40 marcas y una PRIMERA TANDA de modelos.

La diferencia no es pereza. Las marcas son dato verificable —o la terminal opera
en el pais o no—, pero un catalogo de 300 modelos con su `year_from` correcto es
**curaduria de datos de mercado**, no programacion: cada fila afirma en que año
entro un modelo al mercado argentino, y esas cifras hay que sacarlas de una
fuente, no de la memoria de quien escribe la migracion. Sembrar 300 filas
inventadas seria peor que sembrar 40 ciertas — el catalogo se usa para cargar
stock, y un `year_from` mal puesto rechaza vehiculos que existen.

Los modelos de acá son los de mayor volumen del mercado argentino, con años de
inicio de generacion conservadores. Completar hasta 300 queda como tarea de
datos, anotada en el change.

`vehicle_versions` y `trims` NO entran en esta migracion: son las otras dos
tablas de `T-063` y dependen de que los modelos esten curados.

Revision ID: 009
Revises: 008
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MARCAS_TABLA = "vehicle_brands"
MODELOS_TABLA = "vehicle_models"

# El enum ya lo declara `knowledge-base/04` linea 161. Se crea acá porque es la
# primera tabla que lo usa; `vehicles` (C-14) lo reutiliza.
TIPOS_DE_CARROCERIA = (
    "sedan",
    "hatchback",
    "suv",
    "pickup",
    "van",
    "coupe",
    "wagon",
    "other",
)

# (slug, nombre, pais de origen)
#
# Las 40 del seed. Criterio: terminales con operacion comercial en Argentina,
# sea por fabricacion local o importacion oficial. Incluye las de vehiculos
# comerciales pesados (Iveco, Scania), que una agencia multimarca tambien opera.
MARCAS: tuple[tuple[str, str, str], ...] = (
    ("toyota", "Toyota", "Japón"),
    ("volkswagen", "Volkswagen", "Alemania"),
    ("ford", "Ford", "Estados Unidos"),
    ("chevrolet", "Chevrolet", "Estados Unidos"),
    ("renault", "Renault", "Francia"),
    ("fiat", "Fiat", "Italia"),
    ("peugeot", "Peugeot", "Francia"),
    ("citroen", "Citroën", "Francia"),
    ("nissan", "Nissan", "Japón"),
    ("honda", "Honda", "Japón"),
    ("jeep", "Jeep", "Estados Unidos"),
    ("ram", "RAM", "Estados Unidos"),
    ("dodge", "Dodge", "Estados Unidos"),
    ("chrysler", "Chrysler", "Estados Unidos"),
    ("hyundai", "Hyundai", "Corea del Sur"),
    ("kia", "Kia", "Corea del Sur"),
    ("ssangyong", "SsangYong", "Corea del Sur"),
    ("mercedes-benz", "Mercedes-Benz", "Alemania"),
    ("bmw", "BMW", "Alemania"),
    ("audi", "Audi", "Alemania"),
    ("porsche", "Porsche", "Alemania"),
    ("mini", "MINI", "Reino Unido"),
    ("land-rover", "Land Rover", "Reino Unido"),
    ("jaguar", "Jaguar", "Reino Unido"),
    ("volvo", "Volvo", "Suecia"),
    ("alfa-romeo", "Alfa Romeo", "Italia"),
    ("ds", "DS Automobiles", "Francia"),
    ("lexus", "Lexus", "Japón"),
    ("suzuki", "Suzuki", "Japón"),
    ("mitsubishi", "Mitsubishi", "Japón"),
    ("subaru", "Subaru", "Japón"),
    ("isuzu", "Isuzu", "Japón"),
    ("chery", "Chery", "China"),
    ("baic", "BAIC", "China"),
    ("haval", "Haval", "China"),
    ("great-wall", "Great Wall", "China"),
    ("jac", "JAC", "China"),
    ("lifan", "Lifan", "China"),
    ("shineray", "Shineray", "China"),
    ("iveco", "Iveco", "Italia"),
)

# (slug de la marca, nombre del modelo, carroceria, año de inicio)
#
# Primera tanda: los de mayor volumen del mercado argentino. Los años son de
# inicio de generacion y estan puestos conservadores — ver el encabezado sobre
# por que no hay 300 filas acá.
MODELOS: tuple[tuple[str, str, str, int], ...] = (
    ("toyota", "Hilux", "pickup", 2016),
    ("toyota", "Corolla", "sedan", 2020),
    ("toyota", "Corolla Cross", "suv", 2021),
    ("toyota", "Yaris", "hatchback", 2018),
    ("toyota", "SW4", "suv", 2016),
    ("toyota", "Etios", "hatchback", 2013),
    ("volkswagen", "Amarok", "pickup", 2010),
    ("volkswagen", "Polo", "hatchback", 2018),
    ("volkswagen", "Virtus", "sedan", 2018),
    ("volkswagen", "T-Cross", "suv", 2019),
    ("volkswagen", "Nivus", "suv", 2020),
    ("volkswagen", "Taos", "suv", 2021),
    ("ford", "Ranger", "pickup", 2023),
    ("ford", "Territory", "suv", 2021),
    ("ford", "Bronco Sport", "suv", 2021),
    ("ford", "Maverick", "pickup", 2022),
    ("chevrolet", "S10", "pickup", 2012),
    ("chevrolet", "Tracker", "suv", 2020),
    ("chevrolet", "Onix", "hatchback", 2020),
    ("chevrolet", "Cruze", "sedan", 2017),
    ("chevrolet", "Spin", "van", 2013),
    ("renault", "Kangoo", "van", 2018),
    ("renault", "Duster", "suv", 2021),
    ("renault", "Sandero", "hatchback", 2015),
    ("renault", "Logan", "sedan", 2014),
    ("renault", "Alaskan", "pickup", 2017),
    ("fiat", "Cronos", "sedan", 2018),
    ("fiat", "Toro", "pickup", 2016),
    ("fiat", "Pulse", "suv", 2022),
    ("fiat", "Fastback", "suv", 2023),
    ("fiat", "Strada", "pickup", 2021),
    ("peugeot", "208", "hatchback", 2020),
    ("peugeot", "2008", "suv", 2020),
    ("peugeot", "3008", "suv", 2017),
    ("peugeot", "Partner", "van", 2019),
    ("citroen", "C3", "hatchback", 2022),
    ("citroen", "C3 Aircross", "suv", 2022),
    ("citroen", "Berlingo", "van", 2019),
    ("nissan", "Frontier", "pickup", 2018),
    ("nissan", "Kicks", "suv", 2016),
    ("nissan", "Versa", "sedan", 2020),
    ("honda", "HR-V", "suv", 2022),
    ("honda", "City", "sedan", 2022),
    ("jeep", "Renegade", "suv", 2015),
    ("jeep", "Compass", "suv", 2017),
    ("hyundai", "Tucson", "suv", 2021),
    ("hyundai", "Creta", "suv", 2021),
    ("kia", "Sportage", "suv", 2022),
    ("kia", "Seltos", "suv", 2020),
    ("chery", "Tiggo 2", "suv", 2019),
)


def upgrade() -> None:
    # ⚠️ EL ENUM SE CREA UNA VEZ Y SE REFERENCIA CON `create_type=False`.
    #
    # Con `sa.Enum(...)` a secas, SQLAlchemy emite el `CREATE TYPE` **de nuevo**
    # al ver la columna que lo usa, y la migracion muere con "type
    # body_type_enum already exists". El `checkfirst=True` del `create()` no
    # ayuda: el segundo intento no viene de esa llamada sino de `create_table`.
    sa.Enum(*TIPOS_DE_CARROCERIA, name="body_type_enum").create(op.get_bind(), checkfirst=True)
    carroceria = postgresql.ENUM(*TIPOS_DE_CARROCERIA, name="body_type_enum", create_type=False)

    op.create_table(
        MARCAS_TABLA,
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(80), nullable=False, unique=True),
        sa.Column("slug", sa.String(80), nullable=False, unique=True),
        sa.Column("origin_country", sa.String(80), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_table(
        MODELOS_TABLA,
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "brand_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey(f"{MARCAS_TABLA}.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("body_type", carroceria, nullable=False),
        sa.Column("year_from", sa.SmallInteger, nullable=False),
        # NULL = se sigue vendiendo. No es "dato faltante": es el estado normal
        # de un modelo vigente, y por eso la columna no tiene default.
        sa.Column("year_to", sa.SmallInteger, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("true")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        # `knowledge-base/04` linea 178. Dos marcas pueden tener un modelo con el
        # mismo nombre —"500" es de Fiat y podria serlo de otra—, asi que la
        # unicidad es por marca y no global.
        sa.UniqueConstraint("brand_id", "name", name="uq_vehicle_models_brand_name"),
    )

    # El listado de modelos de una marca es LA consulta de este catalogo: es lo
    # que pide el selector en cascada de C-13 en cada cambio de marca.
    op.create_index("ix_vehicle_models_brand_id", MODELOS_TABLA, ["brand_id"])

    _sembrar()
    _revocar_escritura()


def _sembrar() -> None:
    """Siembra marcas y modelos sin pisar lo que ya exista.

    `ON CONFLICT DO NOTHING` y no `DO UPDATE`, por el mismo motivo que el seed de
    `plans`: si fuera `DO UPDATE`, cada despliegue devolveria el catalogo al
    estado de este archivo y borraria en silencio cualquier correccion hecha
    sobre la base. Y este catalogo se va a corregir — ver el encabezado.
    """
    conexion = op.get_bind()

    conexion.execute(
        sa.text(
            "INSERT INTO vehicle_brands (name, slug, origin_country) "
            "VALUES (:name, :slug, :origin) ON CONFLICT (slug) DO NOTHING"
        ),
        [{"name": nombre, "slug": slug, "origin": pais} for slug, nombre, pais in MARCAS],
    )

    # El `brand_id` se resuelve por subconsulta contra el slug y no con un id
    # generado acá: si la marca ya existia, hay que colgar el modelo de ESA fila
    # y no de una nueva.
    conexion.execute(
        sa.text(
            "INSERT INTO vehicle_models (brand_id, name, body_type, year_from) "
            "SELECT b.id, :name, CAST(:body AS body_type_enum), :year_from "
            "FROM vehicle_brands b WHERE b.slug = :brand_slug "
            "ON CONFLICT (brand_id, name) DO NOTHING"
        ),
        [
            {"brand_slug": marca, "name": nombre, "body": carroceria, "year_from": desde}
            for marca, nombre, carroceria, desde in MODELOS
        ],
    )


def _revocar_escritura() -> None:
    """El catalogo se LEE y no se escribe. Hay que REVOCAR, no otorgar.

    ⚠️ La primera version de esta funcion hacia `GRANT SELECT`, y era al reves.
    El init de la base (`infra/local/postgres/init/02-rol-de-aplicacion.sh`)
    tiene un `ALTER DEFAULT PRIVILEGES ... GRANT SELECT, INSERT, UPDATE`, asi
    que **toda tabla nueva nace escribible por el rol de aplicacion**. Otorgar
    `SELECT` no agregaba nada y dejaba el `INSERT` y el `UPDATE` puestos.

    C-13 pide que estas tablas sean "legibles por todos los tenants y
    escribibles por ninguno". Eso no se consigue callando: se consigue
    revocando lo que el default ya dio.

    Es la contracara de la exencion de RLS. Que todos los tenants lean el
    catalogo no significa que alguno pueda cambiarlo: una agencia que renombra
    una marca se la renombra a TODAS. La escritura es del backoffice de
    plataforma, y hasta que exista no es de nadie.

    `DELETE` ya viene negado por el default —regla dura 3— y se revoca igual:
    depender de que otro archivo siga negandolo es la clase de garantia que se
    pierde en un cambio de configuracion.
    """
    conexion = op.get_bind()

    # Se consulta el catalogo y se revoca desde Python, en vez de un bloque
    # `DO $$` con SQL dinamico adentro: el mismo efecto, legible en el diff y
    # depurable si un dia revoca de mas.
    #
    # El rol de aplicacion NO se nombra. Se llama distinto en desarrollo
    # (`deruedas`) que en tests (`deruedas_test`), y hardcodearlo obligaria a
    # esta migracion a conocer el entorno donde corre — la misma razon por la
    # que el init de la base no usa `FOR ROLE`.
    beneficiarios = sa.text(
        "SELECT DISTINCT grantee FROM information_schema.role_table_grants "
        "WHERE table_name = :tabla "
        "  AND privilege_type IN ('INSERT', 'UPDATE', 'DELETE') "
        "  AND grantee <> current_user"
    )

    for tabla in (MARCAS_TABLA, MODELOS_TABLA):
        roles = conexion.execute(beneficiarios, {"tabla": tabla}).scalars().all()
        for rol in roles:
            # noqa S608: los identificadores NO se pueden bindear como parametros.
            # `tabla` es una constante de este modulo y `rol` sale del catalogo
            # del sistema, no de una entrada. Los VALORES de este archivo —los
            # del seed— si van bindeados, que es lo que pide la regla dura 9.
            conexion.execute(
                sa.text(f'REVOKE INSERT, UPDATE, DELETE ON {tabla} FROM "{rol}"')  # noqa: S608
            )


def downgrade() -> None:
    op.drop_index("ix_vehicle_models_brand_id", table_name=MODELOS_TABLA)
    op.drop_table(MODELOS_TABLA)
    op.drop_table(MARCAS_TABLA)
    sa.Enum(name="body_type_enum").drop(op.get_bind(), checkfirst=True)
