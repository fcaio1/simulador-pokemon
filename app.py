"""Streamlit frontend for the Pokémon TCG Simulator."""

from __future__ import annotations

import streamlit as st

from src.parser import parse_deck_list
from src.simulator_service import SAMPLE_DECK_LIST, build_deck, build_report

st.set_page_config(
    page_title="Pokémon TCG Simulator",
    page_icon="🎴",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Sidebar — inputs
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## 🎴 TCG Simulator")

    deck_list_text = st.text_area(
        "Deck List (PTCG Live)",
        value=SAMPLE_DECK_LIST,
        height=220,
        help="Cole aqui o texto exportado do PTCG Live.",
    )

    st.divider()

    try:
        _parsed = parse_deck_list(deck_list_text)
    except Exception:
        _parsed = []

    _all_names = sorted({c["name"] for c in _parsed})
    _pokemon_names = sorted({c["name"] for c in _parsed if c["category"] == "pokemon"})

    if "target_cards_sel" not in st.session_state:
        st.session_state["target_cards_sel"] = _pokemon_names
    else:
        st.session_state["target_cards_sel"] = [
            n for n in st.session_state["target_cards_sel"] if n in _pokemon_names
        ]

    if "search_cards_sel" not in st.session_state:
        st.session_state["search_cards_sel"] = []
    else:
        st.session_state["search_cards_sel"] = [
            n for n in st.session_state["search_cards_sel"] if n in _all_names
        ]

    target_card_names = st.multiselect(
        "Cartas Alvo",
        options=_pokemon_names,
        key="target_cards_sel",
        help="Cartas que você quer ter na mão inicial.",
    )

    target_search_names = st.multiselect(
        "Buscadores",
        options=_all_names,
        key="search_cards_sel",
        help="Cartas que buscam os alvos. Ex: Ultra Ball, Buddy-Buddy Poffin",
    )

    st.divider()

    mc_simulations = st.number_input(
        "Simulações Monte Carlo",
        min_value=0,
        max_value=1_000_000,
        value=100_000,
        step=10_000,
    )
    mc_seed = st.number_input("Seed", min_value=0, value=42)

    st.divider()

    analyze_clicked = st.button(
        "▶ ANALISAR DECK",
        use_container_width=True,
        type="primary",
    )
    st.caption("cache: card_cache.json · TCGDex API")

# ---------------------------------------------------------------------------
# Análise — executar e armazenar em session_state
# ---------------------------------------------------------------------------

if analyze_clicked:
    with st.spinner("Analisando deck..."):
        try:
            deck, unknown = build_deck(deck_list_text)
            report = build_report(
                deck=deck,
                target_card_names=target_card_names,
                target_search_names=target_search_names,
                mc_simulations=int(mc_simulations),
                mc_seed=int(mc_seed),
            )
            st.session_state["report"] = report
            st.session_state["unknown"] = unknown
        except Exception as exc:
            st.error(f"Erro ao analisar deck: {exc}")
            st.stop()

if "report" not in st.session_state:
    st.info("Cole sua deck list na sidebar e clique em **▶ ANALISAR DECK** para começar.")
    st.stop()

report = st.session_state["report"]
unknown = st.session_state["unknown"]

# ---------------------------------------------------------------------------
# Alertas
# ---------------------------------------------------------------------------

if unknown:
    st.warning(
        f"⚠️ {len(unknown)} carta(s) não encontrada(s) na API TCGDex: "
        + ", ".join(unknown)
    )

# ---------------------------------------------------------------------------
# Métricas rápidas
# ---------------------------------------------------------------------------

deck = report.deck
deck_size = deck.total_cards
total_basics = deck.total_basics

_opening = report.opening_df
mulligan_pct = _opening.loc[_opening["Event"].str.contains("Mulligan"), "Probability"].values[0]
supporter_pct = report.support_df.iloc[0]["Probability"]
dead_hand_pct = report.support_df.iloc[1]["Probability"]
ok_count = deck_size - len(unknown)

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total de Cartas", deck_size)
col2.metric("Mulligan", mulligan_pct)
col3.metric("Supporter T1", supporter_pct)
col4.metric("Dead Hand", dead_hand_pct)
col5.metric("Cartas OK", f"{ok_count}/{deck_size}")

# ---------------------------------------------------------------------------
# Seções de resultado
# ---------------------------------------------------------------------------

st.divider()

# 1. Breakdown do Deck
with st.expander("📋 Breakdown do Deck", expanded=True):
    st.dataframe(report.breakdown_df, use_container_width=True, hide_index=True)

# 2. Mão Inicial
with st.expander("✋ Mão Inicial", expanded=True):
    st.dataframe(report.opening_df, use_container_width=True, hide_index=True)

# 3. Starters por Pokémon
with st.expander("🎯 Starters por Pokémon", expanded=True):
    df_starters = report.starters_df.copy()
    st.dataframe(df_starters, use_container_width=True, hide_index=True)

# 4. Prize Cards
with st.expander("🏆 Prize Cards", expanded=True):
    st.dataframe(report.prizes_df, use_container_width=True, hide_index=True)

# 5. Draw por Turno
with st.expander("🃏 Draw por Turno", expanded=True):
    st.dataframe(report.draw_df, use_container_width=True, hide_index=True)

# 6. Supporter & Dead Hand
with st.expander("💼 Supporter & Dead Hand", expanded=True):
    st.dataframe(report.support_df, use_container_width=True, hide_index=True)

# 7. Carta Alvo + Buscadores
with st.expander("🔍 Carta Alvo + Buscadores", expanded=True):
    st.dataframe(report.target_df, use_container_width=True, hide_index=True)

# 8. Monte Carlo
if report.comparison_df is not None:
    with st.expander(f"🎲 Monte Carlo ({int(mc_simulations):,} simulações)", expanded=True):
        st.dataframe(report.comparison_df, use_container_width=True, hide_index=True)

# ---------------------------------------------------------------------------
# Status bar
# ---------------------------------------------------------------------------

st.divider()
cache_info = "cache: card_cache.json"
mc_info = f"Monte Carlo: {int(mc_simulations):,} sims · seed {int(mc_seed)}"
ok_info = f"✅ {ok_count}/{deck_size} cartas classificadas"

st.caption(f"{ok_info} · {cache_info} · {mc_info}")
