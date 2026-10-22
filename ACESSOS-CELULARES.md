# Controle PC Giovanni — identificação dos acessos

| Identificação no Pi | Pessoa | Arquivo privado na LOCAL | Situação |
| --- | --- | --- | --- |
| `teste` | Seu celular | `ATIVAR-CELULAR.txt` | **Primeiro link criado. Preservado.** |
| `chefia` | Celular da chefia | `ATIVAR-CHEFIA.txt` | Acesso separado; pode funcionar junto com o de teste. |

Os links privados não são publicados no GitHub. Este registro contém somente
os nomes dos arquivos, sem códigos de acesso.

- Gerar ou revogar `chefia` não altera `teste`.
- Gerar ou revogar `teste` não altera `chefia`.
- Ativar novamente o mesmo perfil substitui somente o celular daquele perfil.
- Cada link vale por 24 horas e é usado uma vez. Cada sessão dura 30 dias.
- Apagar o arquivo TXT não revoga um celular já autorizado. A revogação precisa
  ser feita no Pi com o perfil correto.

## Revogar um acesso no Pi — somente quando solicitado

Para remover **apenas seu celular de teste**:

```bash
sudo -u pccontrol env PC_DATA=/var/lib/controle-pc python3 /opt/controle-pc/pi/server.py --revoke-phone teste
```

Para remover **apenas o celular da chefia**:

```bash
sudo -u pccontrol env PC_DATA=/var/lib/controle-pc python3 /opt/controle-pc/pi/server.py --revoke-phone chefia
```

Nenhum desses comandos de revogação foi executado ao criar este registro.
