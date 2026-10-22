"""Instala a trava noturna separada na REMOTA, sem ler credenciais do painel."""
from pathlib import Path
import subprocess
from deploy_remote import remote,SSH,REMOTE

root=Path(__file__).resolve().parents[1]
stage='C:\\ProgramData\\NightNetworkControlSetup'
remote("if ($env:COMPUTERNAME -ne 'DESKTOP-8J8LHLR') { throw 'Destino incorreto' }\nNew-Item -ItemType Directory -Force '"+stage+"' | Out-Null\nicacls.exe '"+stage+"' /inheritance:r /grant:r '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-18:(OI)(CI)F' | Out-Null\nif($LASTEXITCODE -ne 0) { throw 'Permissoes' }\n")
for name in ['NightNetworkControl.cs','night-control.ps1','install-night-control.ps1','remove-night-control.ps1']:
    subprocess.run(['scp','-i',SSH[2],'-o','BatchMode=yes',str(root/'windows/noturno'/name),REMOTE+':C:/ProgramData/NightNetworkControlSetup/'+name],check=True)
result=remote("& '"+stage+"\\install-night-control.ps1'\n")
print(result.replace('__PC_OK__','').strip())
