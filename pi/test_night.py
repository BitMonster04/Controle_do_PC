"""Diagnostico curto: afeta apenas ICMP para 1.1.1.1, fora do horario noturno."""
from deploy_remote import remote
script=r'''
$base='C:\ProgramData\ControleNoturnoGiovanni'
& "$env:WINDIR\Microsoft.NET\Framework64\v4.0.30319\csc.exe" /nologo /target:winexe /platform:x64 /optimize+ "/out:$base\LatenciaNoturna.exe" "$base\LatenciaNoturna.cs"
if($LASTEXITCODE -ne 0){throw 'Compilacao falhou'}
$p=Start-Process -FilePath "$base\LatenciaNoturna.exe" -ArgumentList '--self-test' -Wait -PassThru -WindowStyle Hidden
if($p.ExitCode -ne 0){throw 'Self-test falhou'}
$p=Start-Process -FilePath "$base\LatenciaNoturna.exe" -ArgumentList '--check-filter' -Wait -PassThru -WindowStyle Hidden
if($p.ExitCode -ne 0){Get-Content "$base\noturno.log" -Tail 2;throw 'Filtro de producao invalido'}
Write-Output 'SELF_TEST=0 FILTER_CHECK=0'
$baseline=@(Test-Connection 1.1.1.1 -Count 3 | Select-Object -ExpandProperty ResponseTime)
Write-Output ('BASELINE_MS='+($baseline -join ','))
foreach($delay in @(150,700)) {
    $p=Start-Process -FilePath "$base\LatenciaNoturna.exe" -ArgumentList '--probe-ms',"$delay" -PassThru -WindowStyle Hidden
    try {
        Start-Sleep -Seconds 1
        $samples=@(Test-Connection 1.1.1.1 -Count 3 | Select-Object -ExpandProperty ResponseTime)
        if(!$p.WaitForExit(20000)){throw 'Sondagem nao encerrou no prazo'}
        $p.Refresh()
        if($p.ExitCode -ne 0){throw "Sondagem falhou: $($p.ExitCode)"}
        Write-Output ('PROBE'+$delay+'_MS='+($samples -join ',')+' EXIT='+$p.ExitCode)
    } finally { if(!$p.HasExited){Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue} }
}
$after=@(Test-Connection 1.1.1.1 -Count 3 | Select-Object -ExpandProperty ResponseTime)
Write-Output ('AFTER_MS='+($after -join ','))
Get-Content "$base\noturno.log" -Tail 6
'''
print(remote(script).replace('__PC_OK__','').strip())
