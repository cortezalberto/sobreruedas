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

.DEFAULT_GOAL := help
.PHONY: help up down logs migrate migrate-down-one migration test test-integration lint format check

help:  ## Muestra esta ayuda
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sed 's/:.*## /  ->  /'

# ── Entorno ──────────────────────────────────────────────────────────────────
up:  ## Levanta el entorno local completo
	$(COMPOSE) up -d --wait

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

lint:  ## ruff + black --check + mypy --strict
	$(BACKEND) sh -c "ruff check app tests alembic && black --check app tests alembic && mypy app"

format:  ## Aplica black y arregla lo que ruff pueda
	$(BACKEND) sh -c "ruff check --fix app tests alembic && black app tests alembic"

check: lint test  ## Todo lo que el pipeline va a exigir
	@python tools/check-md-links.py
	@python tools/check-config-parity.py
