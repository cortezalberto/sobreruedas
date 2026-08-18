# Despliegue sobre el VPS

Todo lo de este directorio implementa el **bloque 9 de `C-01`** bajo [`ADR-023`](../../docs/adr/ADR-023-despliegue-sobre-vps-con-docker-compose.md) (VPS único con Docker Compose) y [`ADR-025`](../../docs/adr/ADR-025-topologia-de-produccion-y-migraciones-compatibles.md) (topología, Caddy, migraciones compatibles).

> ⚠️ **`infra/k8s/` e `infra/terraform/` no existen y no se crean.** `ADR-023` §Notas de implementación.

---

## La idea en una pantalla

```
GitHub Actions                          VPS (Hostinger)
──────────────                          ───────────────
  CI verde
     │
     ▼                                   deruedas-datos  ← uno solo, permanente
  construir                              ├── postgres  (+ base de Keycloak)
  firmar (cosign)                        ├── redis
  publicar en GHCR                       ├── minio
     │                                   ├── opensearch
     │  ── el pipeline TERMINA acá ──    └── keycloak
     │
     │                                   deruedas-azul  ─┐  uno sirve,
     ▼                                   deruedas-verde ─┘  el otro espera
  ghcr.io/…/backend:<sha>  ◄─── sondea ── agente (timer, cada 2 min)
                                              │
                                              ▼
                                          Caddy ──► el color activo
```

**El VPS tira; el pipeline no empuja.** GitHub Actions nunca recibe acceso SSH: su permiso máximo es publicar una imagen y escribir un tag. Es el control que `ADR-015` defendió y `ADR-023` conservó, y lo hace cumplir un test ([`test_pipeline_sin_credenciales.py`](../../backend/tests/unit/test_pipeline_sin_credenciales.py)).

## Qué hay acá

| Ruta | Qué es |
|---|---|
| `caddy/Caddyfile.tmpl` | Plantilla del proxy. `__COLOR__` lo reemplaza la conmutación. |
| `deploy/desplegar.sh` | El agente. Detecta, verifica firma, migra, levanta, humea, conmuta. |
| `deploy/conmutar-upstream.sh` | Mueve el upstream de Caddy. Hace una sola cosa, a propósito. |
| `deploy/humo.sh` | Pruebas de humo, 5 minutos, contra el stack que aún no recibe tráfico. |
| `deploy/notificar.sh` | Telegram. Independiente del SMTP de la aplicación. |
| `deploy/*.service` `*.timer` | Unidades de systemd. |
| `postgres/init/10-keycloak.sql` | Base y rol propios de Keycloak. |
| `../../docker-compose.prod.yml` | El override. La base sigue siendo `docker-compose.yml`. |

---

# Runbooks

## 1 · Provisionar el VPS — tarea 9.1

```bash
# Actualizaciones de seguridad desatendidas
sudo apt update && sudo apt install -y unattended-upgrades chrony
sudo dpkg-reconfigure -plow unattended-upgrades

# Reloj sincronizado — los tokens OIDC tienen ventana de validez, y un reloj
# corrido produce fallos de autenticacion que parecen cualquier otra cosa.
sudo systemctl enable --now chrony
timedatectl status | grep -i synchronized
```

## 2 · Endurecer el servidor — tarea 9.2

```bash
# Usuario de despliegue, sin privilegios fuera de Docker
sudo adduser --disabled-password --gecos "" deploy
sudo usermod -aG docker deploy

# SSH solo por clave, sin root
sudo install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
# …copiar tu clave publica a /home/deploy/.ssh/authorized_keys…
sudo sed -i 's/^#*PermitRootLogin.*/PermitRootLogin no/'            /etc/ssh/sshd_config
sudo sed -i 's/^#*PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo systemctl restart ssh

# Firewall: solo 22, 80 y 443
sudo ufw default deny incoming && sudo ufw default allow outgoing
sudo ufw allow 22/tcp && sudo ufw allow 80/tcp && sudo ufw allow 443/tcp
sudo ufw --force enable
```

> **Verificá antes de cerrar la sesión.** Abrí una segunda terminal y confirmá que entrás. Si `PermitRootLogin no` te dejó afuera y no tenés otra sesión, hace falta la consola web del proveedor.

## 3 · Docker, red y directorios — tarea 9.3

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo mkdir -p /etc/deruedas /opt/deruedas
sudo chown -R deploy:deploy /opt/deruedas

sudo -u deploy git clone https://github.com/cortezalberto/sobreruedas.git /opt/deruedas

# Las redes son EXTERNAS: las comparten los tres proyectos de Compose. Sin esto
# los stacks de aplicacion no alcanzan a la base.
docker network create deruedas_prod_default
docker network create deruedas_prod_observability

sudo install -m 0755 /opt/deruedas/infra/vps/deploy/*.sh /opt/deruedas/infra/vps/deploy/
sudo cp /opt/deruedas/infra/vps/deploy/deruedas-desplegar.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload
```

## 4 · Claves `age` y secretos con SOPS — tareas 9.5 y 9.6

```bash
# EN EL VPS. La clave privada vive acá y NO se versiona nunca (regla dura 4).
age-keygen -o /etc/deruedas/age.key
sudo chmod 600 /etc/deruedas/age.key
grep 'public key' /etc/deruedas/age.key    # ← esta va al .sops.yaml del repo
```

En tu máquina, con esa clave pública en `.sops.yaml`:

```bash
sops --encrypt --age <clave_publica> produccion.env > infra/vps/secretos/produccion.env.sops
```

Y en el VPS, para materializar el archivo que lee Compose:

```bash
SOPS_AGE_KEY_FILE=/etc/deruedas/age.key \
  sops --decrypt /opt/deruedas/infra/vps/secretos/produccion.env.sops \
  | sudo tee /etc/deruedas/produccion.env > /dev/null
sudo chmod 600 /etc/deruedas/produccion.env
```

> **Tarea 9.7 — el gate tiene que seguir mordiendo.** Después de versionar los archivos cifrados, plantá un secreto **en claro** al lado y confirmá que `gitleaks` lo detecta. Un gate que se apaga para no molestar deja de ser un gate.

## 5 · Primer arranque

```bash
cd /opt/deruedas
export HOST_BIND_ADDR=127.0.0.1:

# Stack de datos. Los init de PostgreSQL —extensiones, rol de aplicacion
# (ADR-020) y base de Keycloak (ADR-025)— corren UNA sola vez, al crear el
# volumen.
docker compose -p deruedas-datos \
  -f docker-compose.yml -f docker-compose.prod.yml \
  --env-file /etc/deruedas/produccion.env \
  up -d --wait postgres redis minio opensearch keycloak

# Proxy, arrancando en azul
sed 's/__COLOR__/azul/g' infra/vps/caddy/Caddyfile.tmpl | sudo tee /etc/caddy/Caddyfile
echo azul | sudo tee /etc/deruedas/color-activo

# Agente
sudo systemctl enable --now deruedas-desplegar.timer
systemctl list-timers deruedas-desplegar.timer
```

## 6 · Backup y restauración — tareas 9.21 y 9.22

**El destino tiene que estar fuera de Hostinger, no solo fuera del VPS.** Un incidente a nivel proveedor se lleva la máquina y el backup juntos, que es justamente el escenario que el backup existe para cubrir. `ADR-025` eligió **Backblaze B2**, que es S3-compatible.

```ini
# /etc/pgbackrest/pgbackrest.conf
[global]
repo1-type=s3
repo1-s3-endpoint=s3.us-west-004.backblazeb2.com
repo1-s3-bucket=deruedas-backups
repo1-retention-full=4
repo1-cipher-type=aes-256-cbc

[deruedas]
pg1-path=/var/lib/postgresql/data
```

```bash
pgbackrest --stanza=deruedas stanza-create
pgbackrest --stanza=deruedas --type=full backup
```

> **La tarea 9.22 no es escribir el procedimiento: es ejecutarlo y fecharlo.** Sin una restauración probada, el RPO de 5 minutos del plan de SRE es una intención, no una garantía. Restaurá sobre una máquina descartable, verificá que los datos están, y anotá la fecha.

---

## Operación cotidiana

```bash
# Que color esta sirviendo
/opt/deruedas/infra/vps/deploy/conmutar-upstream.sh --actual

# Volver al stack anterior (si todavia esta levantado)
/opt/deruedas/infra/vps/deploy/conmutar-upstream.sh verde

# Que hizo el agente
journalctl -u deruedas-desplegar -n 100 -f

# Forzar un despliegue sin esperar al timer
sudo systemctl start deruedas-desplegar.service
```

## Lo que este despliegue NO da — asumido, no olvidado

- **Punto único de fallo.** Sin redundancia de ninguna clase. El conflicto con los SLA publicados está escalado a Dirección + SRE en [`ESC-001`](../../docs/escalaciones/ESC-001-sla-sobre-nodo-unico.md).
- **La deriva es silenciosa.** ArgoCD reportaba divergencia entre el estado declarado y el real; un cambio hecho a mano sobre el VPS no lo denuncia nadie.
- **La reversión de la base no es gratis.** Por eso existe la regla dura 13 y sus dos gates: sin migraciones compatibles hacia atrás, el stack viejo deja de ser una red de seguridad.
