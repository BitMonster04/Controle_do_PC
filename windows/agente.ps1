# Agente fixo: so executa bloquear/desbloquear pelo script local existente.
$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$base = Join-Path $env:ProgramData 'BloqueioJogos'
$cfg = Get-Content (Join-Path $base 'agent-config.json') -Raw | ConvertFrom-Json
$controle = Join-Path $base 'controle.ps1'
$log = Join-Path $base 'agente.log'
$ack = $null
$erro = $null
function Write-Log([string]$Message) {
    if ((Test-Path $log) -and (Get-Item $log).Length -gt 1048576) {
        Move-Item -LiteralPath $log -Destination "$log.1" -Force
    }
    Add-Content -LiteralPath $log -Value "$(Get-Date -Format s) $Message"
}
function Get-Trava {
    $rules = @(Get-NetFirewallRule -PolicyStore ActiveStore -ErrorAction Stop |
        Where-Object { $_.Group -eq 'BloqueioJogosLocal' -and $_.Enabled -eq 'True' -and $_.Direction -eq 'Outbound' -and $_.Action -eq 'Block' })
    $profiles = @(Get-NetFirewallProfile -ErrorAction Stop | Where-Object { -not $_.Enabled })
    if ($rules.Count -gt 0 -and $profiles.Count -gt 0) {
        throw 'Existe perfil de firewall desativado. Verifique o Windows Firewall.'
    }
    return @{blocked=($rules.Count -gt 0); count=$rules.Count}
}
while ($true) {
    try {
        $estado = Get-Trava
        $body = @{
            p_device=$cfg.deviceId; p_token=$cfg.deviceToken
            p_blocked=$estado.blocked; p_rule_count=$estado.count
            p_ack=$ack; p_error=$erro
        } | ConvertTo-Json -Compress
        if ($cfg.serverUrl) {
            $reply = Invoke-RestMethod -Method Post -Uri "$($cfg.serverUrl)/api/heartbeat" `
                -ContentType 'application/json' -Body $body -TimeoutSec 20
        } else {
            $reply = Invoke-RestMethod -Method Post -Uri "$($cfg.supabaseUrl)/rest/v1/rpc/pc_heartbeat" `
                -Headers @{apikey=$cfg.publicKey} -ContentType 'application/json' -Body $body -TimeoutSec 20
        }
        $ack=$null; $erro=$null
        if ($reply.action -in @('bloquear','desbloquear')) {
            $ack=[long]$reply.revision
            try {
                if (!(Test-Path -LiteralPath $controle)) { throw 'controle.ps1 nao encontrado.' }
                $saida = & powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File $controle $reply.action 2>&1
                if ($LASTEXITCODE -ne 0 -or ($saida -join "`n") -match 'Falhas:\s*[1-9]') {
                    throw 'O script de bloqueio informou falhas. Verifique controle.ps1 na REMOTA.'
                }
                $novo=Get-Trava
                $esperado=$reply.action -eq 'bloquear'
                if ($novo.blocked -ne $esperado) { throw 'O firewall nao confirmou o estado solicitado; verifique se ha jogos identificados.' }
                Write-Log "Ordem $ack executada: $($reply.action). Regras: $($novo.count)."
            } catch {
                $erro=$_.Exception.Message
                Write-Log "Falha na ordem $ack : $erro"
            }
            # Envia a confirmacao imediatamente na proxima iteracao.
            continue
        }
    } catch {
        # Nenhuma ordem nova e executada sem resposta autenticada do servidor.
        Write-Log 'Sem comunicacao ou erro de leitura do firewall. Nova tentativa em 15 segundos.'
    }
    Start-Sleep -Seconds 15
}
