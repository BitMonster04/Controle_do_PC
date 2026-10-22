# Execute como administrador NA REMOTA. agente.ps1 e agent-config.json devem
# estar ao lado deste instalador. O arquivo de configuracao e privado.
$ErrorActionPreference='Stop'
$admin=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (!$admin) { throw 'Abra o PowerShell como administrador NA REMOTA.' }
$base=Join-Path $env:ProgramData 'BloqueioJogos'
if (!(Test-Path "$base\controle.ps1")) { throw 'controle.ps1 nao encontrado. Confirme que esta na REMOTA.' }
$src=Join-Path $PSScriptRoot 'agent-config.json'
$cfg=Get-Content -LiteralPath $src -Raw | ConvertFrom-Json
if ($cfg.serverUrl -ne 'https://aurora2d.tail8abf1e.ts.net:8443/controle-pc' -or $cfg.deviceToken -notmatch '^[a-f0-9]{64}$') { throw 'Configuracao invalida.' }
icacls.exe $base /inheritance:r /grant:r '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-18:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Falha ao proteger pasta.' }
Stop-ScheduledTask -TaskName 'ShockImports-ControleJogos' -ErrorAction SilentlyContinue
Copy-Item "$PSScriptRoot\agente.ps1" "$base\agente.ps1" -Force
Copy-Item $src "$base\agent-config.json" -Force
foreach ($item in @("$base\agent-config.json","$base\agente.ps1","$base\controle.ps1")) {
    icacls.exe $item /reset | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Falha ao proteger $item" }
}
$action=New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$base\agente.ps1`""
$trigger=New-ScheduledTaskTrigger -AtStartup
$principal=New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'ShockImports-ControleJogos' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName 'ShockImports-ControleJogos'
Remove-Item -LiteralPath $src -Force
Write-Host 'Agente conectado ao Pi. Aguarde ate 1 minuto para aparecer online.'
