# Execute NA REMOTA, com PowerShell como administrador, junto de agente.ps1.
$ErrorActionPreference='Stop'
$admin=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (!$admin) { throw 'Abra o PowerShell como administrador NA REMOTA.' }
$base=Join-Path $env:ProgramData 'BloqueioJogos'
if (!(Test-Path "$base\controle.ps1")) { throw 'O script controle.ps1 nao existe nesta maquina. Confirme que esta na REMOTA.' }
if (!(Test-Path "$PSScriptRoot\agente.ps1")) { throw 'Mantenha agente.ps1 na mesma pasta deste instalador.' }
$url=(Read-Host 'URL do projeto Supabase (https://....supabase.co)').Trim().TrimEnd('/')
if ($url -notmatch '^https://[a-z0-9-]+\.supabase\.co$') { throw 'URL Supabase invalida.' }
$key=(Read-Host 'Chave PUBLICA publishable ou anon (nunca service_role)').Trim()
if (!$key -or $key.StartsWith('sb_secret_')) { throw 'Use a chave publica do projeto.' }
if ($key.StartsWith('eyJ')) {
    try {
        $payload=$key.Split('.')[1].Replace('-','+').Replace('_','/')
        $payload=$payload.PadRight($payload.Length+(4-$payload.Length%4)%4,'=')
        $claims=[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($payload))|ConvertFrom-Json
        if ($claims.role -ne 'anon') { throw 'Chave nao publica.' }
    } catch { throw 'Use a chave anon publica, nunca service_role.' }
} elseif (!$key.StartsWith('sb_publishable_')) { throw 'Formato de chave publica desconhecido.' }
$segredo=Read-Host 'Token do dispositivo gerado pelo SQL (entrada oculta)' -AsSecureString
$ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($segredo)
try { $token=[Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr) }
finally { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) }
if ($token -notmatch '^[a-f0-9]{64}$') { throw 'Token invalido. Use o token de 64 caracteres gerado no cadastro.' }
$cfgPath=Join-Path $base 'agent-config.json'
if (Test-Path $cfgPath) { throw 'Agente ja configurado. Remova a instalacao anterior antes de configurar novamente.' }
@{supabaseUrl=$url;publicKey=$key;deviceId='pc-jogos';deviceToken=$token} |
    ConvertTo-Json | Set-Content -LiteralPath $cfgPath -Encoding UTF8
# Protege configuracao, script de controle e agente contra alteracoes por usuarios comuns.
icacls.exe $base /inheritance:r /grant:r '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-18:(OI)(CI)F'
if ($LASTEXITCODE -ne 0) { throw 'Falha ao proteger a pasta.' }
Copy-Item "$PSScriptRoot\agente.ps1" "$base\agente.ps1" -Force
foreach ($item in @($cfgPath,"$base\agente.ps1","$base\controle.ps1")) {
    icacls.exe $item /reset | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "Falha ao proteger $item" }
}
$action=New-ScheduledTaskAction -Execute "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$base\agente.ps1`""
$trigger=New-ScheduledTaskTrigger -AtStartup
$principal=New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 10 -RestartInterval (New-TimeSpan -Minutes 1) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName 'ShockImports-ControleJogos' -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName 'ShockImports-ControleJogos'
Write-Host 'Agente instalado. A pagina deve mostrar online em ate 1 minuto.'
