$ErrorActionPreference='Stop'
if($env:COMPUTERNAME -ne 'DESKTOP-8J8LHLR'){throw 'Instalar somente na REMOTA.'}
$admin=([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if(!$admin){throw 'Execute como administrador.'}
$base=Join-Path $env:ProgramData 'ControleNoturnoGiovanni'
if((Test-Path $base) -and !(Test-Path "$base\instalacao-noturna.txt")){throw 'Pasta existente sem identificacao; nao sobrescrever.'}
New-Item -ItemType Directory -Path $base -Force | Out-Null
icacls.exe $base /inheritance:r /grant:r '*S-1-5-32-544:(OI)(CI)F' '*S-1-5-18:(OI)(CI)F' | Out-Null
if($LASTEXITCODE -ne 0){throw 'Falha nas permissoes.'}
(Get-Item $base -Force).Attributes=(Get-Item $base -Force).Attributes -bor [IO.FileAttributes]::Hidden
Set-Content "$base\instalacao-noturna.txt" 'Controle PC Giovanni - Latencia noturna local - pasta separada'
foreach($file in @('LatenciaNoturna.cs','controle-noturno.ps1','remover-noturno.ps1')) {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $file) -Destination $base -Force
}
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$zip=Join-Path $base 'WinDivert-2.2.2-A.zip'
if(!(Test-Path $zip)){Invoke-WebRequest -UseBasicParsing -Uri 'https://github.com/basil00/WinDivert/releases/download/v2.2.2/WinDivert-2.2.2-A.zip' -OutFile $zip}
Expand-Archive -LiteralPath $zip -DestinationPath "$base\vendor" -Force
$dll=@(Get-ChildItem "$base\vendor" -Filter WinDivert.dll -Recurse | Where-Object {$_.Directory.Name -eq 'x64'})
$driver=@(Get-ChildItem "$base\vendor" -Filter WinDivert64.sys -Recurse | Where-Object {$_.Directory.Name -eq 'x64'})
if($dll.Count -ne 1 -or $driver.Count -ne 1){throw 'Pacote oficial nao corresponde a estrutura esperada.'}
$signature=Get-AuthenticodeSignature -LiteralPath $driver[0].FullName
if($signature.Status -ne 'Valid'){throw "Assinatura do driver nao validada: $($signature.Status). Nao desativar protecoes do Windows."}
Copy-Item $dll[0].FullName "$base\WinDivert.dll" -Force
Copy-Item $driver[0].FullName "$base\WinDivert64.sys" -Force
$compiler="$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe"
& $compiler /nologo /target:winexe /platform:x64 /optimize+ "/out:$base\LatenciaNoturna.exe" "$base\LatenciaNoturna.cs"
if($LASTEXITCODE -ne 0){throw 'Falha ao compilar.'}
$test=Start-Process -FilePath "$base\LatenciaNoturna.exe" -ArgumentList '--self-test' -Wait -PassThru -WindowStyle Hidden
if($test.ExitCode -ne 0){throw 'Teste de horario e oscilacao falhou.'}
$filterTest=Start-Process -FilePath "$base\LatenciaNoturna.exe" -ArgumentList '--check-filter' -Wait -PassThru -WindowStyle Hidden
if($filterTest.ExitCode -ne 0){throw 'Filtro de producao nao foi validado; agenda nao sera armada.'}
# So arma a agenda; nenhum atraso e aplicado durante o dia.
$name='ControlePCGiovanni-LatenciaNoturna'
$action=New-ScheduledTaskAction -Execute "$base\LatenciaNoturna.exe" -WorkingDirectory $base
$startup=New-ScheduledTaskTrigger -AtStartup
$daily=New-ScheduledTaskTrigger -Daily -At '22:00'
$principal=New-ScheduledTaskPrincipal -UserId SYSTEM -LogonType ServiceAccount -RunLevel Highest
$settings=New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Hours 9) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $name -Action $action -Trigger @($startup,$daily) -Principal $principal -Settings $settings -Force | Out-Null
$stopAction=New-ScheduledTaskAction -Execute "$env:WINDIR\System32\WindowsPowerShell\v1.0\powershell.exe" -Argument "-NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$base\controle-noturno.ps1`" parar"
Register-ScheduledTask -TaskName "$name-Encerrar06h" -Action $stopAction -Trigger (New-ScheduledTaskTrigger -Daily -At '06:00') -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName $name
Write-Host 'Agenda instalada em pasta separada e oculta. Ativa das 22h as 6h, horario local do Windows.'
Write-Host "Driver: $($signature.SignerCertificate.Subject)"
