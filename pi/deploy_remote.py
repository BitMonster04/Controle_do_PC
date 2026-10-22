"""Executar na LOCAL. Transfere token Pi->REMOTA via SSH, sem exibi-lo."""
import json
import base64
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
KEY=str(Path.home()/'.ssh/controle_jogos')
REMOTE='ggped@100.87.198.65'
SSH=['ssh','-i',KEY,'-o','BatchMode=yes','-o','ConnectTimeout=8']

def remote(script):
    encoded=base64.b64encode(script.encode('utf-8')).decode('ascii')
    line=("$ErrorActionPreference='Stop'; try { & ([ScriptBlock]::Create([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('"+encoded+"')))); Write-Output '__PC_OK__' } catch { Write-Output '__PC_FAILED__'; exit 1 }\n")
    r=subprocess.run(SSH+[REMOTE,'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -Command -'],input=line,text=True,capture_output=True)
    if r.returncode or '__PC_OK__' not in r.stdout:
        # Nao inclui script, token nem saida arbitraria nos erros.
        raise SystemExit('Falha ao executar preparacao na REMOTA. Nenhuma credencial foi exibida.')
    return r.stdout

def main():
    remote("$ErrorActionPreference='Stop'\nif ($env:COMPUTERNAME -ne 'DESKTOP-8J8LHLR') { exit 2 }\nif (!(Test-Path 'C:\\ProgramData\\BloqueioJogos\\controle.ps1')) { exit 3 }\nNew-Item -ItemType Directory -Force 'C:\\ProgramData\\BloqueioJogos\\PainelSetup' | Out-Null\nicacls.exe 'C:\\ProgramData\\BloqueioJogos\\PainelSetup' /inheritance:r /grant:r '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-18:(OI)(CI)F' | Out-Null\nif ($LASTEXITCODE -ne 0) { exit 4 }\n")
    for name in ['agente.ps1','instalar-pi.ps1']:
        subprocess.run(['scp','-i',KEY,'-o','BatchMode=yes','-o','ConnectTimeout=8',str(ROOT/'windows'/name),REMOTE+':C:/ProgramData/BloqueioJogos/PainelSetup/'+name],check=True)
    r=subprocess.run(SSH+['bit@aurora2d','sudo -n cat /root/controle-pc-credenciais.json'],capture_output=True,text=True,check=True)
    token=json.loads(r.stdout)['device_token']
    cfg=json.dumps(dict(serverUrl='https://aurora2d.tail8abf1e.ts.net:8443/controle-pc',deviceId='pc-jogos',deviceToken=token),separators=(',',':'))
    script=("$ErrorActionPreference='Stop'\ntry {\n"
            "$cfg = '"+cfg+"'\n"
            "$cfg | Set-Content -LiteralPath 'C:\\ProgramData\\BloqueioJogos\\PainelSetup\\agent-config.json' -Encoding UTF8\n"
            "& 'C:\\ProgramData\\BloqueioJogos\\PainelSetup\\instalar-pi.ps1'\n"
            "if (!(Test-Path 'C:\\ProgramData\\BloqueioJogos\\agente.ps1')) { exit 6 }\n"
            "$task=Get-ScheduledTask -TaskName 'ShockImports-ControleJogos' -ErrorAction Stop\n"
            "if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) { exit 4 }\n"
            "} catch { exit 5 }\n")
    # Somente stdin criptografado; segredo nao vai em argumentos de processo.
    remote(script)
    print('Agente instalado na REMOTA. Nenhuma ordem de bloquear/liberar foi enviada.')

if __name__=='__main__': main()
