# REID · Guia de carreira

Este guia liga o REID à consultoria de LinkedIn da Light Code Systems (novembro de 2026). Ele segue a "regra de ouro" da consultoria: **o mesmo nome, as mesmas datas e os mesmos números no LinkedIn, no currículo e na Gupy**. Todos os textos abaixo já estão unificados e podem ser colados como estão.

## 1. Fatos oficiais do projeto

Use estes dados em todos os lugares. Eles substituem as versões antigas ("Robô de Vagas de Estágio", "Radar de Vagas em TI e Dados", "22 testes").

| Item | Valor oficial |
|---|---|
| Nome | REID · Radar de Empregos e Inteligência de Dados |
| Nome em inglês | REID · Recruitment Engine for IT and Data |
| Início | outubro de 2026, em andamento |
| Frequência | duas vezes por dia (13h e 22h) |
| Fontes | 10: LinkedIn (incluindo publicações de recrutadores), Gupy, Catho, InfoJobs, Nerdin, Sólides, Eureca, Cia de Talentos, Google Vagas e Remotive |
| Trilhas | Dados, Desenvolvimento Python e Automação, Suporte e Infra N1 |
| Níveis | estágio e júnior |
| Modalidades | remoto no Brasil, remoto no exterior e híbrido ou presencial no Grande Rio (prioridade para o Centro) |
| Testes | 130 testes automatizados |
| Cota | 250 buscas por mês, distribuídas por round-robin ponderado |
| Código | https://github.com/Reidner-Verdino/robo-vagas-estagio |

## 2. Correções necessárias na consultoria

Conferi os links e dados da consultoria antes de usá-los. Estes itens precisam de ajuste:

| Onde aparece | Problema | Correção |
|---|---|---|
| Sobre (PT e EN), currículos, mensagens T2, T5, T8 e E1, banner | `github.com/reidnervedino` não existe (o GitHub responde "página não encontrada") | Usar `github.com/Reidner-Verdino`, que é a conta real com os repositórios |
| Seção 08, projeto 1 | `github.com/reidnervedino/[repositório]` | `https://github.com/Reidner-Verdino/robo-vagas-estagio` |
| Seção 08, projeto 2 | link do Telecom X | `https://github.com/Reidner-Verdino/telecomx-churn-analysis` (confirmado no ar) |
| Banner A e B (terminal) | "22 testes passando" e "radar_de_vagas.py" | O banner é uma imagem: peça à consultoria uma versão com "130 testes passando" e "python -m reid", ou mantenha sabendo que o número está desatualizado |
| Sobre, Experiência, Projetos, currículos, Post 1 | nome "Radar de Vagas em TI e Dados" e "22 testes" | Usar os textos da seção 3 deste guia |

A seção 04 da consultoria diz que a URL `linkedin.com/in/reidnervedino` está correta; ela foi mantida como está em toda a documentação do REID.

## 3. Textos prontos e unificados

### LinkedIn · Projetos (substitui o projeto 1 da seção 08)

**Nome do projeto:** REID · Radar de Empregos e Inteligência de Dados

```
Automação em Python que monitora vagas de estágio e júnior em TI e as envia por e-mail duas vezes ao dia, rodando na nuvem com GitHub Actions, sem servidor e sem custo.

Como funciona: coleta vagas em 10 fontes (LinkedIn (incluindo publicações de recrutadores), Gupy, Catho, InfoJobs, Nerdin, Sólides, Eureca, Cia de Talentos, Google Vagas e Remotive), classifica cada uma por trilha (Dados, Desenvolvimento ou Suporte), nível e modalidade (remoto no Brasil, remoto no exterior ou híbrido no RJ), indica qual currículo usar, remove duplicidades e envia um e-mail por prioridade com uma planilha de controle anexa.

Desafios que resolvi:
▸ A Gupy desativou o endereço antigo da API: identifiquei o novo endpoint pelos logs e criei um fallback entre endereços.
▸ O Google ignorava a restrição ao LinkedIn em buscas de emprego: um log com o motivo de cada descarte mostrou o problema, e troquei o motor de busca para o DuckDuckGo.
▸ O plano gratuito permite 250 buscas por mês: implementei um round-robin ponderado que prioriza as buscas mais importantes.
▸ Configuração validada antes de cada execução, histórico que nunca é sobrescrito por engano e 130 testes automatizados.

Código: https://github.com/Reidner-Verdino/robo-vagas-estagio
```

**Competências:** Python · API REST · GitHub Actions · Automação · ETL · Testes Automatizados · Git

### LinkedIn · Sobre (substitui o primeiro item de "O que já construí")

Português:

```
▸ REID · Radar de Empregos e Inteligência de Dados — automação em Python que coleta vagas em 10 fontes (LinkedIn (incluindo publicações de recrutadores), Gupy, Catho, InfoJobs, Nerdin, Sólides, Eureca, Cia de Talentos, Google Vagas e Remotive), classifica por trilha, nível e modalidade, remove duplicidades e envia um e-mail por prioridade duas vezes ao dia, rodando sozinha no GitHub Actions. Inclui gestão de cota de API (round-robin ponderado) e 130 testes automatizados.
```

Inglês:

```
▸ REID · Recruitment Engine for IT and Data — Python automation that collects job postings from 10 sources (LinkedIn (including recruiter posts), Gupy, Catho, InfoJobs, Nerdin, Sólides, Eureca, Cia de Talentos, Google Jobs and Remotive), classifies them by track, level and work model, removes duplicates and emails a prioritized digest twice a day, running on GitHub Actions. Includes API quota management (weighted round-robin) and 130 automated tests.
```

Na linha final do Sobre, troque `github.com/reidnervedino` por `github.com/Reidner-Verdino`.

### LinkedIn · Experiência "Projetos Independentes em Python, Dados e Automação"

Troque o primeiro item da descrição da seção 07 por:

```
▸ REID · Radar de Empregos e Inteligência de Dados: automação em Python (APIs + GitHub Actions) que monitora vagas em 10 fontes e envia relatório priorizado por e-mail 2x ao dia; 130 testes automatizados.
```

### Currículos · bloco de projetos (substitui o Radar da seção 10)

```
REID · Radar de Empregos e Inteligência de Dados | Python, APIs REST, GitHub Actions | out/2026 – atual | https://github.com/Reidner-Verdino/robo-vagas-estagio
• Pipeline que coleta vagas de 10 fontes (LinkedIn, Gupy, Catho, InfoJobs, Nerdin, Sólides, Eureca, Cia de Talentos, Google Vagas, Remotive), classifica por trilha, nível e modalidade, remove duplicadas e envia e-mail priorizado 2x ao dia, na nuvem e sem custo.
• Cota de API (250 buscas/mês) gerida com round-robin ponderado; configuração validada e 130 testes automatizados.
```

Nos resumos profissionais da seção 10, troque "22 testes automatizados" por "130 testes automatizados". No currículo em inglês, use "REID · Recruitment Engine for IT and Data".

### Gupy

A consultoria pede os mesmos títulos e datas da Gupy no LinkedIn. Por isso, a experiência na Gupy passa a ser a mesma do LinkedIn:

| Campo | O que preencher |
|---|---|
| Empresa | Autônomo |
| Cargo | Projetos Independentes em Python, Dados e Automação |
| Início | o mesmo mês e ano usados no LinkedIn |
| Fim | marcar "Trabalho atual" |
| Descrição | o texto abaixo |

```
Desenvolvo projetos próprios em Python, dados e automação, com código aberto no GitHub, para aplicar o que aprendo no curso e no programa ONE (Oracle + Alura).

- REID: automação em Python que monitora vagas em 10 fontes por APIs, classifica por trilha, nível e modalidade e envia relatório por e-mail 2x ao dia pelo GitHub Actions; 130 testes automatizados.
- Análise de churn (Telecom X): pipeline ETL e modelo de decisão.
- Análise Alura Store: mais de 9 mil vendas de 4 lojas analisadas com Python, Pandas e Matplotlib, com recomendação final para o negócio.
- Gerador de Escalas: rodízio justo com restrições por pessoa e exportação para Excel.

Código: github.com/Reidner-Verdino
```

Sem datas dentro da descrição: a IA da Gupy pode ler uma data no texto como outra experiência. A escala também pode ficar em **Conquistas → Trabalho voluntário**, com o título "Automação em Python da escala mensal de voluntários da igreja".

Em **Habilidades**, use os mesmos termos do LinkedIn: Python, SQL, Análise de Dados, ETL, API REST, GitHub Actions, Automação, Testes Automatizados, Git, Pandas.

## 4. O REID na rotina semanal da consultoria

A seção 11 da consultoria pede 5 a 8 candidaturas de qualidade por semana, em pelo menos duas modalidades. O REID foi desenhado para isso:

1. **Leia o e-mail uma vez por dia.** As seções já vêm na ordem da sua prioridade (Dados primeiro) e cada uma diz qual currículo usar.
2. **Escolha pela pontuação e pela modalidade.** As vagas dos seus sites preferidos (LinkedIn, Gupy, Catho, InfoJobs, Nerdin, Sólides, Eureca e Cia de Talentos) ganham pontos extras e aparecem primeiro. As vagas de cada seção estão ordenadas da mais aderente para a menos. "A confirmar" significa que a modalidade não estava no anúncio.
3. **Abra a planilha CSV anexa** e cole as vagas escolhidas na sua planilha de controle: as colunas já seguem o formato da consultoria (empresa, vaga, trilha, modalidade, data, contato, status e próximo passo).
4. **Candidate-se pelo canal oficial** com o currículo indicado, trocando 3 termos do resumo pelos do anúncio.
5. **Aborde o recrutador** com as mensagens T2 a T7 da consultoria, citando o REID como prova (e com o link certo do GitHub).
6. **Use o rodapé do e-mail para conteúdo.** A linha "Mais citados em [mês]" alimenta o post "As palavras mais pedidas nas vagas deste mês" do banco de ideias da consultoria.

Vagas marcadas com "Atenção: menciona pagamento" merecem cuidado redobrado: a consultoria recomenda desconfiar de vagas que cobram taxa.

## 5. Post de lançamento (substitui o Post 1 da consultoria)

```
Cansei de procurar estágio abrindo vários sites todo dia. Então construí um robô que faz isso por mim.

O REID (Radar de Empregos e Inteligência de Dados) é uma automação em Python que, duas vezes por dia:
→ coleta vagas no LinkedIn, em publicações de recrutadores, na Gupy, no Google Vagas e na Remotive
→ classifica cada uma por trilha (Dados, Desenvolvimento ou Suporte), nível e modalidade
→ remove duplicadas
→ e me envia um e-mail por prioridade, dizendo qual currículo usar em cada vaga

Roda na nuvem com GitHub Actions: sem servidor e sem custo.

O que mais me ensinou:
• Quando a Gupy desativou o endereço antigo da API, achei o novo endpoint pelos logs e criei um fallback.
• O Google ignorava a restrição ao LinkedIn nas buscas de emprego. Um log com o motivo de cada descarte mostrou o problema, e troquei o motor de busca.
• Para caber nas 250 buscas mensais do plano gratuito, implementei um round-robin ponderado.
• São 130 testes automatizados, e o robô só roda se todos passarem.

Código no primeiro comentário.

Que funcionalidade você adicionaria?

#Python #Automação #GitHubActions #Dados #Tecnologia
```

Primeiro comentário: `Código: https://github.com/Reidner-Verdino/robo-vagas-estagio`

## 6. Histórias para entrevista (formato STAR)

**A API da Gupy mudou.** Situação: o robô terminou sem erro, mas sem vagas da Gupy. Tarefa: descobrir por quê. Ação: o log mostrava HTTP 404; confirmei que a Gupy tinha migrado a API e criei uma lista de endereços com reserva. Resultado: a coleta voltou na execução seguinte e ficou preparada para a próxima mudança.

**O Google ignorava a restrição ao LinkedIn.** Situação: 21 resultados, zero aproveitados. Tarefa: saber se o problema era o filtro ou a busca. Ação: registrei no log o motivo, o título e o link de cada descarte; os resultados eram do Glassdoor e de outros agregadores. Testei o parâmetro próprio do Google, que também falhou, troquei para o DuckDuckGo e agrupei os termos com parênteses. Resultado: uma única busca passou a trazer 11 vagas do LinkedIn, todas aproveitadas.

**Histórico apagado por engano.** Situação: ao atualizar o repositório, substituí o histórico de vagas por uma versão vazia. Ação: restaurei a versão anterior pelo histórico de commits do GitHub. Resultado: nenhuma vaga repetida. Lição aplicada na versão 2.0: hoje o robô se recusa a rodar com um histórico corrompido e só grava depois do envio.

**Reescrita para não errar (versão 2.0).** Situação: o robô crescia em um único arquivo, com regras de filtro diferentes por fonte. Ação: separei em módulos, criei uma única regra de classificação para todas as fontes, validação completa da configuração e 130 testes, que rodam antes de cada execução. Resultado: cada descarte tem um motivo registrado, e uma mudança errada é barrada antes de chegar ao e-mail.

## 7. Perguntas prováveis

| Pergunta | Ponto central da resposta |
|---|---|
| Me fale sobre o projeto | Problema (horas de busca manual), solução (10 fontes, com prioridade para os sites escolhidos, classificação, e-mail 2x ao dia), resultado (em uso diário) |
| Por que não raspou o LinkedIn? | Termos de uso proíbem; uso o índice público de um buscador e confiro o domínio de cada resultado |
| Como evita vaga repetida? | Chave por título e empresa (ou link do post), histórico versionado, e a vaga de maior pontuação vence entre fontes |
| O que é o round-robin ponderado? | Fila em que buscas importantes aparecem mais vezes; cada execução pega o próximo trecho, dentro da cota |
| Como você testou? | 130 testes com unittest e respostas de API simuladas, sem internet, rodando antes de cada execução |
| Como garante que não erra? | Validação do config, histórico que nunca é sobrescrito por engano, gravação só após o envio, falhas por fonte isoladas e visíveis |
| Você usou IA? | Sim, como ferramenta. Defini os requisitos, testei com dados reais, li os logs, decidi as soluções e estudei o código até conseguir explicá-lo |

A última resposta só é verdadeira depois do plano de estudo da seção 8.

## 8. Plano de estudo do código

- [ ] Rodar `python -m reid --teste --previa previa.html` e abrir o arquivo no navegador.
- [ ] Ler `reid/texto.py` e testar `normalizar` e `tem_termo` no terminal do Python.
- [ ] Ler `reid/classificacao.py` com a tabela da seção 3 da documentação técnica ao lado.
- [ ] Acrescentar um termo ao `config.json` e escrever um teste para ele em `tests/test_filtros.py`.
- [ ] Ler `reid/cota.py` e montar no papel o ciclo para três buscas com pesos 3, 2 e 1.
- [ ] Ler uma fonte (`reid/fontes/gupy.py`) e o teste correspondente em `tests/test_fontes.py`.
- [ ] Fazer uma melhoria só sua, com teste, e explicá-la em dois minutos.
