"""Cria identidades separadas; transfere somente as chaves PUBLICAS."""
import json
from pathlib import Path
import subprocess
from deploy_remote import remote

HOME=Path.home()
PRIMARY=HOME/'.ssh/controle_jogos'
LOCAL_KEY=HOME/'.ssh/controle_giovanni_reserva_local'
PI_KEY='/home/bit/.ssh/controle_giovanni_remota'
SSH=['ssh','-i',str(PRIMARY),'-o','BatchMode=yes','-o','ConnectTimeout=8']

def pi(command,stdin=None):
    r=subprocess.run(SSH+['bit@aurora2d',command],input=stdin,text=True,capture_output=True)
    if r.returncode:raise SystemExit('Falha ao preparar chaves no Pi. Nenhuma chave privada foi exibida.')
    return r.stdout.strip()

def main():
    if not LOCAL_KEY.exists():
        subprocess.run(['ssh-keygen','-q','-t','ed25519','-N','','-C','reserva-local-controle-giovanni','-f',str(LOCAL_KEY)],check=True)
    if not Path(str(LOCAL_KEY)+'.pub').exists():raise SystemExit('Par local incompleto; nao sobrescrever.')
    local_public=Path(str(LOCAL_KEY)+'.pub').read_text().strip()
    pi("umask 077; if test -e "+PI_KEY+"; then test -s "+PI_KEY+".pub; else ssh-keygen -q -t ed25519 -N '' -C codex-pi-controle-giovanni -f "+PI_KEY+"; fi; chmod 600 "+PI_KEY)
    pi_public=pi('cat '+PI_KEY+'.pub')
    for key in (local_public,pi_public):
        if not key.startswith('ssh-ed25519 ') or '\n' in key:raise SystemExit('Chave publica invalida.')
    # Cadastra reserva LOCAL -> Pi. Nao le ou transporta a privada gerada no Pi.
    script="""from pathlib import Path
p=Path('/home/bit/.ssh/authorized_keys')
key=KEY
text=p.read_text() if p.exists() else ''
if not any(line.split()[1:2]==key.split()[1:2] for line in text.splitlines()):
    p.write_text(text.rstrip()+'\\n'+key+'\\n')
p.chmod(0o600)
""".replace('KEY',repr(local_public))
    pi('python3 -',script)
    # Cadastra Pi -> REMOTA e reserva LOCAL -> REMOTA sem remover a chave atual.
    values=json.dumps([pi_public,local_public])
    ps="""$ErrorActionPreference='Stop'
if ($env:COMPUTERNAME -ne 'DESKTOP-8J8LHLR') { throw 'Destino incorreto.' }
$arquivo='C:\\ProgramData\\ssh\\administrators_authorized_keys'
$keys='PUBLIC_JSON' | ConvertFrom-Json
$lines=@(Get-Content -LiteralPath $arquivo)
foreach($key in $keys) {
  $part=$key.Split(' ')[1]
  if(!($lines | Where-Object { $_ -like "*$part*" })) {
    Add-Content -LiteralPath $arquivo -Value $key -Encoding ascii
    $lines+= $key
  }
}
icacls.exe $arquivo /inheritance:r /grant:r '*S-1-5-32-544:F' '*S-1-5-18:F' | Out-Null
if($LASTEXITCODE -ne 0) { throw 'Falha nas permissoes.' }
""".replace('PUBLIC_JSON',values)
    remote(ps)
    host_output=remote("Get-Content -LiteralPath 'C:\\ProgramData\\ssh\\ssh_host_ed25519_key.pub'\n")
    host_public=next((line.strip() for line in host_output.splitlines() if line.startswith('ssh-ed25519 ')),None)
    if not host_public:raise SystemExit('Nao foi possivel verificar a chave publica do servidor REMOTO.')
    entry='100.87.198.65 '+host_public
    script="""from pathlib import Path
p=Path('/home/bit/.ssh/known_hosts')
entry=ENTRY
text=p.read_text() if p.exists() else ''
if entry not in text.splitlines():p.write_text(text.rstrip()+'\\n'+entry+'\\n')
p.chmod(0o600)
""".replace('ENTRY',repr(entry))
    pi('python3 -',script)
    print('Chaves publicas cadastradas. As duas privadas permaneceram em seus computadores de origem.')
    print('LOCAL: '+str(LOCAL_KEY))
    print('Pi: '+PI_KEY)

if __name__=='__main__':main()
