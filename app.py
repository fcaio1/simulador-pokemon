"""Streamlit frontend for the Pokémon TCG Simulator."""

from __future__ import annotations

import math
import streamlit as st
import streamlit.components.v1 as components

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
        st.session_state["target_cards_sel"] = []
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

# 0. Deck List Visual
with st.expander("🃏 Deck List", expanded=True):
    _category_order = {"pokemon": 0, "trainer": 1, "energy": 2}
    _ordered_cards = sorted(
        deck.cards,
        key=lambda c: (_category_order.get(c.category, 3), c.name),
    )
    _badge = (
        'position:absolute;bottom:4px;left:4px;background:#e53935;color:white;'
        'border-radius:50%;width:22px;height:22px;font-size:13px;font-weight:bold;'
        'display:flex;align-items:center;justify-content:center;'
    )
    _cards_html = ""
    for _card in _ordered_cards:
        if _card.image:
            _cards_html += (
                f'<div class="ptcg-card" data-img="{_card.image}" onclick="openPtcgModal(\'{_card.image}\')">'
                f'<img src="{_card.image}" width="90" style="border-radius:6px;display:block;" title="{_card.name}"/>'
                f'<span style="{_badge}">{_card.quantity}</span>'
                f'</div>'
            )
        else:
            _cards_html += (
                f'<div class="ptcg-card" style="width:90px;height:126px;background:#333;'
                f'border-radius:6px;color:white;font-size:10px;text-align:center;'
                f'padding-top:50px;box-sizing:border-box;">'
                f'{_card.name[:14]}'
                f'<span style="{_badge}">{_card.quantity}</span>'
                f'</div>'
            )
    _rows = math.ceil(len(_ordered_cards) / 9)
    _height = max(180, _rows * 145 + 20)
    components.html(
        f"""
        <style>
        body {{ margin: 0; }}
        .ptcg-card {{
            position: relative;
            display: inline-block;
            margin: 4px;
            cursor: pointer;
            transition: opacity 0.15s;
        }}
        .ptcg-card:hover {{ opacity: 0.85; }}
        </style>
        <div style="display:flex;flex-wrap:wrap;gap:2px;">{_cards_html}</div>
        <script>
        document.querySelectorAll('.ptcg-card[data-img]').forEach(function(card) {{
            card.addEventListener('mouseenter', function() {{
                var p = window.parent.document;
                var preview = p.getElementById('ptcg-hover');
                if (!preview) {{
                    preview = p.createElement('div');
                    preview.id = 'ptcg-hover';
                    preview.style.cssText = 'position:fixed;z-index:9998;pointer-events:none;'
                        + 'transition:opacity 0.15s;border-radius:12px;'
                        + 'box-shadow:0 8px 32px rgba(0,0,0,0.7);';
                    preview.innerHTML = '<img id="ptcg-hover-img" style="width:180px;border-radius:12px;display:block;"/>';
                    p.body.appendChild(preview);
                }}
                var iframe = window.frameElement;
                var ir = iframe.getBoundingClientRect();
                var cr = this.getBoundingClientRect();
                var cx = ir.left + cr.left + cr.width  / 2;
                var cy = ir.top  + cr.top  + cr.height / 2;
                var pw = 180, ph = 252;
                var vw = window.parent.innerWidth, vh = window.parent.innerHeight;
                var left = Math.max(8, Math.min(cx - pw / 2, vw - pw - 8));
                var top  = Math.max(8, Math.min(cy - ph / 2, vh - ph - 8));
                preview.style.left = left + 'px';
                preview.style.top  = top  + 'px';
                p.getElementById('ptcg-hover-img').src = this.dataset.img;
                preview.style.display = 'block';
            }});
            card.addEventListener('mouseleave', function() {{
                var preview = window.parent.document.getElementById('ptcg-hover');
                if (preview) preview.style.display = 'none';
            }});
        }});

        // Injeta closePtcgModal no <head> do documento pai (executa no contexto pai,
        // então `document` dentro dela é o documento do Streamlit, não do iframe)
        (function() {{
            var p = window.parent.document;
            if (p.getElementById('ptcg-modal-script')) return;
            var sc = p.createElement('script');
            sc.id = 'ptcg-modal-script';
            sc.textContent =
                'function closePtcgModal() {{' +
                '  var m = document.getElementById("ptcg-modal");' +
                '  if (m) m.style.display = "none";' +
                '}}' +
                'document.addEventListener("keydown", function(e) {{' +
                '  if (e.key === "Escape") closePtcgModal();' +
                '}});';
            p.head.appendChild(sc);
        }})();

        function openPtcgModal(src) {{
            var p = window.parent.document;
            var modal = p.getElementById('ptcg-modal');
            if (!modal) {{
                modal = p.createElement('div');
                modal.id = 'ptcg-modal';
                modal.setAttribute('onclick', "if(event.target===this)closePtcgModal()");
                modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;'
                    + 'background:rgba(0,0,0,0.88);z-index:99999;display:flex;'
                    + 'align-items:center;justify-content:center;';
                modal.innerHTML =
                    '<button onclick="closePtcgModal()" style="position:fixed;top:18px;right:26px;'
                    + 'background:none;border:none;font-size:42px;color:white;cursor:pointer;'
                    + 'font-weight:bold;line-height:1;z-index:100000;">&#x2715;</button>'
                    + '<img id="ptcg-modal-img" style="max-height:88vh;max-width:88vw;'
                    + 'border-radius:16px;box-shadow:0 0 80px rgba(0,0,0,0.9);"/>';
                p.body.appendChild(modal);
            }}
            p.getElementById('ptcg-modal-img').src = src;
            modal.style.display = 'flex';
        }}
        </script>
        """,
        height=_height,
    )

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
