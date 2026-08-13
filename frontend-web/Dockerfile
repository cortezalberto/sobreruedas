# ─────────────────────────────────────────────────────────────────────────────
# Frontend web — Next.js 14+ con App Router (ADR-004)
#
# Imagen de DESARROLLO: sirve `next dev` con hot reload contra el codigo montado.
# La imagen de produccion es otra cosa —build standalone, multi-stage, sin
# devDependencies— y la define C-07 junto con el design system.
#
# ⚠️ Requiere frontend-web/package.json, que crea T-006 (bloque 7 de C-01).
#    Hasta entonces este build falla, y falla bien: dice exactamente que falta.
# ─────────────────────────────────────────────────────────────────────────────

FROM node:20-slim

ENV NODE_ENV=development \
    NEXT_TELEMETRY_DISABLED=1

# curl para el healthcheck del compose.
RUN apt-get update \
 && apt-get install --no-install-recommends -y curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Manifiestos antes que el codigo: mientras las dependencias no cambien, Docker
# reutiliza la capa del npm ci y no reinstala en cada edicion de un componente.
# El comodin en package-lock.json lo hace opcional — todavia no existe.
COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# La imagen de node ya trae el usuario `node` (uid 1000), sin privilegios.
RUN chown -R node:node /app
USER node

EXPOSE 3000

CMD ["npm", "run", "dev"]
