# REID · Documentação técnica

Versão 2.0.0. Este documento descreve como o REID funciona, como configurá-lo e como resolver problemas. Para o uso do projeto na busca de emprego (LinkedIn, Gupy, currículo e entrevistas), veja o [Guia de carreira](GUIA_DE_CARREIRA.md). Para publicar alterações, veja [Como atualizar o GitHub](COMO_ATUALIZAR_O_GITHUB.md).

## 1. Uma execução, passo a passo

1. O GitHub Actions inicia o workflow `REID` às 16h e à 1h UTC (13h e 22h em Brasília) ou pelo botão **Run workflow**.
2. Os 130 testes rodam. Se algum falhar, o robô não roda.
3. O `config.json` é validado por completo. Qualquer erro interrompe a execução com código 2 e a lista de problemas.
4. O modo é definido: **produção** com `EMAIL_REMETENTE` e `EMAIL_SENHA_APP` preenchidos, **teste** sem nenhum dos dois, erro se só um estiver preenchido.
5. O histórico (`vagas_vistas.json`) e as estatísticas (`estatisticas.json`) são lidos. Arquivo ausente vale como vazio; arquivo corrompido interrompe a execução.
6. As fontes gratuitas (Gupy e Remotive) são consultadas. Em seguida, o saldo da SerpApi define quantas buscas pagas cabem nesta execução, e o revezamento escolhe quais.
7. Cada candidato passa pela classificação (seção 3). Os descartes são contados por fonte e motivo e aparecem no log.
8. As vagas aceitas são ordenadas por pontuação, e as repetidas (no histórico ou entre fontes) são removidas.
9. Em produção, o e-mail é enviado com a planilha CSV anexa. Só depois do envio o histórico e as estatísticas são gravados, e o workflow faz commit deles.

Se todas as fontes consultadas falharem, nada é enviado nem salvo e a execução termina com código 1.

## 2. Módulos

| Módulo | Responsabilidade |
|---|---|
| `reid/principal.py` | Linha de comando, ordem da execução, coleta, deduplicação, envio e gravação |
| `reid/classificacao.py` | Única regra de aceitação: trilha, nível, modalidade, alertas e pontuação |
| `reid/config.py` | Leitura e validação estrita do `config.json` |
| `reid/cota.py` | Divisão do saldo da SerpApi e escolha das buscas por round-robin ponderado |
| `reid/historico.py` | Leitura e gravação atômica do histórico e das estatísticas |
| `reid/relatorio.py` | E-mail em HTML e texto, assunto e planilha CSV |
| `reid/envio.py` | Montagem da mensagem e envio pelo SMTP do Gmail |
| `reid/rede.py` | Requisições HTTP com até 3 tentativas em falhas temporárias |
| `reid/texto.py` | Normalização, busca de termos e interpretação de datas |
| `reid/modelo.py` | Estruturas `Candidato` (dado bruto) e `Vaga` (dado classificado) |
| `reid/fontes/` | Uma fonte por arquivo (`gupy`, `linkedin`, `sites`, `google_vagas`, `remotive`, `serpapi`). As fontes só convertem dados; nunca decidem se a vaga entra |

## 3. Regras de classificação

As regras são aplicadas nesta ordem. A primeira que falhar define o motivo do descarte, que aparece no log exatamente com o texto da coluna "Motivo".

| Ordem | Regra | Motivo do descarte |
|---|---|---|
| 1 | Título não vazio e link começando com `http://` ou `https://` | dados incompletos |
| 2 | Data informada, quando a fonte exige data | sem data |
| 3 | Idade dentro do limite da fonte (`dias_maximos`) | mais antiga que o limite |
| 4 | Nenhum termo de `termos_excluir` | termo excluído |
| 5 | Pelo menos um termo de alguma trilha, na ordem das trilhas | fora das trilhas de TI |
| 6 | Publicações: nenhum termo de candidato | candidato procurando vaga |
| 7 | Publicações: algum sinal de anúncio | não anuncia vaga |
| 8 | Nível reconhecido fora de `niveis.aceitos` (por padrão, só estágio e júnior; trainee fica de fora) | nível não aceito |
| 9 | Nível pleno ou acima no título, sem estágio ou júnior | nível acima de júnior |
| 10 | Nível não informado: recusado por padrão (`aceitar_nivel_nao_informado: false`) e sempre no exterior | nível não informado |
| 11 | Exterior: região aceita para candidatos do Brasil | região do exterior não aceita |
| 12 | Brasil: remoto, ou cidade da lista, ou local genérico | presencial ou híbrido fora da região |

Detalhes que costumam gerar dúvida:

- **Ordem das trilhas.** Um título que cita dados e Python ("Engenheiro de Dados Python") entra em Dados, porque Dados vem primeiro.
- **Júnior vence pleno.** "Desenvolvedor Júnior/Pleno" é aceito como júnior.
- **Onde o nível é lido.** Em vagas, só no título. Em publicações, "estágio" ou "júnior" valem em qualquer parte do texto, mas os termos de nível alto continuam sendo lidos só no título.
- **Centro do Rio.** Vagas presenciais ou híbridas que citam o Centro do Rio (por exemplo, "Centro/RJ" ou "Centro do Rio de Janeiro") aparecem como "Presencial (Centro do Rio)" ou "Híbrido (Centro do Rio)" e ganham pontos extras. "Centro de Distribuição" não conta.
- **Publicações não entram em "TI geral".** Palavras como "tecnologia" aparecem em posts de qualquer área; por isso posts precisam de um termo de Dados, Desenvolvimento ou Suporte. Pelo mesmo motivo, a palavra "dados" sozinha só vale em títulos de vagas ("envie seus dados" não conta).
- **Cidade.** Só a primeira parte do local é comparada com a lista: "Macaé, Rio de Janeiro" é recusado; "Rio de Janeiro, RJ" é aceito.
- **Local genérico.** "Brasil", "Brazil" ou vazio viram modalidade "A confirmar": a vaga entra, e a modalidade deve ser conferida no anúncio.
- **Alertas.** Termos como "taxa de inscrição" ou "pix" não descartam a vaga, mas mostram um aviso laranja no e-mail.

## 4. Pontuação

A pontuação ordena as vagas dentro de cada seção e decide qual versão fica quando a mesma vaga chega por duas fontes.

| Componente | Pontos |
|---|---|
| Trilha | peso no `config.json`: Dados 30, Desenvolvimento 20, Suporte 10, TI geral 5 |
| Nível | Estágio 10, Júnior 10 (Trainee 8 e Não informado 0, se forem liberados no `config.json`) |
| Modalidade | Remoto 6, Híbrido (RJ) 6, Remoto (exterior) 5, Presencial (RJ) 4, A confirmar 0 |
| Centro do Rio | + `perfil.bonus_local_prioritario` (padrão 4) para presencial ou híbrido no Centro |
| Site prioritário | + `perfil.bonus_site_prioritario` (padrão 3) quando a vaga vem de LinkedIn, Gupy, Catho, InfoJobs, Nerdin, Sólides, Eureca ou Cia de Talentos, pelo nome da fonte ou pelo domínio do link |
| Recência | 3 se publicada há no máximo 2 dias |

## 5. Referência do config.json

| Chave | Tipo | Efeito |
|---|---|---|
| `perfil.cidades_presencial` | lista | Cidades de fácil acesso aceitas para vagas presenciais e híbridas: Rio de Janeiro, Mesquita, Nova Iguaçu, Nilópolis, São João de Meriti, Duque de Caxias, Belford Roxo e Queimados (acentos não importam) |
| `perfil.locais_prioritarios` | lista | Expressões que indicam o Centro do Rio |
| `perfil.bonus_local_prioritario` | 0 a 50 | Pontos extras para vagas no Centro do Rio |
| `perfil.sites_prioritarios` | lista | Sites que ganham prioridade, comparados com o nome da fonte e o domínio do link |
| `perfil.bonus_site_prioritario` | 0 a 50 | Pontos extras para vagas desses sites |
| `perfil.regioes_exterior_aceitas` | lista | Regiões aceitas em vagas do exterior ("worldwide", "latam"...) |
| `perfil.aceitar_nivel_nao_informado` | true/false | Aceita vagas no Brasil sem nível no título (padrão: false) |
| `niveis.aceitos` | lista | Níveis que entram no e-mail: `estagio`, `junior` e, se quiser, `trainee` (padrão: estágio e júnior) |
| `trilhas[]` | lista de objetos | `id`, `nome`, `curriculo` (texto exibido no e-mail), `peso` (0 a 100), `aceita_publicacoes`, `termos` e, opcional, `termos_somente_vagas` |
| `niveis.estagio`, `trainee`, `junior`, `excluidos` | listas | Termos que reconhecem cada nível (o trainee é reconhecido para poder ser recusado) |
| `termos_excluir` | lista | Termos que descartam a vaga |
| `termos_remoto`, `termos_hibrido` | listas | Sinais de modalidade no título, local ou trecho |
| `termos_sinal_vaga`, `termos_candidato` | listas | Distinguem anúncio de vaga de post de candidato |
| `termos_alerta` | lista | Termos que geram aviso de possível golpe |
| `termos_stack` | lista | Tecnologias contadas nas estatísticas mensais |
| `fontes.gupy` | objeto | `ativa`, `dias_maximos`, `paginas_por_termo` (100 vagas por página), `termos` |
| `fontes.google_vagas` | objeto | `ativa`, `peso` no revezamento, `dias_maximos`, `aceitar_sem_data`, `localizacao`, `consultas` |
| `fontes.linkedin` | objeto | `ativa`, `motor` (`duckduckgo` ou `google`), região e período de cada motor, `dias_maximos`, `recrutadores`, `recrutadores_peso`, `buscas` |
| `fontes.linkedin.buscas[]` | lista de objetos | `id` único, `peso` (1 a 10), `site` (precisa ser do linkedin.com) e `q` (a consulta) |
| `fontes.sites` | objeto | `ativa`, `peso` de cada site no revezamento, `dias_maximos`, `aceitar_sem_data`, região e período do DuckDuckGo e `lista` |
| `fontes.sites.lista[]` | lista de objetos | `id` único, `nome` (exibido no e-mail), `dominio` (só o domínio, como `catho.com.br`) e `q` (a consulta) |
| `fontes.remotive` | objeto | `ativa`, `dias_maximos` |
| `serpapi.dia_renovacao` | 1 a 31 | Dia do mês em que a cota da SerpApi renova |
| `serpapi.execucoes_por_dia` | 1 a 24 | Precisa bater com o número de horários do workflow |
| `serpapi.buscas_por_execucao_padrao` | 0 a 50 | Usado só quando o saldo não pode ser consultado |
| `email.max_por_secao` | 1 a 200 | Vagas exibidas por seção; o restante vai só para o CSV |
| `email.enviar_sem_vagas` | true/false | Envia e-mail mesmo sem novidades |
| `email.anexar_csv` | true/false | Anexa a planilha |
| `historico.dias` | 7 a 3650 | Tempo que uma vaga fica no histórico |

Regras de escrita dos termos: maiúsculas e acentos não importam; o termo casa como palavra inteira ("ti" não casa com "partida"); um `*` no fim casa o começo da palavra ("estagi*" casa estágio, estagiário e estagiária). Termos entre aspas nas consultas (`q`) são enviados ao buscador como estão.

**Recrutadores favoritos.** Os nomes em `fontes.linkedin.recrutadores` devem estar exatamente como aparecem no LinkedIn. Todos entram numa única busca, então acrescentar nomes não gasta cota. No repositório público a lista fica vazia, para não expor ninguém.

## 6. Segredos e variáveis de ambiente

| Variável | Obrigatória | Uso |
|---|---|---|
| `EMAIL_REMETENTE` | para envio | Gmail que envia |
| `EMAIL_SENHA_APP` | para envio | Senha de app de 16 letras do Gmail |
| `EMAIL_DESTINO` | não | Quem recebe; padrão é o remetente |
| `SERPAPI_KEY` | não | Sem ela, LinkedIn e Google Vagas não são consultados (aviso no log e no e-mail) |
| `SMTP_SERVIDOR`, `SMTP_PORTA` | não | Outro servidor SMTP; padrão `smtp.gmail.com`, porta 465 |

## 7. Arquivos de dados

`vagas_vistas.json` mapeia a chave de cada vaga enviada para a data do envio. A chave é título e empresa sem acentos e em minúsculas (`"estagio em dados|acme"`), ou o link sem parâmetros, no caso de publicações. É o mesmo formato das versões anteriores, então o histórico antigo continua valendo.

`estatisticas.json` guarda, por mês, o total de vagas novas, a contagem por trilha e quantas vagas citaram cada tecnologia. Os 12 meses mais recentes são mantidos.

Os dois arquivos são gravados de forma atômica (arquivo temporário e troca), então nunca ficam pela metade.

## 8. Linha de comando e códigos de saída

```bash
python -m reid                               # produção (ou teste, sem credenciais)
python -m reid --teste                       # nunca envia nem salva
python -m reid --validar                     # só valida o config.json
python -m reid --teste --previa previa.html  # grava o e-mail em HTML para conferir
```

| Código | Significado |
|---|---|
| 0 | Sucesso, com ou sem vagas novas |
| 1 | Falha na execução: todas as fontes falharam, o envio falhou ou o histórico está corrompido |
| 2 | Configuração inválida ou credenciais incompletas |

## 9. Lendo o log e resolvendo problemas

| No log ou no e-mail | Causa | O que fazer |
|---|---|---|
| `[Cota] 0 nesta execução` | Saldo da SerpApi esgotado até a renovação | Nada; Gupy e Remotive continuam. Confira `serpapi.dia_renovacao` |
| `SERPAPI_KEY não definida` | Segredo ausente | Cadastrar o segredo no repositório privado |
| `Gupy: HTTP 404` nos dois endereços | A Gupy mudou a API de novo | Abrir o portal da Gupy, achar o novo endereço e atualizar `ENDERECOS` em `reid/fontes/gupy.py` |
| Muitos `não é do LinkedIn` ou `não é do Catho` (ou de outro site) | O buscador ignorou a restrição de site | Simplificar a consulta do site |
| Muitos `página de listagem, não de vaga` | O buscador devolveu páginas como "120 vagas de estágio em TI" | Nada; essas páginas não são vagas e são descartadas de propósito |
| Muitos `fora das trilhas de TI` com títulos de TI | Falta um termo | Acrescentar o termo na trilha certa e um teste |
| Muitos `nível não informado` | Vagas sem estágio ou júnior no título: descartadas de propósito | Nada; para recebê-las, mude `aceitar_nivel_nao_informado` para true |
| `config.json inválido` | Chave ausente, tipo errado ou vírgula sobrando | Corrigir o item apontado; `python -m reid --validar` confere |
| `está corrompido` | Edição manual quebrou o JSON do histórico | Restaurar a versão anterior pelo histórico de commits |
| `ERRO ao enviar o e-mail` | Senha de app inválida ou trocada | Gerar outra senha de app e atualizar `EMAIL_SENHA_APP` |
| Execução sem e-mail | Nenhuma vaga nova | Nada; o log mostra `Nenhuma vaga nova` |

Avisos aparecem em amarelo na aba **Actions** do GitHub, e erros em vermelho, graças às anotações do workflow.

## 10. Como estender

- **Novo termo:** acrescente na lista certa do `config.json`, rode `python -m reid --validar` e escreva um teste em `tests/test_filtros.py` com um título real.
- **Novo recrutador:** acrescente o nome em `fontes.linkedin.recrutadores` (só no repositório privado).
- **Novo site de vagas:** acrescente um objeto em `fontes.sites.lista` com `id`, `nome`, `dominio` e `q`, e o nome em `perfil.sites_prioritarios` se ele deve ter prioridade. Cada site novo é mais uma busca no revezamento da cota.
- **Nova busca do LinkedIn:** acrescente um objeto em `fontes.linkedin.buscas` com `id` único e `peso`. Agrupe alternativas entre parênteses, porque um `OR` solto quebra a restrição de site.
- **Nova fonte:** crie `reid/fontes/nome.py` com uma função que devolva `(candidatos, falhas)` usando `Candidato`, chame-a em `coletar` no `principal.py`, crie a seção em `fontes` no `config.json` e a validação em `config.py`, e escreva testes com respostas simuladas.

## 11. Testes

`python -m unittest discover -s tests` roda os 130 testes em menos de um segundo, sem acesso à internet: as respostas das APIs e o envio de e-mail são simulados. Eles cobrem texto e datas, cada regra de classificação, cada fonte, a camada de rede, a cota, o histórico, o relatório, a validação do `config.json` e execuções completas (envio, repetição, falhas de fonte, falha de envio, histórico corrompido e modos de execução).

## 12. Limitações conhecidas

- Publicações do LinkedIn visíveis só para conexões não aparecem em buscadores, e as públicas podem levar horas ou dias para ser indexadas.
- Os sites via buscador (Catho, InfoJobs, Nerdin, Sólides, Eureca e Cia de Talentos) não informam a empresa no resultado da busca, e o local só é lido quando aparece como "Cidade, UF" ou "Cidade/UF". Essas vagas são identificadas pelo link no histórico.
- Com 14 a 15 buscas pagas no revezamento e cerca de 8 por dia, cada site é consultado mais ou menos a cada 2 ou 3 dias; como a busca cobre a última semana, nenhuma vaga recente fica de fora por isso.
- A Remotive tem um feed pequeno, e a maioria das vagas é sênior; poucas passam nos filtros.
- O nível é lido só do título das vagas. Uma vaga júnior cujo título não diga "júnior" é descartada; essa é a troca por um e-mail só com vagas de estágio e júnior.
- O Centro do Rio só é reconhecido quando o anúncio o cita; a Gupy e o Google Vagas costumam informar apenas a cidade.
- A palavra "tecnologia" em títulos pode trazer vagas de outras áreas (por exemplo, tecnologia de alimentos) na seção "TI geral".
