# Histórico de versões

## 2.0.0 · novembro de 2026 · REID

Reescrita completa, alinhada ao plano de carreira (trilhas, níveis e modalidades).

- Novo nome: REID · Radar de Empregos e Inteligência de Dados (Recruitment Engine for IT and Data).
- Código organizado em pacote (`reid/`) com um módulo por responsabilidade; execução por `python -m reid`.
- Sites prioritários via buscador: Catho, InfoJobs, Nerdin, Sólides, Eureca e Cia de Talentos, com verificação do domínio, descarte de páginas de listagem e pontos extras na ordenação (também para LinkedIn e Gupy).
- Nova fonte: Remotive, para vagas remotas no exterior abertas a candidatos do Brasil (Worldwide e LATAM).
- Classificação única para todas as fontes: trilha (Dados, Desenvolvimento Python e Automação, Suporte e Infra N1, TI geral), nível (somente estágio e júnior) e modalidade (remoto no Brasil, remoto no exterior, híbrido ou presencial em cidades de fácil acesso do Grande Rio, com prioridade para o Centro do Rio).
- Somente vagas de estágio e júnior: trainee, vagas sem nível no título e vagas de nível pleno ou acima são descartadas, com o motivo no log.
- Vagas presenciais e híbridas só em cidades de fácil acesso do Grande Rio; Niterói e São Gonçalo ficam de fora. Vagas no Centro do Rio ganham prioridade.
- E-mail minimalista (preto, branco, cinzas e laranja) com o currículo indicado por seção, alerta de possível golpe e rodapé com as tecnologias mais citadas no mês.
- Planilha CSV anexa no formato de controle de candidaturas.
- Estatísticas mensais em `estatisticas.json`.
- Validação completa do `config.json`, histórico protegido contra corrupção, gravação atômica, novas tentativas de rede, falhas isoladas por fonte e anotações de aviso e erro na aba Actions.
- Workflow roda os testes antes do robô e impede execuções simultâneas.
- 130 testes automatizados.
- Histórico de vagas compatível com as versões anteriores.

## 1.x · outubro e novembro de 2026 · Robô de Vagas / Radar de Vagas

- Coleta na Gupy e no Google Vagas; envio por e-mail duas vezes por dia pelo GitHub Actions.
- Migração para o novo endereço da API da Gupy, com endereço de reserva.
- Leitura de datas nas etiquetas do Google Vagas.
- Gestão da cota da SerpApi com round-robin ponderado.
- Buscas no LinkedIn (vagas e publicações de recrutadores), trocadas do Google para o DuckDuckGo.
