"""Executar na LOCAL: salva acesso inicial em arquivo privado fora do Git."""
import json
from pathlib import Path
import subprocess

key=Path.home()/'.ssh/controle_jogos'
r=subprocess.run(['ssh','-i',str(key),'-o','BatchMode=yes','bit@aurora2d',
                  'sudo -n cat /root/controle-pc-credenciais.json'],capture_output=True,check=True,text=True)
data=json.loads(r.stdout)
out=Path(__file__).resolve().parents[1]/'PAINEL-ACESSO.txt'
out.write_text('PAINEL DE CONTROLE DOS JOGOS\n\n'
               'Link: https://aurora2d.tail8abf1e.ts.net:8443/controle-pc/\n\n'
               'Senha do painel: '+data['panel_password']+'\n\n'
               'Essa senha pertence somente ao painel. Nao e senha Windows nem SSH.\n'
               'Clique no botao central para entrar. Vermelho = trava ativada; verde = trava desativada.\n'
               'O controle real depende do agente instalado na REMOTA.\n',encoding='utf-8')
print('Arquivo de acesso salvo; nenhuma credencial foi exibida.')
