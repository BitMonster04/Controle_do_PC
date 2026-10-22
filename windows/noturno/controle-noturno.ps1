param([ValidateSet('status','ativar','desativar','parar')][string]$Acao='status')
$ErrorActionPreference='Stop'
$base=Join-Path $env:ProgramData 'ControleNoturnoGiovanni'
$task='ControlePCGiovanni-LatenciaNoturna'
switch($Acao) {
    'ativar' {
        Remove-Item -LiteralPath "$base\desativado.flag" -Force -ErrorAction SilentlyContinue
        Start-ScheduledTask -TaskName $task
        Write-Host 'Agenda ativada: 22h ate 6h. Fora desse horario nao aplica atraso.'
    }
    'desativar' {
        Set-Content -LiteralPath "$base\desativado.flag" -Value 'Desativado pelo administrador'
        Set-Content -LiteralPath "$base\parar.flag" -Value 'Parar e liberar fila'
        Write-Host 'Trava noturna desativada. O processo libera a fila e encerra.'
    }
    'parar' { Set-Content -LiteralPath "$base\parar.flag" -Value 'Encerramento das 6h' }
    'status' {
        [pscustomobject]@{Pasta=$base;AgendaAtivada=!(Test-Path "$base\desativado.flag");HorarioLocal=(Get-Date);Janela='22:00-06:00'}
        Get-ScheduledTask -TaskName $task,"$task-Encerrar06h" | Select-Object TaskName,State
        Get-Content "$base\noturno.log" -Tail 5 -ErrorAction SilentlyContinue
    }
}
