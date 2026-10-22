$ErrorActionPreference='Stop'
$base=Join-Path $env:ProgramData 'NightNetworkControl'
& "$base\night-control.ps1" desativar
Start-Sleep -Seconds 3
foreach($name in @('NightNetworkControl','NightNetworkControl-StopAt0600')) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
}
Write-Host 'Agenda removida e atraso desativado. Arquivos mantidos para auditoria; trava principal preservada.'
