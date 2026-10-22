#!/bin/bash
set -euo pipefail
test "$(id -u)" = 0 || { echo 'Execute com sudo.'; exit 1; }
src="$(cd "$(dirname "$0")/.." && pwd)"
dest=/opt/controle-pc
nginx=/etc/nginx/conf.d/shock-dicionario.conf
test -f "$nginx"
if ss -ltnH 'sport = :8795' | grep -q . && ! systemctl is-active --quiet controle-pc; then
  echo 'Porta 8795 em uso por outro aplicativo.'; exit 1
fi
id pccontrol >/dev/null 2>&1 || useradd --system --home-dir /var/lib/controle-pc --shell /usr/sbin/nologin pccontrol
install -d -m 755 "$dest" "$dest/pi"
install -d -o pccontrol -g pccontrol -m 700 /var/lib/controle-pc
for f in index.html style.css app.js; do install -m 644 "$src/$f" "$dest/$f"; done
for f in server.py config.js api.js; do install -m 644 "$src/pi/$f" "$dest/pi/$f"; done
if ! test -f /var/lib/controle-pc/state.sqlite3; then
  umask 077
  PC_DATA=/var/lib/controle-pc python3 "$dest/pi/server.py" --init > /root/controle-pc-credenciais.json
  chown pccontrol:pccontrol /var/lib/controle-pc/state.sqlite3
fi
cat > /etc/systemd/system/controle-pc.service <<'UNIT'
[Unit]
Description=Painel de controle de jogos Shock Imports
After=network.target

[Service]
Type=simple
User=pccontrol
Group=pccontrol
WorkingDirectory=/opt/controle-pc
Environment=PC_DATA=/var/lib/controle-pc
Environment=PC_ORIGIN=https://aurora2d.tail8abf1e.ts.net:8443
ExecStart=/usr/bin/python3 /opt/controle-pc/pi/server.py --port 8795
Restart=on-failure
RestartSec=5
UMask=0077
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/controle-pc
CapabilityBoundingSet=
RestrictAddressFamilies=AF_INET AF_UNIX

[Install]
WantedBy=multi-user.target
UNIT
cat > /etc/nginx/snippets/controle-pc.conf <<'NGINX'
location = /controle-pc { return 302 /controle-pc/; }
location ^~ /controle-pc/ {
    client_max_body_size 8k;
    limit_req zone=shock_api burst=20 nodelay;
    proxy_pass http://127.0.0.1:8795;
    proxy_set_header Host aurora2d.tail8abf1e.ts.net:8443;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-Proto https;
    proxy_connect_timeout 5s;
    proxy_read_timeout 30s;
}
NGINX
backup="$nginx.controle-pc-$(date +%Y%m%d-%H%M%S).bak"
cp -a "$nginx" "$backup"
python3 - "$nginx" <<'PY'
from pathlib import Path
import sys
p=Path(sys.argv[1]); text=p.read_text()
line='    include /etc/nginx/snippets/controle-pc.conf;\n'
if line not in text:
    marker='    location / {'
    if text.count(marker)!=1: raise SystemExit('Bloco Nginx ambiguo; configuracao preservada.')
    p.write_text(text.replace(marker,line+marker,1))
PY
if ! nginx -t; then cp -a "$backup" "$nginx"; exit 1; fi
systemctl daemon-reload
systemctl enable --now controle-pc
systemctl restart controle-pc
systemctl reload nginx
systemctl is-active controle-pc
echo 'Painel: https://aurora2d.tail8abf1e.ts.net:8443/controle-pc/'
echo 'Credenciais iniciais guardadas somente em /root/controle-pc-credenciais.json.'
