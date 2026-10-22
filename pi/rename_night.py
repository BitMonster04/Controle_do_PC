"""Migra nomes da segunda trava, preservando logs, agenda e primeira trava."""
from pathlib import Path
import subprocess
from deploy_remote import remote,SSH,REMOTE
root=Path(__file__).resolve().parents[1]
stage='C:\\ProgramData\\NightNetworkControlSetup'
remote("New-Item -ItemType Directory -Force '"+stage+"' | Out-Null\nicacls.exe '"+stage+"' /inheritance:r /grant:r '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-18:(OI)(CI)F' | Out-Null\nif($LASTEXITCODE -ne 0){throw 'Permissoes'}\n")
names=['NightNetworkControl.cs','night-control.ps1','install-night-control.ps1','remove-night-control.ps1','README.md']
for name in names:
    subprocess.run(['scp','-i',SSH[2],'-o','BatchMode=yes',str(root/'windows/noturno'/name),REMOTE+':C:/ProgramData/NightNetworkControlSetup/'+name],check=True)
script=r'''
if($env:COMPUTERNAME -ne 'DESKTOP-8J8LHLR'){throw 'Destino incorreto'}
$old='C:\ProgramData\ControleNoturnoGiovanni'
$new='C:\ProgramData\NightNetworkControl'
$stage='C:\ProgramData\NightNetworkControlSetup'
if(!(Test-Path -LiteralPath $old) -or (Test-Path -LiteralPath $new)){throw 'Pastas nao correspondem ao estado esperado'}
$item=Get-Item -LiteralPath $old -Force
if($item.FullName -ne $old -or ($item.Attributes -band [IO.FileAttributes]::ReparsePoint)){throw 'Origem nao verificada'}
if([IO.Path]::GetFullPath($new) -ne $new -or [IO.Path]::GetDirectoryName($new) -ne 'C:\ProgramData'){throw 'Destino nao verificado'}
$oldNames=@('ControlePCGiovanni-LatenciaNoturna','ControlePCGiovanni-LatenciaNoturna-Encerrar06h')
& "$old\controle-noturno.ps1" parar
Start-Sleep -Seconds 2
if(Get-CimInstance Win32_Process -Filter "Name='LatenciaNoturna.exe'"){throw 'Processo antigo ainda em execucao'}
$driver=Get-CimInstance Win32_SystemDriver | Where-Object {$_.Name -eq 'WinDivert'}
if($driver -and $driver.PathName -notlike '*C:\ProgramData\ControleNoturnoGiovanni\WinDivert64.sys'){throw 'Driver nao pertence a esta instalacao'}
foreach($name in $oldNames){Disable-ScheduledTask -TaskName $name | Out-Null}
if($driver -and $driver.State -eq 'Running'){
    sc.exe stop WinDivert | Out-Null
    if($LASTEXITCODE -ne 0){throw 'Driver nao pode ser parado; manter a instalacao antiga para revisao'}
    for($n=0;$n -lt 20;$n++){$current=Get-CimInstance Win32_SystemDriver -Filter "Name='WinDivert'";if(!$current -or $current.State -eq 'Stopped'){break};Start-Sleep -Milliseconds 250}
    $current=Get-CimInstance Win32_SystemDriver -Filter "Name='WinDivert'"
    if($current -and $current.State -ne 'Stopped'){throw 'Driver nao encerrou'}
}
Move-Item -LiteralPath $old -Destination $new
if(Get-CimInstance Win32_SystemDriver -Filter "Name='WinDivert'"){
    sc.exe config WinDivert binPath= "\??\C:\ProgramData\NightNetworkControl\WinDivert64.sys" | Out-Null
    if($LASTEXITCODE -ne 0){throw 'Falha ao atualizar caminho do driver'}
}
Move-Item -LiteralPath "$new\instalacao-noturna.txt" -Destination "$new\installation.txt"
if(Test-Path "$new\noturno.log"){Move-Item -LiteralPath "$new\noturno.log" -Destination "$new\night-control.log"}
if(Test-Path "$new\noturno.log.1"){Move-Item -LiteralPath "$new\noturno.log.1" -Destination "$new\night-control.log.1"}
& "$stage\install-night-control.ps1"
Copy-Item "$stage\install-night-control.ps1" "$new\install-night-control.ps1" -Force
Copy-Item "$stage\README.md" "$new\README.md" -Force
if(!(Get-ScheduledTask -TaskName 'NightNetworkControl') -or !(Get-ScheduledTask -TaskName 'NightNetworkControl-StopAt0600')){throw 'Tarefas novas nao confirmadas'}
foreach($name in $oldNames){Unregister-ScheduledTask -TaskName $name -Confirm:$false}
foreach($name in @('LatenciaNoturna.exe','LatenciaNoturna.cs','controle-noturno.ps1','instalar-noturno.ps1','remover-noturno.ps1')){
    $file=Join-Path $new $name
    if(Test-Path -LiteralPath $file){Remove-Item -LiteralPath $file -Force}
}
foreach($name in @('NightNetworkControl.cs','night-control.ps1','install-night-control.ps1','remove-night-control.ps1','README.md')){Remove-Item -LiteralPath (Join-Path $stage $name) -Force}
Remove-Item -LiteralPath $stage -Force
Get-ScheduledTask -TaskName 'NightNetworkControl*' | Select-Object TaskName,State
Get-ScheduledTaskInfo -TaskName 'NightNetworkControl' | Select-Object NextRunTime,LastTaskResult
Get-Item $new -Force | Select-Object FullName,Attributes
'''
print(remote(script).replace('__PC_OK__','').strip())
