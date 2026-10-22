$ErrorActionPreference='Stop'
$base=Join-Path $env:ProgramData 'ControleNoturnoGiovanni'
& "$base\controle-noturno.ps1" desativar
Start-Sleep -Seconds 3
foreach($name in @('ControlePCGiovanni-LatenciaNoturna','ControlePCGiovanni-LatenciaNoturna-Encerrar06h')) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
}
Write-Host 'Agenda removida e atraso desativado. Arquivos mantidos para auditoria; trava principal preservada.'
