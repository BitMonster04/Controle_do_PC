# Chaves SSH — Controle PC Giovanni

Referência de nomes e caminhos. **Não contém chaves privadas.**

| Identificação | Privada guardada em | Destinos autorizados | Teste |
| --- | --- | --- | --- |
| Principal original | LOCAL: `C:\Users\Paula\.ssh\controle_jogos` | Pi e REMOTA | Funcionando; preservada. |
| Reserva LOCAL | LOCAL: `C:\Users\Paula\.ssh\controle_giovanni_reserva_local` | Pi e REMOTA | Ambas as conexões confirmadas. |
| Codex do Pi → REMOTA | Pi: `/home/bit/.ssh/controle_giovanni_remota` | REMOTA `ggped@100.87.198.65` | Conexão confirmada com verificação estrita do host. |

As chaves públicas correspondentes têm sufixo `.pub`. Somente as públicas
foram cadastradas nos destinos; as privadas permaneceram na máquina de origem.
A identidade SSH da REMOTA foi obtida pela conexão já confiável e registrada
no `known_hosts` do Pi. Não foi necessário desativar a verificação de host.

## A partir do Pi — para o Codex que roda nele

```bash
ssh -i /home/bit/.ssh/controle_giovanni_remota -o IdentitiesOnly=yes -o BatchMode=yes -o StrictHostKeyChecking=yes ggped@100.87.198.65
```

## A partir da LOCAL — usando a reserva

Para o Pi:

```powershell
ssh -i "$env:USERPROFILE\.ssh\controle_giovanni_reserva_local" -o IdentitiesOnly=yes bit@aurora2d
```

Para a REMOTA:

```powershell
ssh -i "$env:USERPROFILE\.ssh\controle_giovanni_reserva_local" -o IdentitiesOnly=yes ggped@100.87.198.65
```

As reservas são identidades independentes, não cópias da chave principal.
Não protegem contra máquina desligada, Tailscale desconectado ou serviço SSH
parado. Nessas situações, outras chaves também não estabelecem a conexão.

## Acesso SSH e acesso ao painel são diferentes

Os perfis de celular `teste` e `chefia` continuam independentes dessas chaves.
Nenhum acesso de celular foi revogado ao criar as reservas.

## Estado da instalação

O usuário autorizou concluir a instalação com a REMOTA ligada. O agente foi
instalado como tarefa `ShockImports-ControleJogos`, executada como SYSTEM.
Primeiro heartbeat confirmado no Pi: trava ativa, **225 regras**.
Teste real de ordem pela API concluído: revisão **1**, reconhecida pelo agente,
mantendo a trava ativa e as 225 regras. Nenhuma liberação dos jogos foi feita
nesse teste. A tarefa está configurada para iniciar no boot; não foi reiniciada
a REMOTA para testar um ciclo completo de inicialização.

Atualização: 22/10/2026.
