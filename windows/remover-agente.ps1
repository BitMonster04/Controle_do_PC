# Execute como administrador NA REMOTA. Nao muda a trava existente.
$ErrorActionPreference='Stop'
Stop-ScheduledTask -TaskName 'ShockImports-ControleJogos' -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName 'ShockImports-ControleJogos' -Confirm:$false -ErrorAction SilentlyContinue
$base=Join-Path $env:ProgramData 'BloqueioJogos'
foreach ($nome in @('agente.ps1','agent-config.json')) {
    Remove-Item -LiteralPath (Join-Path $base $nome) -Force -ErrorAction SilentlyContinue
}
Write-Host 'Agente removido. O estado da trava foi mantido.'
