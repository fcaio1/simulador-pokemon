# Design: Multiselect Selectors para Cartas Alvo e Buscadores

**Data:** 2026-05-03  
**Arquivo afetado:** `app.py`

## Contexto

O frontend atual usa `st.text_input` para "Cartas Alvo" e "Buscadores", exigindo que o usuário digite nomes manualmente. O objetivo é substituir por `st.multiselect` populado com as cartas do deck list colado.

## Solução

### Parse leve no sidebar

Após o `text_area` do deck list, chamar `parse_deck_list()` (sem API, ~1ms) para extrair nomes únicos das cartas. Isso não bloqueia a UI e não faz chamadas de rede.

```python
from src.parser import parse_deck_list

try:
    _parsed = parse_deck_list(deck_list_text)
except Exception:
    _parsed = []

_all_names = sorted({c["name"] for c in _parsed})
_pokemon_names = sorted({c["name"] for c in _parsed if c["category"] == "pokemon"})
```

### Session state — inicialização e filtragem

Antes de cada `st.multiselect`, o session state é inicializado (primeira execução) ou filtrado (deck mudou):

- **Cartas Alvo** — pré-seleção: todos os Pokémon do deck (category == "pokemon")
- **Buscadores** — sem pré-seleção (lista vazia)

Se o usuário trocar o deck list, seleções que não existem no novo deck são removidas automaticamente.

### Widgets

```python
target_card_names = st.multiselect(
    "Cartas Alvo",
    options=_all_names,
    key="target_cards_sel",
    help="Cartas que você quer ter na mão inicial.",
)

target_search_names = st.multiselect(
    "Buscadores",
    options=_all_names,
    key="search_cards_sel",
    help="Cartas que buscam os alvos.",
)
```

## Comportamento esperado

| Situação | Cartas Alvo | Buscadores |
|---|---|---|
| Primeira carga (sample deck) | Pokémon do sample deck pré-selecionados | Vazio |
| Usuário cola deck novo | Seleções anteriores inválidas removidas; Pokémon novo pré-selecionados | Seleções anteriores inválidas removidas |
| Usuário clica ANALISAR sem selecionar buscadores | `target_search_names = []` — cálculo roda sem buscadores |  |

## O que NÃO muda

- Lógica de `build_deck` e `build_report` — recebem `list[str]` igual antes
- Fluxo de análise (botão ANALISAR DECK)
- Nenhum outro arquivo além de `app.py`

## Dependências

- `src.parser.parse_deck_list` — já existe, sem mudança
