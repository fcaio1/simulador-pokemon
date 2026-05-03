# Simulador de Pokémon TCG

Aplicação para analisar decks do Pokémon TCG a partir de uma deck list exportada do PTCG Live. O projeto combina cálculos teóricos de probabilidade com simulação de Monte Carlo e uma interface em Streamlit para mostrar os resultados de forma rápida.

## O que o projeto faz

O simulador recebe uma deck list no formato textual do PTCG Live, identifica as cartas do deck e classifica cada uma com apoio da API pública do TCGDex. A partir disso, ele gera métricas úteis para montagem e ajuste de listas.

Entre as análises disponíveis:

- probabilidade de mulligan, com base na quantidade de básicos
- chance de abrir com exatamente 1 básico
- chance de abrir com 2 ou mais básicos
- chance de um Pokémon básico específico aparecer na mão inicial
- chance de um básico ser um possível starter
- chance de um básico ser starter forçado
- chance de pelo menos 1 cópia de uma carta estar nos prêmios
- chance de comprar uma carta até determinados turnos
- chance de abrir com Supporter no turno 1
- chance de "dead hand" na mão inicial
- chance de abrir com cartas-alvo e/ou buscadores escolhidos pelo usuário
- comparação entre resultados teóricos e resultados simulados por Monte Carlo

## Interface

A interface principal está em `app.py` e roda com Streamlit.

Na barra lateral, o usuário pode:

- colar uma deck list exportada do PTCG Live
- escolher cartas-alvo entre os Pokémon do deck
- escolher buscadores entre todas as cartas identificadas
- definir o número de simulações Monte Carlo
- definir a seed da simulação

Depois da análise, a aplicação exibe:

- breakdown do deck por categoria e subcategoria
- estatísticas da mão inicial
- tabela de starters por Pokémon básico
- probabilidades de prize cards
- probabilidades de draw por turno
- métricas de Supporter e dead hand
- análise de cartas-alvo e buscadores
- comparação entre cálculo teórico e simulação

## Como funciona internamente

O fluxo principal do projeto é este:

1. O parser lê a deck list em texto no formato do PTCG Live.
2. Cada carta é enriquecida com dados da TCGDex.
3. O projeto classifica as cartas em subcategorias como `basic`, `supporter`, `item`, `basic_energy` e `special_energy`.
4. O módulo de cálculo aplica fórmulas hipergeométricas para probabilidades teóricas.
5. O módulo de Monte Carlo simula milhares de mãos para validar os resultados.
6. O serviço monta tabelas prontas para exibição no Streamlit.

## Estrutura do projeto

```text
.
|-- app.py
|-- simulator.ipynb
|-- card_cache.json
|-- requirements.txt
|-- src/
|   |-- api_client.py
|   |-- calculator.py
|   |-- deck.py
|   |-- monte_carlo.py
|   |-- parser.py
|   |-- set_mapping.py
|   `-- simulator_service.py
`-- tests/
```

### Principais arquivos

- `app.py`: interface web em Streamlit
- `src/parser.py`: parser da deck list exportada do PTCG Live
- `src/api_client.py`: integração com a API TCGDex, cache local e aprendizado de mapeamentos de sets
- `src/deck.py`: modelos `Card` e `Deck`
- `src/calculator.py`: fórmulas de probabilidade
- `src/monte_carlo.py`: simulação empírica de mãos iniciais
- `src/simulator_service.py`: orquestração da análise e geração das tabelas da interface
- `simulator.ipynb`: notebook para exploração e experimentos
- `tests/`: suíte de testes automatizados

## Formato de entrada

O parser espera uma deck list parecida com esta:

```text
Pokémon: 20
4 Abra MEG 54
2 Dunsparce JTG 120

Trainer: 33
4 Ultra Ball SVI 196
4 Iono PAL 269

Energy: 7
7 Psychic Energy SVE 5
```

Cada linha de carta deve conter:

- quantidade
- nome da carta
- código do set
- número da carta no set

O parser aceita cabeçalhos como `Pokémon:`, `Pokemon:`, `Trainer:` e `Energy:`.

## Cache e integração com TCGDex

O projeto usa a API do TCGDex para descobrir a categoria e subcategoria real de cada carta. Para evitar consultas repetidas, os resultados ficam salvos em `card_cache.json`.

Além disso, o projeto mantém um mapeamento entre códigos de set do PTCG Live e IDs da TCGDex em `src/set_mapping.py`. Quando encontra um set ainda não mapeado, ele tenta aprender esse vínculo automaticamente.

Se uma carta não for encontrada:

- ela permanece com subcategoria `unknown`
- a interface mostra um aviso
- o restante da análise continua funcionando

## Requisitos

- Python 3.10 ou superior
- acesso à internet na primeira consulta de cartas que ainda não estejam em cache

Dependências principais:

- `streamlit`
- `pandas`
- `numpy`
- `pytest`

## Como rodar

Instale as dependências:

```bash
pip install -r requirements.txt
```

Inicie a interface:

```bash
streamlit run app.py
```

## Como testar

Para executar a suíte de testes:

```bash
pytest
```

Os testes cobrem:

- parser da deck list
- cálculo de probabilidades
- comportamento do modelo de deck
- integração com cache e API
- simulação de Monte Carlo
- montagem do relatório final

## Exemplos de métricas úteis

Este projeto ajuda a responder perguntas como:

- quantos básicos meu deck precisa para reduzir mulligan?
- qual a chance de abrir com um starter específico?
- qual a chance de uma tech de 1 cópia cair nos prêmios?
- até que turno eu costumo ver determinada carta?
- meus buscadores realmente aumentam a consistência da carta-alvo?
- a simulação bate com os cálculos teóricos?

## Limitações atuais

- a análise depende da classificação correta da TCGDex
- cartas não encontradas podem afetar parte das métricas
- a interface é focada principalmente em estatísticas de mão inicial e consistência
- o notebook e a interface podem ter sobreposição de uso, mas a aplicação principal hoje é o Streamlit

## Próximos passos possíveis

- exportar relatórios em CSV ou Excel
- gráficos para comparar builds diferentes
- filtros por tipo de carta ou engine do deck
- simulações mais avançadas com regras específicas de busca e draw
- comparação entre múltiplas listas lado a lado

## Resumo

Este repositório é um simulador de consistência para decks de Pokémon TCG. Ele transforma uma deck list textual em métricas práticas para deckbuilding, usando matemática combinatória, simulação e uma interface web simples para apoiar testes e decisões de construção de deck.
