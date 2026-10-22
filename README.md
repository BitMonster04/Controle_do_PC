# Controle do PC — Shock Imports

## Hospedagem atual: Pi (substitui o Supabase)

### Celular da chefia e instalacao pelo Chrome

O painel agora se chama **Controle PC Giovanni**. O indicador online/offline
aparece em destaque acima do botao. `manifest.webmanifest`, icones 192/512 e
service worker permitem instalar pelo Chrome. O botao “Instalar no celular”
usa o convite nativo quando disponivel e mostra instrucoes do menu caso contrario.
O service worker nao guarda respostas da API nem simula estado offline.

`pi/activate_phone.py` gera link de uso unico valido por 24 horas e o salva
apenas em `ATIVAR-CELULAR.txt` na LOCAL (ignorado pelo Git). Abra esse link
primeiro no Chrome do celular da chefia. A sessao fica salva por 30 dias,
sem digitar senha. Existem dois perfis independentes: `teste` (primeiro link,
seu celular) e `chefia`. Ambos funcionam ao mesmo tempo. Ativar novamente o
mesmo perfil substitui somente o aparelho daquele perfil. Limpar os dados do
Chrome exige novo link. Consulte `ACESSOS-CELULARES.md` antes de revogar acessos.
O link de ativacao e privado; nao publica-lo no repositorio.

Para gerar somente o acesso da chefia, use `python pi/activate_phone.py --name chefia`.
Ele salva em `ATIVAR-CHEFIA.txt`, sem tocar no primeiro `ATIVAR-CELULAR.txt`.

O login por senha de recuperacao continua disponivel em
`/controle-pc/?recuperar=1`; nao foi removido globalmente. Nenhuma alteracao
nessa configuracao instala ou autoriza o agente SYSTEM da REMOTA.

Painel instalado em:
https://aurora2d.tail8abf1e.ts.net:8443/controle-pc/

O GitHub Pages apenas redireciona para esse endereco. O Pi hospeda interface,
login, SQLite e a API do agente. Nenhuma configuracao Supabase e necessaria
nessa instalacao. As instrucoes antigas mais abaixo sao somente referencia.

- Servico: `controle-pc.service`, usuario sem login `pccontrol`.
- Backend: `127.0.0.1:8795`, publicado pelo Nginx existente em `/controle-pc/`.
- Codigo: `/opt/controle-pc`; dados privados: `/var/lib/controle-pc`.
- Credenciais iniciais: `/root/controle-pc-credenciais.json`, permissao 600.
- O agente usa HTTPS de saida; nao abre porta na REMOTA.
- O estado atual precisa ser informado pelo agente antes de habilitar a trava.
- Vermelho = Trava ativada. Verde = Trava desativada. Antes do login, o mesmo
  botao central oferece acesso ao controle, sem exibir um estado inventado.

`pi/install.sh` instala o painel no Pi e preserva os outros aplicativos.
`pi/access_note.py` salva a senha do painel somente em `PAINEL-ACESSO.txt`,
arquivo ignorado pelo Git; nao imprime senha nem token.
`pi/deploy_remote.py` prepara a REMOTA e transfere o token individual por SSH
(stdin criptografado), sem token em argumentos de processo ou GitHub.
`windows/instalar-pi.ps1` instala a tarefa `ShockImports-ControleJogos` como
SYSTEM ao iniciar o Windows. A tarefa executa somente bloquear/desbloquear
pelo script local `controle.ps1`. `windows/remover-agente.ps1` remove a tarefa.

O backend foi validado com oito testes de login, autorizacao, confirmacao,
expiracao e auditoria. Execute `python -m unittest discover -s tests -p test_pi.py`.
Os sete testes de interface continuam em `node --test tests/panel.test.mjs`.
Validacao de sintaxe nao substitui a instalacao real na REMOTA.

**Situacao ao preparar esta versao:** painel instalado e verificado no Pi;
agente da REMOTA ainda pendente de instalacao e autorizacao explicita apos
revisao automatica. Nao presumir controle de ponta a ponta antes de verificar
o primeiro heartbeat e a execucao de uma ordem.

---

## Arquitetura anterior — Supabase (nao usada no Pi)

Painel com um botao grande no centro: **Trava ativada** em vermelho e
**Trava desativada** em verde. O clique solicita o estado oposto. O painel
so confirma a mudanca quando a REMOTA informa o resultado do firewall.

GitHub Pages hospeda a interface. Supabase recebe o estado e as ordens.
Um agente PowerShell na REMOTA consulta o servidor a cada 15 segundos.
O chefe usa apenas o navegador; Tailscale e SSH nao sao necessarios para o painel.

## 1. Supabase — no navegador da LOCAL

1. Crie um projeto Supabase para este painel.
2. Em SQL Editor, execute **uma vez** `supabase/schema.sql`.
3. Em Authentication > Users > Add user, crie o usuario do chefe com email
   e uma senha exclusiva do painel. Confirme o email no cadastro administrativo.
   Nao use a senha Windows.
4. Em Authentication, desabilite novos cadastros publicos se nao forem necessarios.
   Mesmo com cadastros abertos, usuarios nao autorizados nao acessam os controles.
5. Abra `supabase/cadastrar.sql`, substitua `EMAIL_DO_CHEFE_AQUI` pelo email
   cadastrado e execute. Guarde o token retornado para instalar o agente.
   Se a consulta nao retornar token, confira o erro; nao execute novamente para
   trocar o token de um dispositivo que ja esteja instalado.
6. Confirme o cadastro do operador no SQL Editor:

```sql
select u.email from pc_private.operators o join auth.users u on u.id=o.user_id;
```

Somente os usuarios desta lista podem consultar ou alterar o painel.

## 2. Publicar a pagina — na LOCAL

Edite `config.js` no GitHub e preencha:

```js
window.PC_CONFIG = {
  supabaseUrl: 'https://SEU-PROJETO.supabase.co',
  supabasePublicKey: 'SUA_CHAVE_PUBLICA_PUBLISHABLE_OU_ANON',
  deviceId: 'pc-jogos'
};
```

A URL esta no projeto Supabase; a chave publica fica nas configuracoes de
API/API Keys. `sb_publishable_...` ou a antiga `anon` sao publicas.
**Nunca publique `service_role`, `sb_secret_...`, senha ou token do agente.**

Em GitHub > Settings > Pages > Build and deployment > Source, escolha
**GitHub Actions**. Execute o workflow **Publicar painel** em Actions se o
push inicial ocorreu antes dessa configuracao. A URL esperada e:

https://bitmonster04.github.io/Controle_do_PC/

Antes da configuracao, a pagina mostra o botao grande desabilitado, com
“Aguardando conexao”, sem simular um estado de trava confirmado. A URL acima
nao confirma que o GitHub Pages ja terminou a publicacao.

## 3. Instalar o agente — SOMENTE NA REMOTA

A REMOTA ja deve ter `C:\ProgramData\BloqueioJogos\controle.ps1`, o script
de firewall instalado anteriormente. Este pacote nao instala jogos nem Python.

1. Baixe o ZIP deste repositorio (Code > Download ZIP) e extraia na REMOTA.
2. Abra PowerShell como administrador na REMOTA.
3. Execute o instalador da pasta extraida, adaptando o caminho:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\CAMINHO\Controle_do_PC-main\windows\instalar.ps1"
```

4. Informe a URL do Supabase, a chave publica e o token gerado no passo 1.
   O token e solicitado com entrada oculta. Nao o envie pelo chat ou GitHub.
5. O instalador copia o agente e cria a tarefa `ShockImports-ControleJogos`,
   executada como SYSTEM ao iniciar o Windows, sem precisar de usuario logado.
   A tarefa do sistema usa janela oculta para nao abrir um terminal a cada boot;
   permanece visivel no Agendador de Tarefas para administracao.

O token fica apenas em `C:\ProgramData\BloqueioJogos\agent-config.json`,
com acesso limitado a Administradores e SYSTEM. A pasta tambem fica protegida
contra alteracao do script executado pela tarefa.

## 4. Uso e verificacao

1. Abra a pagina e entre com o usuario autorizado do chefe.
2. A REMOTA deve aparecer online em ate um minuto.
3. Clique no botao. Ele mostra “Aplicando…” e aguarda a REMOTA.
4. Verifique vermelho/“Trava ativada” e verde/“Trava desativada”.
5. Desligue a REMOTA: depois de 60 segundos sem sinal, aparece offline.
   Offline significa sem comunicacao do agente; pode ser internet indisponivel,
   suspensao ou agente parado, e nao prova que o computador foi desligado.

Ligar o computador **nao altera automaticamente** a escolha da trava. As regras
do firewall permanecem apos reiniciar. O agente nao reaplica estados antigos
apenas por iniciar; executa somente ordens pendentes com validade de dois minutos.
Se a REMOTA cair durante uma ordem, ela pode recebe-la ao reconectar dentro
desses dois minutos. O botao fica desabilitado quando a maquina esta offline.

O botao nao altera o firewall de forma otimista: o resultado vem do agente.
O estado vermelho indica regras ativas do grupo `BloqueioJogosLocal`, nao uma
garantia de bloquear qualquer jogo. Jogos de navegador, outras pastas e novas
versoes em caminhos diferentes podem escapar do script de identificacao atual.

### Diagnostico NA REMOTA

```powershell
Get-ScheduledTaskInfo -TaskName 'ShockImports-ControleJogos'
Get-Content 'C:\ProgramData\BloqueioJogos\agente.log' -Tail 15
```

O log nao grava o token nem respostas com credenciais. Se o firewall nao puder
ser consultado, o agente nao informa um falso estado de sucesso; apos 60 segundos
sem sinal, o painel marca sem comunicacao.

### Remover agente NA REMOTA

Execute `windows/remover-agente.ps1` como administrador. Isso remove a tarefa
e o token local; **mantem as regras existentes**. Para liberar os jogos antes
de remover, use o botao ou o comando local:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\ProgramData\BloqueioJogos\controle.ps1" desbloquear
```

Para revogar definitivamente o agente, remova o dispositivo no SQL Editor do
Supabase (remova primeiro suas linhas de auditoria), ou atualize `token_hash`
com o hash de um novo segredo e configure novamente a REMOTA.

## Arquitetura e autorizacao

- Nenhuma porta de entrada e aberta pelo painel ou agente.
- Navegador e agente fazem conexoes HTTPS para Supabase.
- Login nao basta: as funcoes verificam `auth.uid()` na lista de operadores.
- Tabelas privadas usam RLS sem politicas publicas e nao concedem acesso direto.
- O agente usa token aleatorio por dispositivo, armazenado como SHA-256 no banco.
- O token permite apenas informar estado e receber a acao do proprio dispositivo.
- Ordens aceitam exclusivamente os dois estados booleanos; nao ha execucao de
  comandos arbitrarios, SSH pelo navegador ou caminhos recebidos da pagina.
- Todas as ordens sao registradas em `pc_private.audit`.
- A pagina nao mostra notificacoes fora do navegador: o indicador online e
  atualizado enquanto a pagina estiver aberta. Alertas por email/push exigem
  implementacao separada.

## Validacao local

```text
node --test tests/panel.test.mjs
```

Os testes simulam os estados da interface; nao substituem a verificacao com o
projeto Supabase configurado e o firewall da REMOTA. SQL, login, tarefa e ciclo
completo precisam dessa configuracao real.
