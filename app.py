from __future__ import annotations

import streamlit as st

from src.parser import parse_deck_list
from src.simulator_service import SAMPLE_DECK_LIST, build_deck, build_report


st.set_page_config(
    page_title="Pokemon TCG Simulator",
    page_icon="🃏",
    layout="wide",
)

st.markdown(
    """
    <style>
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(255, 204, 112, 0.22), transparent 30%),
            radial-gradient(circle at top right, rgba(98, 182, 255, 0.18), transparent 28%),
            linear-gradient(180deg, #f8f4ea 0%, #efe4cf 100%);
    }
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
        max-width: 1380px;
    }
    .hero {
        padding: 1.5rem 1.6rem;
        border-radius: 24px;
        background: linear-gradient(135deg, rgba(27, 47, 66, 0.95), rgba(163, 91, 44, 0.92));
        color: #fff6df;
        border: 1px solid rgba(255, 246, 223, 0.14);
        box-shadow: 0 18px 40px rgba(27, 47, 66, 0.16);
        margin-bottom: 1rem;
    }
    .hero h1 {
        margin: 0 0 0.35rem 0;
        font-size: 2.2rem;
        letter-spacing: -0.03em;
    }
    .hero p {
        margin: 0;
        font-size: 1rem;
        color: rgba(255, 246, 223, 0.86);
    }
    .panel {
        background: rgba(255, 250, 241, 0.72);
        border: 1px solid rgba(27, 47, 66, 0.08);
        border-radius: 20px;
        padding: 1rem 1.1rem;
        box-shadow: 0 10px 24px rgba(27, 47, 66, 0.06);
    }
    .kpi {
        background: rgba(255, 250, 241, 0.78);
        border: 1px solid rgba(27, 47, 66, 0.08);
        border-radius: 18px;
        padding: 0.9rem 1rem;
        box-shadow: 0 10px 24px rgba(27, 47, 66, 0.06);
    }
    .kpi-label {
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #6c6356;
    }
    .kpi-value {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1b2f42;
        margin-top: 0.2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "deck_list_text" not in st.session_state:
    st.session_state.deck_list_text = SAMPLE_DECK_LIST

st.markdown(
    """
    <div class="hero">
        <h1>Pokemon TCG Simulator</h1>
        <p>Analise opening hand, starters, prizes, draw curve e target searches usando a mesma engine do notebook atual.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Deck")
    if st.button("Carregar Exemplo", use_container_width=True):
        st.session_state.deck_list_text = SAMPLE_DECK_LIST

    deck_list_text = st.text_area(
        "Deck list",
        value=st.session_state.deck_list_text,
        height=420,
        help="Cole a lista no formato do PTCG Live.",
    )
    st.session_state.deck_list_text = deck_list_text

    try:
        parsed_cards = parse_deck_list(deck_list_text)
    except Exception:
        parsed_cards = []

    available_names = sorted({card["name"] for card in parsed_cards})
    default_target = "Abra" if "Abra" in available_names else (available_names[0] if available_names else "")
    default_searches = [
        name for name in ["Buddy-Buddy Poffin", "Poké Pad"] if name in available_names
    ]

    st.header("Target")
    target_card_name = st.selectbox(
        "Target card",
        options=available_names or [""],
        index=(available_names.index(default_target) if default_target in available_names else 0),
    )
    target_search_names = st.multiselect(
        "Search cards for the target",
        options=available_names,
        default=default_searches,
    )

    st.header("Monte Carlo")
    run_monte_carlo = st.toggle("Executar validação", value=True)
    mc_simulations = st.slider("Simulações", 10_000, 200_000, 100_000, step=10_000)
    mc_seed = st.number_input("Seed", min_value=0, value=42, step=1)

    run_analysis = st.button("Rodar Simulador", type="primary", use_container_width=True)


def render_kpi(label: str, value: str) -> None:
    st.markdown(
        f"""
        <div class="kpi">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


if run_analysis:
    if not parsed_cards:
        st.error("A deck list está vazia ou não pôde ser interpretada.")
    elif not target_card_name:
        st.error("Selecione uma target card para rodar a análise.")
    else:
        try:
            with st.spinner("Processando deck e gerando estatísticas..."):
                deck, unknown_cards = build_deck(deck_list_text)
                report = build_report(
                    deck=deck,
                    target_card_name=target_card_name,
                    target_search_names=target_search_names,
                    mc_simulations=mc_simulations if run_monte_carlo else 0,
                    mc_seed=int(mc_seed),
                )
        except Exception as exc:
            st.error(f"Não foi possível gerar a análise: {exc}")
        else:
            if unknown_cards:
                st.warning(
                    "Algumas cartas não foram classificadas pela API: "
                    + ", ".join(unknown_cards)
                )

            kpi_1, kpi_2, kpi_3, kpi_4 = st.columns(4)
            with kpi_1:
                render_kpi("Total Cards", str(deck.total_cards))
            with kpi_2:
                render_kpi("Basic Pokemon", str(deck.total_basics))
            with kpi_3:
                render_kpi(
                    "Target Copies",
                    str(sum(card.quantity for card in deck.cards if card.name == target_card_name)),
                )
            with kpi_4:
                render_kpi(
                    "Target Searches",
                    str(sum(card.quantity for card in deck.cards if card.name in set(target_search_names))),
                )

            top_left, top_right = st.columns([1.15, 1])
            with top_left:
                st.markdown('<div class="panel">', unsafe_allow_html=True)
                st.subheader("Opening Hand")
                st.dataframe(report.opening_df, use_container_width=True, hide_index=True)
                st.subheader("Supporters and Dead Hand")
                st.dataframe(report.support_df, use_container_width=True, hide_index=True)
                st.subheader("Target Card + Searches")
                st.dataframe(report.target_df, use_container_width=True, hide_index=True)
                st.markdown("</div>", unsafe_allow_html=True)
            with top_right:
                st.markdown('<div class="panel">', unsafe_allow_html=True)
                st.subheader("Deck Breakdown")
                st.dataframe(report.breakdown_df, use_container_width=True, hide_index=True)
                st.markdown("</div>", unsafe_allow_html=True)

            tab1, tab2, tab3, tab4 = st.tabs(
                ["Starters", "Prize Map", "Draw Curve", "Monte Carlo"]
            )

            with tab1:
                st.dataframe(report.starters_df, use_container_width=True, hide_index=True)

            with tab2:
                st.dataframe(report.prizes_df, use_container_width=True, hide_index=True)

            with tab3:
                draw_filter = st.text_input("Filtrar cartas", value="", key="draw_filter")
                draw_df = report.draw_df
                if draw_filter:
                    draw_df = draw_df[
                        draw_df["Card"].str.contains(draw_filter, case=False, na=False)
                    ]
                st.dataframe(draw_df, use_container_width=True, hide_index=True)

            with tab4:
                if report.comparison_df is None:
                    st.info("Ative a validação Monte Carlo na barra lateral para comparar teoria e simulação.")
                else:
                    st.dataframe(report.comparison_df, use_container_width=True, hide_index=True)
else:
    st.info("Ajuste a deck list e clique em `Rodar Simulador` para montar a interface do deck.")
