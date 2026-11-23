# REID · Como atualizar o GitHub

Existem dois repositórios e dois pacotes, um para cada:

| Repositório | Visibilidade | Pacote | Diferença |
|---|---|---|---|
| `Reidner-Verdino/bot-vaga-estagio` | privado | `reid-privado.zip` | `config.json` com os recrutadores favoritos |
| `Reidner-Verdino/robo-vagas-estagio` | público | `reid-publico.zip` | `config.json` com a lista de recrutadores vazia |

Nenhum pacote contém `vagas_vistas.json` nem `estatisticas.json`. Assim, a atualização nunca apaga o histórico de vagas já enviadas.

A versão 2.0 tem pastas ocultas (`.github`) e exige apagar um arquivo antigo (`vagas_bot.py`). O caminho mais seguro é o terminal (Opção A). O navegador também funciona (Opção B), mas tem mais passos manuais.

## Opção A · Terminal (recomendada)

### 1. Criar um token de acesso (uma vez só)

O GitHub não aceita a senha da conta no terminal. Crie um token:

1. Acesse https://github.com/settings/tokens e clique em **Generate new token → Generate new token (classic)**.
2. Em **Note**, escreva `REID terminal`. Em **Expiration**, escolha 90 dias.
3. Marque os escopos **repo** e **workflow**. O escopo **workflow** é obrigatório, porque a atualização altera os arquivos de `.github/workflows`; sem ele, o envio é recusado.
4. Clique em **Generate token** e copie o código (começa com `ghp_`). Ele aparece só uma vez.

Quando o terminal pedir `Username`, digite `Reidner-Verdino`. Quando pedir `Password`, cole o token. Nada aparece enquanto você cola; isso é normal.

### 2. Atualizar o repositório privado

Considerando que os zips estão em `~/Downloads`:

```bash
cd ~
git clone https://github.com/Reidner-Verdino/bot-vaga-estagio.git
cd bot-vaga-estagio

git rm vagas_bot.py                              # código antigo, substituído pela pasta reid/
unzip -o ~/Downloads/reid-privado.zip -d .       # copia a versão 2.0 por cima

python3 -m unittest discover -s tests            # opcional: deve terminar com "OK" (*)
git add -A
git status
```

(*) Se aparecer `No module named 'requests'`, instale com `pip install requests` ou simplesmente pule esse comando: os mesmos testes rodam no GitHub antes de cada execução.

Antes de continuar, confira o resultado do `git status`:

- `vagas_vistas.json` **não pode** aparecer como `deleted` (apagado). Se aparecer, pare e rode `git restore --staged --worktree vagas_vistas.json`.
- Devem aparecer como novos: a pasta `reid/`, os testes novos, `docs/`, `README_EN.md` e `CHANGELOG.md`.

Se estiver tudo certo:

```bash
git commit -m "REID 2.0: trilhas, níveis e modalidades, Remotive, e-mail minimalista e 130 testes"
git push
```

### 3. Atualizar o repositório público

```bash
cd ~
git clone https://github.com/Reidner-Verdino/robo-vagas-estagio.git
cd robo-vagas-estagio
git rm vagas_bot.py
unzip -o ~/Downloads/reid-publico.zip -d .
git add -A
git status
git commit -m "REID 2.0: trilhas, níveis e modalidades, Remotive, e-mail minimalista e 130 testes"
git push
```

Se o `git clone` disser que a pasta já existe (de uma tentativa anterior), entre nela com `cd` e rode `git pull` antes do `git rm`.

## Opção B · Navegador

Faça em cada repositório, com o zip correspondente extraído numa pasta nova:

1. **Apague o código antigo:** abra `vagas_bot.py` no GitHub, clique em **⋯ → Delete file** e confirme com **Commit changes**.
2. **Envie os arquivos:** em **Add file → Upload files**, entre na pasta extraída, aperte **Ctrl + H** e **Ctrl + A** e arraste tudo. Confira na lista que os caminhos **não** começam pelo nome da pasta e clique em **Commit changes**.
3. **Atualize os workflows à mão,** porque o navegador ignora a pasta `.github`: abra `.github/workflows/vagas.yml`, clique no lápis ✏️, apague tudo, cole o conteúdo do `vagas.yml` da pasta extraída e confirme. Repita com `testes.yml`.

## Depois de atualizar

1. Na aba **Actions**, a lista à esquerda passa a mostrar o workflow **REID** (antes "Vagas de estágio").
2. No privado, clique em **REID → Run workflow** e aguarde o ✅.
3. Abra o passo **Buscar vagas e enviar e-mail** e confira o log: `REID v2.0.0`, as fontes consultadas e a linha `Aceitas: ... · novas: ...`.
4. Se houver vagas novas, o e-mail chega no visual novo, com a planilha CSV anexa.
5. No público, o mesmo workflow roda em modo teste (sem credenciais) e deve terminar com ✅.

Os segredos (`EMAIL_REMETENTE`, `EMAIL_SENHA_APP`, `EMAIL_DESTINO`, `SERPAPI_KEY`) continuam valendo e não precisam ser cadastrados de novo.

## Atualizações futuras

Para mudar só a configuração (por exemplo, um recrutador novo), edite o `config.json` direto no GitHub com o lápis ✏️. O workflow **Testes** roda sozinho e valida o arquivo; se ficar ❌, o log aponta exatamente o item errado.

Para mudanças maiores, repita a Opção A: `git pull`, altere, `python3 -m unittest discover -s tests`, `git add -A`, `git commit` e `git push`.
