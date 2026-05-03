"""Streamlit frontend for the Pokémon TCG Simulator."""

from __future__ import annotations

import streamlit as st

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

    target_input = st.text_input(
        "Cartas Alvo (separadas por vírgula)",
        value="Riolu",
        help="Cartas que você quer ter na mão inicial. Ex: Riolu, Mega Lucario ex",
    )
    target_card_names = [n.strip() for n in target_input.split(",") if n.strip()]

    search_input = st.text_input(
        "Buscadores (separados por vírgula)",
        value="Ultra Ball,Buddy-Buddy Poffin,Poké Pad",
        help="Cartas que buscam os alvos. Ex: Ultra Ball, Buddy-Buddy Poffin",
    )
    target_search_names = [n.strip() for n in search_input.split(",") if n.strip()]

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
