# ─────────────────────────────────────────────────────────────────────────────
# deRuedas Gestion — atajos de desarrollo
#
# `make migrate` y `make migrate-down-one` los exige T-007 explicitamente.
#
# NOTA SOBRE LA SECCION 4.1: el arbol vinculante del plan NO incluye un
# Makefile. No es un desvio elegido: el propio T-007 (mismo documento, N2)
# manda estos comandos. Es una inconsistencia interna del plan, no una decision
# nuestra, y por eso no lleva ADR — a diferencia de infra/local/, que si era una
# eleccion entre alternativas y quedo en ADR-019.
#
# Todo corre DENTRO del contenedor: la version de Python es 3.12 (ADR-003) y no
# la que cada quien tenga instalada en su maquina.
# ─────────────────────────────────────────────────────────────────────────────

COMPOSE := docker compose
BACKEND := $(COMPOSE) run --rm --no-deps backend

# `.env` es el archivo de overrides de ESTA maquina, y `docker compose` lo lee
# solo, pero para sustituir dentro del compose — no lo pone en el entorno de
# make. `make seed` necesita `FRONTEND_PORT` para decirle a Keycloak a que
# origen redirigir despues del login, asi que se lee aca tambien.
#
# `-include`: si no existe, no pasa nada. Los defaults viven abajo.
-include .env
FRONTEND_PORT ?= 3000

.DEFAULT_GOAL := help
.PHONY: help up seed down logs rebuild migrate migrate-down-one migration test test-integration coverage test-tools lint format check

help:  ## Muestra esta ayuda
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sed 's/:.*## /  ->  /'

# ── Entorno ──────────────────────────────────────────────────────────────────
up:  ## Levanta el entorno local completo
	$(COMPOSE) up -d --wait

seed:  ## Siembra la agencia demo y los tres usuarios de Keycloak
# `MSYS_NO_PATHCONV=1`: en Git Bash sobre Windows, MSYS reescribe los
# argumentos que parecen rutas absolutas, y `/seed/sembrar_dev.py` llega al
# contenedor como `C:/Program Files/Git/seed/...`. En Linux la variable no
# existe y no molesta.
	@$(COMPOSE) exec -T postgres psql -U $${POSTGRES_USER:-deruedas} -d $${POSTGRES_DB:-deruedas} -f - < infra/local/agencia-demo.sql
	@MSYS_NO_PATHCONV=1 $(COMPOSE) run --rm --no-deps -T -e KEYCLOAK_ADMIN_URL=http://keycloak:8080 -e FRONTEND_PORT=$(FRONTEND_PORT) -v "$(CURDIR)/infra/local:/seed:ro" backend python /seed/sembrar_dev.py

down:  ## Apaga el entorno CONSERVANDO los datos
	$(COMPOSE) down

logs:  ## Sigue los logs del backend
	$(COMPOSE) logs -f backend

# ── Migraciones (T-007) ──────────────────────────────────────────────────────
migrate:  ## Aplica todas las migraciones pendientes
	$(COMPOSE) run --rm backend alembic upgrade head

migrate-down-one:  ## Revierte la ultima migracion
	$(COMPOSE) run --rm backend alembic downgrade -1

# El rev id se calcula correlativo: alembic.ini usa file_template
# %(rev)s_%(slug)s, asi que el archivo sale NNN_descripcion.py como pide T-007.
# Sin --rev-id, alembic genera un hash y el orden deja de leerse del `ls`.
migration:  ## Crea una migracion nueva:  make migration name=agrega_vehiculos
	@test -n "$(name)" || (echo "Falta el nombre:  make migration name=agrega_vehiculos" && exit 1)
	@next=$$(ls backend/alembic/versions/[0-9]*_*.py 2>/dev/null | sed 's|.*/||; s|_.*||' | sort -n | tail -1); 	next=$$(printf '%03d' $$((10#$${next:-0} + 1))); 	echo "Nueva revision: $$next"; 	$(COMPOSE) run --rm backend alembic revision --rev-id $$next -m "$(name)"

# ── Calidad ──────────────────────────────────────────────────────────────────
test:  ## Tests unitarios con cobertura
	$(BACKEND) pytest tests/unit --cov=app

test-integration:  ## Tests contra servicios reales
	$(COMPOSE) run --rm backend pytest tests/integration -m integration

# El mismo gate que corre el pipeline, para no enterarse recien en el PR.
# `fail_under` de coverage.py NO alcanza: mezcla lineas y ramas en un numero
# solo y ADR-014 las exige por separado. Ver tools/check-coverage.py.
#
# Corre la suite COMPLETA, no solo los unitarios, y por eso necesita los
# servicios arriba (sin `--no-deps`). Medir excluyendo los tests de integracion
# subestima justo lo que mas importa: `db/session.py` da 63 % solo-unitarios y
# 95 % con la suite entera, porque el aislamiento multi-tenant se prueba contra
# PostgreSQL de verdad. Es la misma medicion que hace el CI.
coverage:  ## Cobertura con el gate de ADR-014: 80 % lineas Y 60 % ramas
	$(COMPOSE) run --rm backend pytest --cov=app --cov-report=json:coverage.json
	@$(PYTEST_HOST) tools/check-coverage.py --coverage-json backend/coverage.json

# Estos tests son la excepcion a la regla del encabezado: NO corren en el
# contenedor. Crean repositorios git de verdad y la imagen del backend no trae
# git — agregarselo seria engordar una imagen de produccion para correr tests.
#
# Corren en el host, y ahi `python` a secas no alcanza: en Windows suele
# resolver a la instalacion del sistema, que no tiene pytest, y entonces
# `make check` corta con "No module named pytest" — un mensaje que no le dice a
# nadie que el interprete de al lado si lo tiene. El launcher `py -3` elige el
# Python 3 mas nuevo, que es donde suelen estar las herramientas.
#
# Se resuelve con condicionales de Make y no con logica de shell a proposito:
# en Windows este Makefile lo ejecuta cmd.exe, no sh, y un `for ... do` ahi
# falla con "No se esperaba c en este momento".
#
# Si en tu maquina el que tiene pytest es otro:
#     make test-tools PYTEST_HOST="py -3.12"
ifeq ($(OS),Windows_NT)
PYTEST_HOST ?= py -3
else
PYTEST_HOST ?= python3
endif

test-tools:  ## Tests de los verificadores de tools/ (corren en el host)
	@$(PYTEST_HOST) -m pytest tools/tests -q

# ⚠️ Si `make lint` da verde y el CI da rojo, sospecha de la imagen: se
# construye una vez y NO se entera de que pyproject.toml cambio sus pisos de
# version. Paso el 16-ago-2026 — la imagen tenia black 24.10.0 mientras
# pyproject exigia >=26.3.1, asi que el lint local corria una version que ni
# siquiera cumplia la restriccion del proyecto (y con las vulnerabilidades
# PYSEC que ese piso existe para evitar). El CI instala siempre desde cero.
#
#     make rebuild
lint:  ## ruff + black --check + mypy --strict
	$(BACKEND) sh -c "ruff check app tests alembic && black --check app tests alembic && mypy app"

rebuild:  ## Reconstruye la imagen del backend tras tocar pyproject.toml
	$(COMPOSE) build backend

format:  ## Aplica black y arregla lo que ruff pueda
	$(BACKEND) sh -c "ruff check --fix app tests alembic && black app tests alembic"

check: lint test-tools coverage  ## Todo lo que el pipeline va a exigir
	@python tools/check-md-links.py
	@python tools/check-config-parity.py
