# ─────────────────────────────────────────────────────────────────────────────
# Backend — FastAPI sobre Python 3.12 (ADR-003)
#
# Imagen compartida por los servicios `backend` y `worker`: mismo codigo, distinto
# comando de arranque. El worker de Celery no necesita una imagen propia.
#
# En desarrollo el codigo NO se usa desde la imagen: docker-compose.yml monta
# ./backend sobre /app y uvicorn recarga en caliente. Lo que la imagen aporta en
# local son las dependencias del sistema y las de Python ya instaladas.
#
# ⚠️ Requiere backend/pyproject.toml, que crea T-005 (bloque 5 de C-01).
#    Hasta entonces este build falla, y falla bien: dice exactamente que falta.
# ─────────────────────────────────────────────────────────────────────────────

FROM python:3.12-slim AS base

# PYTHONUNBUFFERED: los logs salen al instante y no cuando se llena el buffer.
#   Sin esto, en un contenedor que se cae no ves las ultimas lineas — justo las
#   que necesitas.
# PYTHONDONTWRITEBYTECODE: los .pyc en un volumen montado ensucian el arbol del
#   host y provocan cache invalida cuando el codigo cambia por fuera.
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# libpq5    -> cliente de PostgreSQL en runtime
# curl      -> healthcheck del compose
# build-essential y libpq-dev -> compilar ruedas que no traen binario
RUN apt-get update \
 && apt-get install --no-install-recommends -y \
      libpq5 \
      curl \
      build-essential \
      libpq-dev \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar SOLO el manifiesto antes que el codigo: mientras las dependencias no
# cambien, Docker reutiliza esta capa y no reinstala nada en cada edicion.
COPY pyproject.toml ./
RUN pip install --editable ".[dev]"

# El codigo se copia para que la imagen sirva tambien en CI y en staging, donde
# no hay volume mount. En local queda tapado por el montaje del compose.
COPY . .

# Usuario sin privilegios: un proceso comprometido no debe ser root en el
# contenedor. Va despues del install, que si necesita escribir en site-packages.
RUN useradd --create-home --uid 1000 deruedas \
 && chown -R deruedas:deruedas /app
USER deruedas

EXPOSE 8000

# Default de desarrollo. En staging y produccion el comando lo fija el
# Deployment de Kubernetes, sin --reload y con varios workers (ADR-015).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
