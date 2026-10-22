"""Cria link de ativacao do celular, sem ler credenciais do agente Windows."""
from pathlib import Path
import subprocess

root=Path(__file__).resolve().parents[1]
key=Path.home()/'.ssh/controle_jogos'
command='sudo -n -u pccontrol env PC_DATA=/var/lib/controle-pc python3 /opt/controle-pc/pi/server.py --phone-link'
r=subprocess.run(['ssh','-i',str(key),'-o','BatchMode=yes','bit@aurora2d',command],capture_output=True,text=True,check=True)
link=r.stdout.strip()
if not link.startswith('https://aurora2d.tail8abf1e.ts.net:8443/controle-pc/#ativar='):
    raise SystemExit('Nao foi possivel gerar o link. Nenhuma credencial foi exibida.')
(root/'ATIVAR-CELULAR.txt').write_text(
    'CONTROLE PC GIOVANNI\n\nAbra o link abaixo NO CHROME DO CELULAR DA CHEFIA:\n\n'+link+
    '\n\nLink de uso unico, valido por 24 horas. Nao abra primeiro em outro aparelho.\n'
    'Depois da ativacao, toque em Instalar no celular. O acesso fica salvo por 30 dias.\n'
    'Somente um celular autorizado por vez; ativar outro substitui o anterior.\n'
    'Se limpar os dados do navegador ou trocar de aparelho, gere outro link.\n'
    'O agente da REMOTA ainda precisa ser instalado para controlar os jogos.\n',encoding='utf-8')
print('Link de ativacao salvo em ATIVAR-CELULAR.txt; segredo nao exibido.')
