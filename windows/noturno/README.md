# Night Network Control

Instalação separada da trava principal no computador REMOTO.

## Comportamento

- Pasta: `C:\ProgramData\NightNetworkControl`, atributo **Hidden**.
- Conta das tarefas: SYSTEM; arquivos graváveis apenas por Administradores/SYSTEM.
- Horário do Windows confirmado: `E. South America Standard Time` (Brasília).
- Todos os dias, ativa às **22:00** e retira o atraso às **06:00**.
- Se o computador ligar durante a janela, o gatilho de inicialização inicia a trava.
- Se ligar fora dela, o programa encerra sem abrir captura de pacotes.
- Não depende do Pi, da internet do celular ou de o chefe abrir o painel.
- Atraso ADICIONAL varia suavemente de **150 até 700 ms**, voltando a 150 ms,
  em ciclo triangular de 60 segundos. Não define o ping total da conexão.
- A primeira trava, seus arquivos e suas regras não são alterados.

Às 6h, a segunda trava para e esvazia a fila. Se a trava principal continuar
ativada, seus bloqueios de jogos continuam: encerrar a latência noturna não
libera as regras da primeira trava. O botão atual do painel controla apenas
a primeira trava, não esta segunda agenda.

## Escopo e exceções

É atraso de pacotes de saída usando o driver oficial WinDivert 2.2.2-A, não
queda periódica de rede nem limitação de banda apresentada como ping.

Para preservar administração e serviços básicos, o filtro exclui:

- SSH TCP 22 (origem e destino).
- TCP de saída para 443 e 8443 (HTTPS, painel e relays de administração).
- UDP 41641 (Tailscale, porta observada na instalação).
- DNS UDP 53.
- Loopback, redes privadas IPv4 e a faixa IPv4 Tailscale 100.64.0.0/10.
- Endereços IPv6 locais fd00::/8.

Essas exceções também permitem que jogos/transportes que usem exclusivamente
os caminhos excluídos escapem da latência. Não é detecção universal de jogos.
Aplicativos que usam o tráfego capturado também terão atraso à noite.
Se a porta do Tailscale mudar, revisar as exceções antes de alterar o filtro.

O programa não grava conteúdo de pacotes, senhas ou histórico de navegação.
A fila tem limite de memória; se lotar, antecipa envio em vez de acumular
memória indefinidamente. Os pacotes não são alterados além do recálculo de checksum.

## Tarefas e arquivos

| Recurso | Identificação |
| --- | --- |
| Iniciar no boot e às 22h | `NightNetworkControl` |
| Encerrar às 6h | `NightNetworkControl-StopAt0600` |
| Programa | `NightNetworkControl.exe` |
| Código-fonte | `NightNetworkControl.cs` |
| Controle administrativo | `night-control.ps1` |
| Log, sem conteúdo de rede | `night-control.log` (rotação em 1 MiB) |
| Desativação persistente | `desativado.flag` |
| Pedido de encerramento | `parar.flag` |

As tarefas ficam visíveis no Agendador de Tarefas para administração. A pasta
oculta não é proteção contra outro administrador. Não há ocultação de driver,
remoção de logs, alteração de antivírus ou desativação de assinatura do Windows.

## Comandos — SOMENTE NA REMOTA, como administrador

Status:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\ProgramData\NightNetworkControl\night-control.ps1" status
```

Desativar a segunda trava e impedir as próximas ativações até reabilitar:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\ProgramData\NightNetworkControl\night-control.ps1" desativar
```

Reabilitar a agenda (fora de 22h–6h não cria atraso imediato):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\ProgramData\NightNetworkControl\night-control.ps1" ativar
```

Remover as tarefas sem mexer na primeira trava:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\ProgramData\NightNetworkControl\remove-night-control.ps1"
```

A remoção mantém arquivos e logs para revisão. Não apaga serviço WinDivert
que possa ser usado por outro aplicativo.

## Instalação e fontes

`install-night-control.ps1` deve ser executado com os quatro fontes desta pasta
na REMOTA. Ele baixa o pacote oficial, exige assinatura válida do driver,
compila usando o C# do .NET Framework e cria as tarefas. O helper
`pi/install_night.py` orquestra o envio a partir da LOCAL por SSH.

O arquivo binário compilado e o pacote do fornecedor não entram no Git.
As licenças do WinDivert permanecem na pasta vendor extraída da distribuição.
Não remover proteções do Windows caso uma atualização passe a bloquear o driver.

Fontes oficiais:

- https://github.com/basil00/WinDivert/releases/tag/v2.2.2
- https://github.com/basil00/WinDivert/blob/v2.2.2/include/windivert.h
- https://reqrypt.org/windivert-doc.html

## Verificação

- `NightNetworkControl.exe --self-test`: limites 21:59/22h/05:59/06h e atraso
  sempre entre 150 e 700 ms, com progressão da fila sem inversão.
- `NightNetworkControl.exe --check-filter`: valida o filtro completo na biblioteca
  oficial, sem capturar tráfego.
- `NightNetworkControl.exe --probe-ms 150` ou `700`: diagnóstico por 12 segundos,
  restrito a ICMP de saída para 1.1.1.1, com parada automática.
- `pi/test_night.py`: compila na REMOTA, valida o filtro, mede as duas sondagens
  e o retorno ao normal. Não executá-lo à noite com a captura principal noturna
  já ativa, pois uma instância única protege contra concorrência.

O teste encontrou e corrigiu um erro de parâmetro no encerramento do driver.
A versão final usa `WINDIVERT_SHUTDOWN_RECV=1` e tem limite de encerramento,
além de liberar a fila antes de fechar o handle.

Os gatilhos reais de 22h, 6h e boot não exigem alterar o relógio do Windows
para teste. Testes de fronteira de horário não equivalem a observar uma noite
completa de execução.

### Resultado na REMOTA em 22/10/2026

- Driver: assinatura Authenticode **Valid**, pacote oficial 2.2.2-A.
- Self-test e compilação do filtro: código de saída 0.
- Ping antes: 3–5 ms.
- Sondagem com +150 ms: **167, 169 e 168 ms**; encerrou sozinha com código 0.
- Sondagem com +700 ms: **718, 711 e 703 ms**; encerrou sozinha com código 0.
- Ping depois: **6, 15 e 12 ms**, sem captura restante do teste.
- Produção iniciada durante o dia encerrou sozinha com código 0 e registrou
  “Fora da janela 22h-06h; nenhum atraso aplicado”.
- Próxima execução confirmada: **22/10/2026 às 22h**, tarefas habilitadas.
- Pasta confirmada oculta; instalação temporária removida.
- A trava principal foi observada separadamente como desativada no fim da
  verificação (revisão 4 reconhecida, zero regras). A instalação noturna não
  enviou ordem de liberar ou bloquear a primeira trava.


### Identificação atual

A segunda instalação usa somente o nome **Night Network Control**. A pasta
`C:\ProgramData\NightNetworkControl` permanece oculta. Os nomes pessoais
foram removidos dos arquivos atuais dessa instalação e das tarefas. Horários,
exceções e funcionamento foram preservados; os logs foram mantidos.
