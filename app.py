"""Streamlit frontend — Pokémon TCG Simulator · Consistency Lab theme."""

from __future__ import annotations

import html as _html
import json
import math
import streamlit as st
import streamlit.components.v1 as components

from src.api_client import _load_cache, _save_cache
from src.parser import parse_deck_list
from src.simulator_service import SAMPLE_DECK_LIST, build_deck, build_report


# ─── Card correction helpers ──────────────────────────────────────────────────

_SUB_TO_API: dict[str, dict] = {
    "basic":          {"stage": "Basic"},
    "stage_1":        {"stage": "Stage1"},
    "stage_2":        {"stage": "Stage2"},
    "other":          {"stage": ""},
    "item":           {"trainerType": "Item"},
    "supporter":      {"trainerType": "Supporter"},
    "stadium":        {"trainerType": "Stadium"},
    "tool":           {"trainerType": "Tool"},
    "basic_energy":   {},
    "special_energy": {"energyType": "Special"},
}

_CAT_TO_API = {"pokemon": "Pokemon", "trainer": "Trainer", "energy": "Energy"}


def _apply_card_correction(correction: dict, cache_path: str = "card_cache.json") -> None:
    """Apply a manual correction dict to card_cache.json."""
    set_code = correction.get("set_code", "").upper()
    set_number = correction.get("set_number", "")
    if not set_code or not set_number:
        return

    cache_key = f"{set_code}-{set_number}"
    cache = _load_cache(cache_path)
    entry = cache.get(cache_key, {})

    if correction.get("name"):
        entry["name"] = correction["name"]

    cat = correction.get("category", "")
    if cat in _CAT_TO_API:
        entry["category"] = _CAT_TO_API[cat]

    sub = correction.get("subcategory", "")
    if sub in _SUB_TO_API:
        # Remove all subcategory-related fields first
        for field in ("stage", "trainerType", "energyType"):
            entry.pop(field, None)
        entry.update(_SUB_TO_API[sub])

    cache[cache_key] = entry
    _save_cache(cache, cache_path)


def _update_deck_cards(deck, correction: dict) -> None:
    """Patch in-memory deck cards to match a correction immediately."""
    from src.api_client import _map_subcategory

    set_code = correction.get("set_code", "").upper()
    set_number = correction.get("set_number", "")

    for card in deck.cards:
        if card.set_code.upper() == set_code and card.set_number == set_number:
            if correction.get("name"):
                card.name = correction["name"]
            if correction.get("category"):
                card.category = correction["category"]
            if correction.get("subcategory"):
                card.subcategory = correction["subcategory"]

# ─── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Consistency Lab · Pokémon TCG",
    page_icon="🎴",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Global CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
:root {
    --bg: #0d0e10;
    --s1: #131418;
    --s2: #1c1f26;
    --border: rgba(255,255,255,0.07);
    --border2: rgba(255,255,255,0.13);
    --accent: #ffd740;
    --good: #06d6a0;
    --warn: #ffb454;
    --bad:  #e63946;
    --text: #e8eaf0;
    --muted: #9aa0ad;
    --faint: #5e6371;
    --mono: 'JetBrains Mono', ui-monospace, monospace;
}

#MainMenu, footer { visibility: hidden; }
.stDeployButton { display: none; }
[data-testid="stHeaderActionElements"] { display: none; }
header[data-testid="stHeader"] {
    background: var(--bg) !important;
    border-bottom: 1px solid var(--border) !important;
}
.stApp,
[data-testid="stAppViewContainer"],
[data-testid="block-container"] { background: var(--bg) !important; }

[data-testid="stSidebar"] {
    background: var(--s1) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] hr { border-color: var(--border) !important; }
[data-testid="stSidebar"] .stTextArea textarea {
    font-family: var(--mono) !important;
    font-size: 12px !important;
    line-height: 1.6 !important;
    color: var(--muted) !important;
    background: var(--bg) !important;
    border-color: var(--border) !important;
}
[data-testid="stSidebar"] .stTextArea textarea:focus {
    border-color: var(--accent) !important;
}
[data-testid="stSidebar"] .stMultiSelect [data-baseweb="tag"] {
    background: rgba(255,215,64,.15) !important;
    color: var(--accent) !important;
}

/* ── Sidebar tabs ── */
[data-testid="stSidebar"] [data-testid="stTabsListContainer"] {
    background: var(--bg) !important;
    border-bottom: 1px solid var(--border) !important;
    gap: 0 !important;
    margin: 0 -1rem !important;
    padding: 0 !important;
}
[data-testid="stSidebar"] [data-testid="stTab"] {
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: .05em !important;
    text-transform: uppercase !important;
    color: var(--faint) !important;
    border-radius: 0 !important;
    flex: 1 !important;
    padding: 10px 0 !important;
    border-bottom: 2px solid transparent !important;
    background: none !important;
    transition: color .12s !important;
}
[data-testid="stSidebar"] [data-testid="stTab"]:hover {
    color: var(--muted) !important;
}
[data-testid="stSidebar"] [data-testid="stTab"][aria-selected="true"] {
    color: var(--text) !important;
    border-bottom-color: var(--accent) !important;
}
[data-testid="stSidebar"] [data-testid="stTabsContent"] {
    padding-top: 4px !important;
}

/* ── Sidebar rail brand ── */
.rail-brand {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 2px 0 14px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 4px;
}
.rail-brand-title {
    font-weight: 700;
    font-size: 15px;
    color: var(--text);
    letter-spacing: -.01em;
    line-height: 1.2;
}
.rail-brand-sub {
    font-size: 11px;
    color: var(--muted);
    margin-top: 2px;
}

/* ── Field labels ── */
.fl {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: .08em;
    color: var(--muted);
    margin: 14px 0 6px;
    display: flex;
    align-items: center;
    gap: 8px;
}
.fl.fl-top { margin-top: 6px; }
.fl .flc {
    background: var(--accent);
    color: #1a1a1a;
    font-size: 10px;
    padding: 1px 6px;
    border-radius: 999px;
    font-family: var(--mono);
}

/* ── Textarea meter ── */
.tx-meter {
    display: flex;
    justify-content: space-between;
    font-family: var(--mono);
    font-size: 11px;
    color: var(--muted);
    margin-top: 4px;
}
.tx-meter .ok  { color: var(--good); }
.tx-meter .wn  { color: var(--warn); }
.tx-meter .er  { color: var(--bad);  }

/* ── Rail footer meta ── */
.rail-meta {
    font-size: 10px;
    color: rgba(154,160,173,.45);
    text-align: center;
    margin-top: 7px;
}

/* ── Pills (st.pills widget) ── */
[data-testid="stSidebar"] [data-testid="stPills"] > div {
    display: flex !important;
    flex-wrap: wrap !important;
    gap: 6px !important;
    margin: 0 !important;
}
[data-testid="stSidebar"] [data-testid="stPills"] button {
    display: inline-flex !important;
    align-items: center !important;
    gap: 4px !important;
    padding: 5px 10px !important;
    background: var(--s2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 999px !important;
    color: var(--muted) !important;
    font-size: 12px !important;
    font-family: inherit !important;
    cursor: pointer !important;
    transition: all .1s !important;
    height: auto !important;
    line-height: 1.4 !important;
    min-height: 0 !important;
}
[data-testid="stSidebar"] [data-testid="stPills"] button:hover {
    border-color: var(--border2) !important;
    color: var(--text) !important;
}
[data-testid="stSidebar"] [data-testid="stPills"] button[aria-pressed="true"] {
    background: var(--accent) !important;
    border-color: var(--accent) !important;
    color: #1a1a1a !important;
    font-weight: 600 !important;
}

/* ── Caption hint text in sidebar ── */
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: var(--faint) !important;
    font-size: 11px !important;
    margin-top: 0 !important;
    margin-bottom: 4px !important;
    line-height: 1.5 !important;
}

button[kind="primary"] {
    background: var(--accent) !important;
    color: #0d0e10 !important;
    border: none !important;
    font-weight: 700 !important;
}
button[kind="primary"]:hover { opacity: .88 !important; }

.stExpander {
    background: var(--s1) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    overflow: visible !important;
    margin-bottom: 12px !important;
}
/* Round the summary itself so hover-bg respects the corners */
.stExpander > details > summary {
    font-size: 14px !important;
    font-weight: 600 !important;
    padding: 13px 18px !important;
    color: var(--text) !important;
    border-radius: 10px !important;
}
.stExpander > details[open] > summary {
    border-radius: 10px 10px 0 0 !important;
    border-bottom: 1px solid var(--border) !important;
}
.stExpander > details > summary:hover { background: var(--s2) !important; }
[data-testid="stExpanderDetails"] {
    padding: 16px 18px !important;
    border-radius: 0 0 10px 10px !important;
    overflow: hidden;
}

hr { border-color: var(--border) !important; }

::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,.1); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,.2); }
</style>
""", unsafe_allow_html=True)

# ─── Component CSS ────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── KPI row ── */
.cl-kpi-row { display:flex; gap:10px; flex-wrap:wrap; margin-bottom:20px; }
.cl-kpi {
    background:var(--s1); border:1px solid var(--border); border-radius:10px;
    padding:14px 18px; flex:1; min-width:90px;
}
.cl-kpi-val {
    font-size:24px; font-weight:700; font-family:var(--mono);
    line-height:1.1; color:var(--text);
}
.cl-kpi-val.accent { color:var(--accent); }
.cl-kpi-val.good   { color:var(--good);   }
.cl-kpi-val.warn   { color:var(--warn);   }
.cl-kpi-val.bad    { color:var(--bad);    }
.cl-kpi-label { font-size:11px; color:var(--muted); text-transform:uppercase; letter-spacing:.8px; margin-top:4px; }
.cl-kpi-sub   { font-size:11px; color:var(--muted); margin-top:2px; }

/* ── Section title ── */
.cl-sec {
    font-size:13px; font-weight:600; color:var(--text);
    text-transform:uppercase; letter-spacing:.6px;
    margin-bottom:14px; padding-bottom:8px;
    border-bottom:1px solid var(--border);
    display:flex; justify-content:space-between; align-items:center;
}
.cl-sec-count { color:var(--muted); font-weight:400; font-size:12px; }

/* ── Probability bar row ── */
.cl-prob-row { display:flex; align-items:center; gap:10px; margin-bottom:9px; }
.cl-prob-label { font-size:13px; color:var(--text); flex:1.8; }
.cl-prob-track { flex:2; height:8px; background:var(--s2); border-radius:4px; overflow:hidden; }
.cl-prob-fill  { height:8px; border-radius:4px; background:var(--accent); }
.cl-prob-val   { font-size:13px; font-family:var(--mono); color:var(--text); width:52px; text-align:right; }

/* ── Breakdown rows ── */
.cl-bd-row {
    display:flex; align-items:center; gap:10px; padding:5px 0;
    border-bottom:1px solid var(--border); font-size:13px;
}
.cl-bd-row:last-child { border-bottom:none; }
.cl-bd-cat  { width:70px;  color:var(--muted); }
.cl-bd-sub  { width:90px;  color:var(--text);  }
.cl-bd-n    { width:28px;  text-align:right; font-family:var(--mono); color:var(--text); }
.cl-bd-track{ flex:1; height:6px; background:var(--s2); border-radius:3px; overflow:hidden; }
.cl-bd-fill { height:6px; border-radius:3px; }
.cl-bd-pct  { width:38px; text-align:right; color:var(--muted); font-family:var(--mono); font-size:12px; }

/* ── Starter rows ── */
.cl-starter-row {
    display:flex; align-items:center; gap:12px;
    padding:8px 0; border-bottom:1px solid var(--border);
}
.cl-starter-row:last-child { border-bottom:none; }
.cl-starter-thumb { width:48px; flex-shrink:0; }
.cl-starter-thumb img  { width:48px; border-radius:5px; display:block; }
.cl-starter-ph {
    width:48px; height:67px; border-radius:5px;
    background:var(--s2); border:1px solid var(--border);
    display:flex; align-items:center; justify-content:center;
    font-size:9px; color:var(--muted); text-align:center; line-height:1.3;
}
.cl-starter-name   { flex:1.5; }
.cl-starter-title  { font-size:13px; font-weight:600; color:var(--text); }
.cl-starter-set    { font-size:11px; color:var(--muted); margin-top:1px; }
.cl-starter-copies { width:40px; text-align:center; }
.cl-qty-chip {
    display:inline-block;
    background:rgba(255,215,64,.12); color:var(--accent);
    font-size:12px; font-family:var(--mono); border-radius:4px; padding:1px 6px;
}
.cl-bar-col { flex:1.5; }
.cl-bar-col-lbl { font-size:10px; color:var(--muted); margin-bottom:3px; text-transform:uppercase; letter-spacing:.5px; }
.cl-mini-track { height:6px; background:var(--s2); border-radius:3px; overflow:hidden; margin-bottom:2px; }
.cl-mini-fill  { height:6px; border-radius:3px; }
.cl-bar-val    { font-size:12px; font-family:var(--mono); color:var(--text); }

/* ── Prize rows ── */
.cl-prize-row {
    display:flex; align-items:center; gap:10px;
    padding:7px 0; border-bottom:1px solid var(--border);
}
.cl-prize-row:last-child { border-bottom:none; }
.cl-prize-thumb { width:40px; flex-shrink:0; }
.cl-prize-thumb img { width:40px; border-radius:4px; display:block; }
.cl-prize-ph {
    width:40px; height:56px; border-radius:4px; background:var(--s2);
    display:flex; align-items:center; justify-content:center;
    font-size:8px; color:var(--muted);
}
.cl-prize-name  { flex:1.5; }
.cl-prize-title { font-size:13px; color:var(--text); font-weight:500; }
.cl-prize-copies{ font-size:11px; color:var(--muted); }
.cl-prize-bar   { flex:2; }
.cl-prize-track { height:8px; background:var(--s2); border-radius:4px; overflow:hidden; }
.cl-prize-fill  { height:8px; border-radius:4px; }
.cl-prize-val   { width:52px; text-align:right; font-family:var(--mono); font-size:13px; color:var(--text); }

/* ── Draw heatmap ── */
.cl-heat { width:100%; border-collapse:collapse; font-size:13px; }
.cl-heat th {
    color:var(--muted); font-size:10px; text-transform:uppercase;
    letter-spacing:.6px; padding:4px 6px; border-bottom:1px solid var(--border);
    font-weight:500;
}
.cl-heat th.l { text-align:left; }
.cl-heat th.c { text-align:center; }
.cl-heat td   { padding:5px 6px; border-bottom:1px solid var(--border); }
.cl-heat td.name { color:var(--text); max-width:160px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
.cl-heat td.cp   { text-align:center; }
.cl-heat tr:last-child td { border-bottom:none; }
.cl-hcell { border-radius:4px; font-family:var(--mono); font-size:12px; font-weight:600; text-align:center; padding:3px 0; }

/* ── MC table ── */
.cl-mc { width:100%; border-collapse:collapse; font-size:13px; }
.cl-mc th {
    color:var(--muted); font-size:10px; text-transform:uppercase;
    letter-spacing:.6px; padding:4px 8px; border-bottom:1px solid var(--border);
    font-weight:500; text-align:left;
}
.cl-mc th.r { text-align:right; }
.cl-mc td   { padding:7px 8px; border-bottom:1px solid var(--border); color:var(--text); }
.cl-mc td.mono { font-family:var(--mono); text-align:right; }
.cl-mc td.ok   { font-family:var(--mono); text-align:right; color:var(--good); }
.cl-mc td.warn { font-family:var(--mono); text-align:right; color:var(--warn); }
.cl-mc tr:last-child td { border-bottom:none; }
.cl-mc-vis { position:relative; height:8px; background:var(--s2); border-radius:4px; overflow:visible; min-width:80px; }
.cl-mc-bar { position:absolute; left:0; top:0; bottom:0; border-radius:4px; background:rgba(255,215,64,.3); }
.cl-mc-pin { position:absolute; top:-2px; width:2px; height:12px; background:var(--accent); border-radius:1px; transform:translateX(-1px); }

/* ── Supporter highlight cards ── */
.cl-supp-cards { display:flex; gap:10px; margin-top:14px; }
.cl-supp-card  { flex:1; border-radius:8px; padding:12px; text-align:center; border:1px solid var(--border); }
.cl-supp-val   { font-size:22px; font-weight:700; font-family:var(--mono); }
.cl-supp-lbl   { font-size:11px; color:var(--muted); margin-top:2px; }

/* ── Tooltip icon ── */
.tip-icon {
    display:inline-flex; align-items:center; justify-content:center;
    font-size:9px; font-weight:700; font-style:normal;
    color:var(--muted); cursor:help;
    margin-left:5px; opacity:.5;
    width:13px; height:13px;
    border:1px solid currentColor; border-radius:50%;
    vertical-align:middle; transition:opacity .12s, color .12s;
    flex-shrink:0;
}
.tip-icon:hover { opacity:1; color:var(--accent); }

/* ── Floating tooltip (JS-positioned, appended to body) ── */
.cl-tip-float {
    position:fixed;
    z-index:999999;
    background:#1c1f26;
    border:1px solid rgba(255,255,255,.15);
    border-radius:8px;
    padding:9px 12px;
    font-size:12px; font-weight:400;
    color:#e8eaf0; line-height:1.55;
    white-space:normal; text-align:left;
    pointer-events:none;
    width:230px;
    box-shadow:0 6px 20px rgba(0,0,0,.6);
    transition:opacity .12s;
    opacity:0;
}

/* ── Misc ── */
.cl-title     { font-size:18px; font-weight:700; color:var(--accent); letter-spacing:.5px; margin-bottom:2px; }
.cl-subtitle  { font-size:13px; color:var(--muted); margin-bottom:18px; }
.cl-empty {
    background:var(--s1); border:1px solid var(--border); border-radius:10px;
    padding:32px; color:var(--muted); text-align:center; font-size:14px;
}
.cl-warn-strip {
    background:rgba(255,180,84,.12); border:1px solid rgba(255,180,84,.3);
    border-radius:8px; padding:10px 14px;
    font-size:13px; color:var(--warn); margin-bottom:14px;
}
.cl-status {
    border-top:1px solid var(--border); padding:8px 0;
    font-size:11px; color:var(--muted); display:flex; gap:20px; margin-top:16px;
    flex-wrap:wrap;
}
</style>
""", unsafe_allow_html=True)

# ─── JS tooltip engine (via components.html → window.parent, escapes overflow) ─
components.html("""
<script>
(function(){
  var doc = window.parent.document;

  // Clean up previous listener + element on each rerender
  var old = doc.getElementById('cl-tip-singleton');
  if (old) old.remove();
  if (doc._clTipHandler) doc.removeEventListener('mouseover', doc._clTipHandler);

  var tip = doc.createElement('div');
  tip.id = 'cl-tip-singleton';
  tip.className = 'cl-tip-float';
  doc.body.appendChild(tip);

  function handler(e) {
    var icon = e.target && e.target.closest ? e.target.closest('.tip-icon') : null;
    if (icon) {
      var text = icon.getAttribute('data-tip');
      if (!text) { tip.style.opacity = '0'; return; }
      tip.textContent = text;
      tip.style.opacity = '0';

      var r   = icon.getBoundingClientRect();
      var tw  = tip.offsetWidth  || 230;
      var th  = tip.offsetHeight || 80;
      var left = r.left + r.width / 2 - tw / 2;
      var top  = r.top  - th - 8;

      if (top  < 8) top  = r.bottom + 8;
      if (left < 8) left = 8;
      if (left + tw > window.parent.innerWidth - 8) left = window.parent.innerWidth - tw - 8;

      tip.style.left    = left + 'px';
      tip.style.top     = top  + 'px';
      tip.style.opacity = '1';
    } else {
      tip.style.opacity = '0';
    }
  }

  doc._clTipHandler = handler;
  doc.addEventListener('mouseover', handler);
})();
</script>
""", height=0)

# ─── HTML helpers ─────────────────────────────────────────────────────────────

_SUB_COLOR: dict[str, str] = {
    "basic":          "#7ed68a",
    "stage_1":        "#5bc8a0",
    "stage_2":        "#3ab8b0",
    "other":          "#7ed68a",
    "supporter":      "#ffb454",
    "item":           "#7eb8ff",
    "stadium":        "#caa56b",
    "tool":           "#c79bd1",
    "basic_energy":   "#e6c573",
    "special_energy": "#c79bd1",
}

# ─── Modal JS constants ───────────────────────────────────────────────────────
# Injected once into the parent document; uses plain braces (not f-string).
_MODAL_PARENT_SCRIPT = """
function closePtcgModal() {
    var m = document.getElementById('ptcg-modal');
    if (m) m.style.display = 'none';
}

function ptcgCategoryChanged() {
    var cat = document.getElementById('ptcg-edit-category').value;
    var sub = document.getElementById('ptcg-edit-subcategory');
    var prev = sub.value;
    sub.innerHTML = '';
    var opts = {
        'pokemon': [['basic','Basic'],['stage_1','Stage 1'],['stage_2','Stage 2'],['other','Other (ex / V / VMAX / VSTAR…)']],
        'trainer': [['item','Item'],['supporter','Supporter'],['stadium','Stadium'],['tool','Tool']],
        'energy':  [['basic_energy','Basic Energy'],['special_energy','Special Energy']]
    };
    (opts[cat] || []).forEach(function(o) {
        var el = document.createElement('option');
        el.value = o[0]; el.textContent = o[1];
        sub.appendChild(el);
    });
    sub.value = prev;
}

function savePtcgCorrection() {
    var modal = document.getElementById('ptcg-modal');
    var payload = JSON.stringify({
        set_code:    modal.dataset.setCode,
        set_number:  modal.dataset.setNumber,
        name:        document.getElementById('ptcg-edit-name').value.trim(),
        category:    document.getElementById('ptcg-edit-category').value,
        subcategory: document.getElementById('ptcg-edit-subcategory').value
    });
    var status = document.getElementById('ptcg-save-status');

    // Write correction to URL query params (no page reload)
    var url = new URL(window.location.href);
    url.searchParams.set('ptcg_correction', payload);
    window.history.replaceState(null, '', url);

    // Click the Streamlit "Apply correction" button to trigger a rerun
    var found = false;
    document.querySelectorAll('button').forEach(function(btn) {
        if (!found && btn.textContent.trim().startsWith('Apply correction')) {
            btn.click();
            found = true;
        }
    });

    if (found) {
        status.style.color = '#06d6a0';
        status.textContent = '✓ Saving...';
        setTimeout(closePtcgModal, 1400);
    } else {
        status.style.color = '#ffb454';
        status.textContent = '⚠ Click "Apply correction" in the sidebar to save.';
    }
}

document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') closePtcgModal();
});
"""

_MODAL_HTML = (
    '<button onclick="closePtcgModal()" style="position:fixed;top:18px;right:26px;'
    'background:none;border:none;font-size:42px;color:white;cursor:pointer;'
    'font-weight:bold;line-height:1;z-index:100000;">&#x2715;</button>'
    '<div style="display:flex;gap:20px;align-items:flex-start;max-height:88vh;'
    'padding:12px;flex-wrap:wrap;justify-content:center;overflow-y:auto;">'
    # ── card image ──
    '<img id="ptcg-modal-img" style="max-height:80vh;max-width:min(460px,46vw);'
    'border-radius:16px;object-fit:contain;box-shadow:0 0 60px rgba(0,0,0,.9);flex-shrink:0;"/>'
    # ── details panel ──
    '<div id="ptcg-modal-panel" style="background:#1c1f26;border-radius:16px;'
    'padding:20px 22px;min-width:240px;max-width:288px;overflow-y:auto;'
    'max-height:80vh;color:#e8eaf0;border:1px solid rgba(255,255,255,.07);'
    'font-family:system-ui,sans-serif;flex-shrink:0;">'
    # name
    '<div style="color:#9aa0ad;font-size:10px;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px;">Name</div>'
    '<input id="ptcg-edit-name" type="text" style="width:100%;background:#0d0e10;'
    'border:1px solid rgba(255,255,255,.15);border-radius:6px;color:#e8eaf0;'
    'font-size:14px;font-weight:600;padding:6px 8px;box-sizing:border-box;'
    'margin-bottom:14px;outline:none;" />'
    # set
    '<div style="color:#9aa0ad;font-size:10px;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px;">Set · Number</div>'
    '<div id="ptcg-detail-set" style="font-size:13px;color:#e8eaf0;margin-bottom:14px;font-family:monospace;letter-spacing:.5px;"></div>'
    # stage
    '<div style="color:#9aa0ad;font-size:10px;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px;">Stage</div>'
    '<div id="ptcg-detail-stage" style="font-size:13px;color:#e8eaf0;margin-bottom:14px;"></div>'
    # evolves from (hidden when not applicable)
    '<div id="ptcg-detail-evolve-row">'
    '<div style="color:#9aa0ad;font-size:10px;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px;">Evolves from</div>'
    '<div id="ptcg-detail-evolve" style="font-size:13px;color:#e8eaf0;margin-bottom:14px;"></div>'
    '</div>'
    # divider + edit section
    '<div style="border-top:1px solid rgba(255,255,255,.07);margin:4px 0 14px;"></div>'
    '<div style="color:#ffd740;font-size:10px;text-transform:uppercase;letter-spacing:.8px;margin-bottom:12px;font-weight:600;">Correct API data</div>'
    # category select
    '<div style="color:#9aa0ad;font-size:10px;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px;">Category</div>'
    '<select id="ptcg-edit-category" onchange="ptcgCategoryChanged()" style="width:100%;'
    'background:#0d0e10;border:1px solid rgba(255,255,255,.15);border-radius:6px;'
    'color:#e8eaf0;font-size:13px;padding:6px 8px;box-sizing:border-box;margin-bottom:14px;outline:none;">'
    '<option value="pokemon">Pokémon</option><option value="trainer">Trainer</option><option value="energy">Energy</option>'
    '</select>'
    # subcategory select (options populated by ptcgCategoryChanged)
    '<div style="color:#9aa0ad;font-size:10px;text-transform:uppercase;letter-spacing:.8px;margin-bottom:4px;">Subcategory / Type</div>'
    '<select id="ptcg-edit-subcategory" style="width:100%;background:#0d0e10;'
    'border:1px solid rgba(255,255,255,.15);border-radius:6px;color:#e8eaf0;'
    'font-size:13px;padding:6px 8px;box-sizing:border-box;margin-bottom:20px;outline:none;"></select>'
    # save button
    '<button onclick="savePtcgCorrection()" style="width:100%;background:#ffd740;'
    'color:#0d0e10;border:none;border-radius:8px;font-size:13px;font-weight:700;'
    'padding:9px 0;cursor:pointer;letter-spacing:.3px;">Save correction</button>'
    # status
    '<div id="ptcg-save-status" style="font-size:12px;margin-top:10px;min-height:18px;text-align:center;"></div>'
    '</div>'   # end panel
    '</div>'   # end flex wrapper
)


def _sort_pokemon_by_chain(cards: list) -> list:
    """Sort Pokémon cards by evolution chain (Basic→Stage1→Stage2), then alphabetically."""
    deck_names = {c.name for c in cards}

    # Per-name metadata: prefer entries that have evolve_from set
    name_meta: dict[str, dict] = {}
    for c in cards:
        if c.name not in name_meta:
            name_meta[c.name] = {"stage": c.stage, "evolve_from": c.evolve_from}
        elif c.evolve_from and not name_meta[c.name]["evolve_from"]:
            name_meta[c.name]["evolve_from"] = c.evolve_from

    # Roots: names whose parent is not in the deck (or has no parent)
    roots = sorted(
        n for n, m in name_meta.items()
        if not m["evolve_from"] or m["evolve_from"] not in deck_names
    )

    def _chain(name: str, visited: set) -> list[str]:
        visited.add(name)
        result = [name]
        children = sorted(
            n for n, m in name_meta.items()
            if m["evolve_from"] == name and n not in visited
        )
        for child in children:
            result.extend(_chain(child, visited))
        return result

    visited: set[str] = set()
    order: list[str] = []
    for root in roots:
        if root not in visited:
            order.extend(_chain(root, visited))
    order.extend(sorted(n for n in name_meta if n not in set(order)))

    pos = {name: i for i, name in enumerate(order)}
    return sorted(cards, key=lambda c: (pos.get(c.name, 999), c.set_code, c.set_number))


def _parse_pct(s: str) -> float:
    try:
        return float(str(s).strip("%"))
    except ValueError:
        return 0.0


def _tip(text: str, pos: str = "") -> str:
    """Return an ⓘ tooltip icon HTML element."""
    cls = f" tip-{pos}" if pos else ""
    return f'<span class="tip-icon{cls}" data-tip="{text}">i</span>'


_OPENING_TIPS: dict[str, str] = {
    "Mulligan (no Basic)": (
        "Zero Basic Pokémon in your opening hand. "
        "You must reveal your hand, shuffle back and redraw 7. "
        "Your opponent draws 1 Prize card for each mulligan you take."
    ),
    "Starting with exactly 1 Basic": (
        "Exactly 1 Basic Pokémon in your opening hand. "
        "You must use it as your Active starter — no choice."
    ),
    "Starting with 2 or more Basics": (
        "2 or more Basics in your opening hand. "
        "You can choose which one to place as your Active starter."
    ),
}


def _prob_bar(label: str, pct_str: str, accent: str = "var(--accent)") -> str:
    p = min(_parse_pct(pct_str), 100.0)
    return (
        f'<div class="cl-prob-row">'
        f'<div class="cl-prob-label">{label}</div>'
        f'<div class="cl-prob-track"><div class="cl-prob-fill" style="width:{p:.1f}%;background:{accent};"></div></div>'
        f'<div class="cl-prob-val">{pct_str}</div>'
        f"</div>"
    )


def _html_metrics(
    deck_size: int,
    ok_count: int,
    mulligan: str,
    supporter: str,
    dead_hand: str,
) -> str:
    mull_p = _parse_pct(mulligan)
    mull_cls = "bad" if mull_p > 7 else "warn" if mull_p > 4 else "good"
    dead_p = _parse_pct(dead_hand)
    dead_cls = "warn" if dead_p > 2 else "good"

    def _card(val: str, cls: str, label: str, sub: str = "", tip: str = "") -> str:
        sub_html = f'<div class="cl-kpi-sub">{sub}</div>' if sub else ""
        tip_html = _tip(tip, "b") if tip else ""
        return (
            f'<div class="cl-kpi">'
            f'<div class="cl-kpi-val {cls}">{val}</div>'
            f'<div class="cl-kpi-label">{label}{tip_html}</div>'
            f"{sub_html}"
            f"</div>"
        )

    cards = "".join([
        _card(str(deck_size), "accent", "Deck size",
              tip="Total cards in your deck. Standard format requires exactly 60 cards."),
        _card(mulligan, mull_cls, "Mulligan rate", "P(no Basic in opening 7)",
              tip="Probability of having no Basic Pokémon in your opening 7 cards. Forces a reshuffle — your opponent draws 1 Prize card per mulligan."),
        _card(supporter, "accent", "Supporter T1", "P(≥1 supporter in hand)",
              tip="Probability of having at least 1 Supporter card in your opening 7 cards. Crucial for setting up your first turn."),
        _card(dead_hand, dead_cls, "Dead hand", "0 supporters &amp; 0 energy",
              tip="Probability of a hand with no Supporters AND no Energy. Very hard to recover from — usually means passing your first turn."),
        _card(f"{ok_count}/{deck_size}", "good", "Resolved", "cards via TCGDex",
              tip="Cards successfully identified via TCGDex API. Unresolved cards may affect calculation accuracy."),
    ])
    return f'<div class="cl-kpi-row">{cards}</div>'


def _html_breakdown(breakdown_df, deck_size: int) -> str:
    rows = []
    for _, row in breakdown_df.iterrows():
        n = int(row["#"])
        if n == 0:
            continue
        cat = str(row["Category"]).strip()
        sub = str(row["Subcategory"]).strip()
        pct = n / deck_size * 100
        sub_key = sub.lower().replace(" ", "_")
        color = _SUB_COLOR.get(sub_key, "#666")
        rows.append(
            f'<div class="cl-bd-row">'
            f'<div class="cl-bd-cat">{cat}</div>'
            f'<div class="cl-bd-sub">{sub}</div>'
            f'<div class="cl-bd-n">{n}</div>'
            f'<div class="cl-bd-track"><div class="cl-bd-fill" style="width:{pct:.1f}%;background:{color};"></div></div>'
            f'<div class="cl-bd-pct">{pct:.0f}%</div>'
            f"</div>"
        )
    return "".join(rows)


def _html_opening(opening_df) -> str:
    rows = []
    for _, row in opening_df.iterrows():
        event = row["Event"]
        tip = _OPENING_TIPS.get(event, "")
        label = f'{event}{_tip(tip) if tip else ""}'
        rows.append(_prob_bar(label, row["Probability"]))
    return "".join(rows)


def _html_starter_bars(starters_df, deck) -> str:
    # Key by (set_code, set_number) so multiple cards with the same name
    # (e.g., two Dunsparce from different sets) each get their correct image.
    img_by_key: dict[tuple[str, str], str] = {
        (c.set_code, c.set_number): c.image for c in deck.cards if c.image
    }
    rows = []
    for _, row in starters_df.iterrows():
        raw_name = str(row["Pokémon"])
        name = raw_name.split(" (")[0]
        set_info = raw_name[len(name):].strip("() ")
        copies = row["Copies"]
        possible = str(row["Possible Starter"])
        forced = str(row["Forced Starter"])
        p_p = min(_parse_pct(possible), 100.0)
        f_p = min(_parse_pct(forced), 100.0)

        # Parse "JTG #120" → ("JTG", "120")
        _parts = set_info.split()
        _set_code = _parts[0] if _parts else ""
        _set_num = _parts[1].lstrip("#") if len(_parts) > 1 else ""
        img = img_by_key.get((_set_code, _set_num), "")
        if img:
            thumb = f'<img src="{img}" />'
        else:
            short = name[:10]
            thumb = f'<div class="cl-starter-ph">{short}</div>'

        rows.append(
            f'<div class="cl-starter-row">'
            f'<div class="cl-starter-thumb">{thumb}</div>'
            f'<div class="cl-starter-name">'
            f'  <div class="cl-starter-title">{name}</div>'
            f'  <div class="cl-starter-set">{set_info}</div>'
            f'</div>'
            f'<div class="cl-starter-copies"><span class="cl-qty-chip">{copies}×</span></div>'
            f'<div class="cl-bar-col">'
            f'  <div class="cl-bar-col-lbl">Possible starter'
            f'{_tip("P(≥1 copy in your opening 7 cards). This Pokémon can be your starter, but you may have other Basics to choose from.")}'
            f'</div>'
            f'  <div class="cl-mini-track"><div class="cl-mini-fill" style="width:{p_p:.1f}%;background:var(--accent);"></div></div>'
            f'  <div class="cl-bar-val">{possible}</div>'
            f'</div>'
            f'<div class="cl-bar-col">'
            f'  <div class="cl-bar-col-lbl">Forced starter'
            f'{_tip("P(this is the ONLY Basic Pokémon in your hand). You must start with it — no other Basic available to choose.", "l")}'
            f'</div>'
            f'  <div class="cl-mini-track"><div class="cl-mini-fill" style="width:{f_p:.1f}%;background:#c79bd1;"></div></div>'
            f'  <div class="cl-bar-val">{forced}</div>'
            f'</div>'
            f"</div>"
        )
    return "".join(rows)


def _html_prizes(prizes_df, deck) -> str:
    img_by_name: dict[str, str] = {c.name: c.image for c in deck.cards if c.image}
    prize_col = [c for c in prizes_df.columns if "Prized" in c][0]
    sorted_df = prizes_df.copy()
    sorted_df["_sort"] = sorted_df[prize_col].apply(_parse_pct)
    top8 = sorted_df.sort_values("_sort", ascending=False).head(8)
    rows = []
    for _, row in top8.iterrows():
        name = str(row["Card"])
        copies = row["Copies"]
        prob = str(row[prize_col])
        p = _parse_pct(prob)
        bar_color = "var(--bad)" if p > 40 else "var(--warn)" if p > 25 else "var(--good)"

        img = img_by_name.get(name, "")
        if img:
            thumb = f'<img src="{img}" />'
        else:
            thumb = f'<div class="cl-prize-ph">{name[:8]}</div>'

        rows.append(
            f'<div class="cl-prize-row">'
            f'<div class="cl-prize-thumb">{thumb}</div>'
            f'<div class="cl-prize-name">'
            f'  <div class="cl-prize-title">{name}</div>'
            f'  <div class="cl-prize-copies">{copies}×</div>'
            f'</div>'
            f'<div class="cl-prize-bar">'
            f'  <div class="cl-prize-track"><div class="cl-prize-fill" style="width:{min(p,100):.1f}%;background:{bar_color};"></div></div>'
            f'</div>'
            f'<div class="cl-prize-val">{prob}</div>'
            f"</div>"
        )
    extra = len(prizes_df) - 8
    if extra > 0:
        rows.append(
            f'<div style="font-size:12px;color:var(--muted);padding:6px 0;">+ {extra} more cards</div>'
        )
    return "".join(rows)


def _html_draw_heatmap(draw_df) -> str:
    turn_cols = [f"Turn {i}" for i in range(1, 7)]

    def _heat_bg(p: float) -> str:
        alpha = 0.05 + min(p, 1.0) * 0.85
        return f"rgba(255,215,64,{alpha:.2f})"

    def _heat_fg(p: float) -> str:
        return "#1a1a1a" if p > 0.55 else "rgba(255,255,255,0.85)"

    headers = (
        "<tr>"
        '<th class="l">Card</th>'
        '<th class="c">Copies</th>'
        + "".join(f'<th class="c">T{i}</th>' for i in range(1, 7))
        + "</tr>"
    )
    rows_html = []
    top12 = draw_df.sort_values("Copies", ascending=False).head(12)
    for _, row in top12.iterrows():
        cells = (
            f'<td class="name">{row["Card"]}</td>'
            f'<td class="cp"><span class="cl-qty-chip">{row["Copies"]}×</span></td>'
        )
        for col in turn_cols:
            p_val = _parse_pct(str(row[col])) / 100.0
            bg = _heat_bg(p_val)
            fg = _heat_fg(p_val)
            pct_disp = f"{p_val*100:.0f}"
            cells += (
                f'<td><div class="cl-hcell" style="background:{bg};color:{fg};">{pct_disp}</div></td>'
            )
        rows_html.append(f"<tr>{cells}</tr>")

    return (
        f'<table class="cl-heat">'
        f"<thead>{headers}</thead>"
        f'<tbody>{"".join(rows_html)}</tbody>'
        f"</table>"
    )


def _html_target(target_df) -> str:
    rows = []
    n = len(target_df)
    for i, (_, row) in enumerate(target_df.iterrows()):
        stat = str(row["Statistic"])
        prob = str(row["Probability"])
        p = _parse_pct(prob)
        if i == n - 1:
            accent = "var(--good)"
        elif "search" in stat.lower() or "buscador" in stat.lower():
            accent = "#7eb8ff"
        else:
            accent = "var(--accent)"
        rows.append(_prob_bar(stat, prob, accent))
    return "".join(rows)


def _html_supporter(support_df) -> str:
    supp = str(support_df.iloc[0]["Probability"])
    dead = str(support_df.iloc[1]["Probability"])
    bars = _prob_bar(support_df.iloc[0]["Statistic"], supp, "var(--good)")
    bars += _prob_bar(support_df.iloc[1]["Statistic"], dead, "var(--bad)")
    highlight = (
        '<div class="cl-supp-cards">'
        '<div class="cl-supp-card" style="background:rgba(6,214,160,.08);border-color:rgba(6,214,160,.3);">'
        f'<div class="cl-supp-val" style="color:var(--good);">{supp}</div>'
        '<div class="cl-supp-lbl">Supporter T1</div></div>'
        '<div class="cl-supp-card" style="background:rgba(230,57,70,.08);border-color:rgba(230,57,70,.3);">'
        f'<div class="cl-supp-val" style="color:var(--bad);">{dead}</div>'
        '<div class="cl-supp-lbl">Dead Hand</div></div>'
        "</div>"
    )
    return bars + highlight


def _html_mc(comparison_df) -> str:
    headers = (
        "<tr>"
        "<th>Statistic</th>"
        '<th class="r">Theoretical</th>'
        '<th class="r">Simulated</th>'
        '<th class="r">Δ</th>'
        "<th></th>"
        "</tr>"
    )
    rows_html = []
    for _, row in comparison_df.iterrows():
        is_combo = str(row["Statistic"]).startswith("Combo:")
        theo_raw = str(row["Theoretical"])
        diff_raw = str(row["Diff"])
        has_theo = theo_raw != "—"
        has_diff = diff_raw != "—"

        try:
            diff_val = float(diff_raw) if has_diff else 0.0
        except (ValueError, TypeError):
            diff_val = 0.0
        diff_cls = "ok" if diff_val <= 0.005 else "warn"

        try:
            theo = float(theo_raw) if has_theo else 0.0
            emp = float(row["Simulated"])
        except (ValueError, TypeError):
            theo, emp = 0.0, 0.0

        if has_theo:
            vis = (
                f'<div class="cl-mc-vis">'
                f'<div class="cl-mc-bar" style="width:{min(theo*100, 100):.1f}%;"></div>'
                f'<div class="cl-mc-pin" style="left:{min(emp*100, 100):.1f}%;"></div>'
                f"</div>"
            )
        else:
            vis = (
                f'<div class="cl-mc-vis">'
                f'<div class="cl-mc-pin" style="left:{min(emp*100, 100):.1f}%;"></div>'
                f"</div>"
            )

        row_style = ' style="background:rgba(255,215,64,.06);"' if is_combo else ""
        theo_cell = f'<td class="mono">{theo*100:.2f}%</td>' if has_theo else '<td class="mono" style="color:var(--muted);">—</td>'
        diff_cell = f'<td class="{diff_cls}">{diff_val*100:.3f}%</td>' if has_diff else '<td class="mono" style="color:var(--muted);">—</td>'

        rows_html.append(
            f"<tr{row_style}>"
            f'<td>{row["Statistic"]}</td>'
            f"{theo_cell}"
            f'<td class="mono">{emp*100:.2f}%</td>'
            f"{diff_cell}"
            f"<td>{vis}</td>"
            f"</tr>"
        )
    return (
        f'<table class="cl-mc">'
        f"<thead>{headers}</thead>"
        f'<tbody>{"".join(rows_html)}</tbody>'
        f"</table>"
    )


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    # Brand header
    st.markdown("""
    <div class="rail-brand">
      <span style="font-size:26px;line-height:1;">🎴</span>
      <div>
        <div class="rail-brand-title">Consistency Lab</div>
        <div class="rail-brand-sub">Pokémon TCG Simulator</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    tab_deck, tab_config = st.tabs(["DECK", "CONFIG"])

    # ── DECK tab ──────────────────────────────────────────────────────────────
    with tab_deck:
        st.markdown('<div class="fl fl-top">Deck List</div>', unsafe_allow_html=True)
        deck_list_text = st.text_area(
            "Deck List (PTCG Live)",
            value=SAMPLE_DECK_LIST,
            height=260,
            help="Cole o texto exportado do PTCG Live.",
            label_visibility="collapsed",
        )

        try:
            _parsed = parse_deck_list(deck_list_text)
        except Exception:
            _parsed = []

        _card_count = sum(c["quantity"] for c in _parsed)
        _unique = len(_parsed)
        _cc_cls = "ok" if _card_count == 60 else "wn" if _card_count > 0 else "er"
        st.markdown(
            f'<div class="tx-meter"><span>{_unique} unique</span>'
            f'<span class="{_cc_cls}">{_card_count}/60</span></div>',
            unsafe_allow_html=True,
        )

        _all_names = sorted({c["name"] for c in _parsed})
        _pokemon_names = sorted({c["name"] for c in _parsed if c["category"] == "pokemon"})

        # Filter stale selections when deck changes
        _tc_prev = st.session_state.get("target_cards_sel") or []
        st.session_state["target_cards_sel"] = [n for n in _tc_prev if n in _pokemon_names]
        _sc_prev = st.session_state.get("search_cards_sel") or []
        st.session_state["search_cards_sel"] = [n for n in _sc_prev if n in _all_names]

        _tc_n = len(st.session_state["target_cards_sel"])
        _tc_badge = f' <span class="flc">{_tc_n}</span>' if _tc_n else ""
        st.markdown(f'<div class="fl">Target cards{_tc_badge}</div>', unsafe_allow_html=True)
        st.caption("Pokémon you want to draw into your opening hand.")
        target_card_names = list(st.pills(
            "Target cards",
            options=_pokemon_names,
            selection_mode="multi",
            key="target_cards_sel",
            label_visibility="collapsed",
        ) or [])

        _sc_n = len(st.session_state["search_cards_sel"])
        _sc_badge = f' <span class="flc">{_sc_n}</span>' if _sc_n else ""
        st.markdown(f'<div class="fl">Searchers{_sc_badge}</div>', unsafe_allow_html=True)
        st.caption("Cards that fetch your targets — Ultra Ball, Buddy-Buddy Poffin...")
        target_search_names = list(st.pills(
            "Searchers",
            options=_all_names,
            selection_mode="multi",
            key="search_cards_sel",
            label_visibility="collapsed",
        ) or [])

    # ── CONFIG tab (MC settings + Combo) ──────────────────────────────────────
    with tab_config:
        st.markdown('<div class="fl fl-top">Monte Carlo Simulations</div>', unsafe_allow_html=True)

        if "mc_sims_n" not in st.session_state:
            st.session_state["mc_sims_n"] = 100_000

        _pm = {"10K": 10_000, "50K": 50_000, "100K": 100_000, "500K": 500_000}
        _seg = st.segmented_control(
            "Presets",
            list(_pm.keys()),
            label_visibility="collapsed",
        )
        if _seg:
            st.session_state["mc_sims_n"] = _pm[_seg]

        mc_simulations = st.number_input(
            "Custom value",
            min_value=0,
            max_value=1_000_000,
            step=10_000,
            key="mc_sims_n",
            label_visibility="collapsed",
        )

        st.markdown('<div class="fl">Random Seed</div>', unsafe_allow_html=True)
        mc_seed = st.number_input(
            "Seed",
            min_value=0,
            value=42,
            label_visibility="collapsed",
        )

        st.divider()

        _cb_n = len(st.session_state.get("mc_combo_sel") or [])
        _cb_badge = f' <span class="flc">{_cb_n}</span>' if _cb_n else ""
        st.markdown(f'<div class="fl">Combo cards{_cb_badge}</div>', unsafe_allow_html=True)
        st.caption("Select 2+ cards — P(all in opening hand).")
        mc_combo = list(st.pills(
            "Combo",
            options=_all_names,
            selection_mode="multi",
            key="mc_combo_sel",
            label_visibility="collapsed",
        ) or [])

    # ── Analyze button (always visible, outside tabs) ─────────────────────────
    st.markdown('<div style="height:8px;"></div>', unsafe_allow_html=True)
    analyze_clicked = st.button(
        "▶  Analyze deck",
        use_container_width=True,
        type="primary",
    )
    st.markdown(
        '<div class="rail-meta">cache: card_cache.json · TCGDex API</div>',
        unsafe_allow_html=True,
    )

    # Invisible trigger button — JS clicks this to send correction data to Python.
    _apply_clicked = st.button("Apply correction", key="apply_correction_btn")
    st.markdown("""
    <style>
    [data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] { display:none; }
    </style>
    """, unsafe_allow_html=True)
    if _apply_clicked:
        _raw = st.query_params.get("ptcg_correction", "")
        if _raw:
            try:
                _corr = json.loads(_raw)
                _apply_card_correction(_corr)
                if "report" in st.session_state:
                    _update_deck_cards(st.session_state["report"].deck, _corr)
                del st.query_params["ptcg_correction"]
                st.session_state["_corr_success"] = (
                    f"✓ Correction saved for {_corr.get('name', 'card')} "
                    f"({_corr.get('set_code', '')}·{_corr.get('set_number', '')})"
                )
            except Exception as _exc:
                st.session_state["_corr_error"] = str(_exc)
        st.rerun()


# ─── Page title ───────────────────────────────────────────────────────────────
st.markdown(
    '<div class="cl-title">🎴 Consistency Lab</div>'
    '<div class="cl-subtitle">Pokémon TCG · probabilistic deck analysis</div>',
    unsafe_allow_html=True,
)

# ─── Analysis ─────────────────────────────────────────────────────────────────
if analyze_clicked:
    with st.spinner("Analyzing deck…"):
        try:
            deck, unknown = build_deck(deck_list_text)
            report = build_report(
                deck=deck,
                target_card_names=target_card_names,
                target_search_names=target_search_names,
                mc_simulations=int(mc_simulations),
                mc_seed=int(mc_seed),
                mc_combo=mc_combo or None,
            )
            st.session_state["report"] = report
            st.session_state["unknown"] = unknown
        except Exception as exc:
            st.error(f"Error analyzing deck: {exc}")
            st.stop()

if "report" not in st.session_state:
    st.markdown(
        '<div class="cl-empty">'
        'Paste your deck list in the sidebar and click '
        '<span style="color:var(--accent);font-weight:700;">▶ Analyze deck</span> to start.'
        "</div>",
        unsafe_allow_html=True,
    )
    st.stop()

report = st.session_state["report"]
unknown = st.session_state["unknown"]
deck = report.deck
deck_size = deck.total_cards
ok_count = deck_size - len(unknown)

# ─── Alerts ───────────────────────────────────────────────────────────────────
if unknown:
    st.markdown(
        f'<div class="cl-warn-strip">'
        f"⚠ {len(unknown)} card(s) not found in TCGDex API: "
        + ", ".join(unknown)
        + "</div>",
        unsafe_allow_html=True,
    )

# ─── KPI row ──────────────────────────────────────────────────────────────────
mulligan_pct = report.opening_df.iloc[0]["Probability"]
supporter_pct = report.support_df.iloc[0]["Probability"]
dead_hand_pct = report.support_df.iloc[1]["Probability"]

st.markdown(
    _html_metrics(deck_size, ok_count, mulligan_pct, supporter_pct, dead_hand_pct),
    unsafe_allow_html=True,
)

# ─── Correction feedback ───────────────────────────────────────────────────────
if _corr_ok := st.session_state.pop("_corr_success", None):
    st.success(_corr_ok)
if _corr_err := st.session_state.pop("_corr_error", None):
    st.error(f"Correction failed: {_corr_err}")

# ─── Deck list visual ─────────────────────────────────────────────────────────
with st.expander("Deck list", expanded=True):
    _cat_order = {"pokemon": 0, "trainer": 1, "energy": 2}
    _groups: dict[str, list] = {"pokemon": [], "trainer": [], "energy": []}

    _pokemon_sorted = _sort_pokemon_by_chain(
        [c for c in deck.cards if c.category == "pokemon"]
    )
    _others_sorted = sorted(
        [c for c in deck.cards if c.category != "pokemon"],
        key=lambda c: (_cat_order.get(c.category, 3), c.name),
    )
    for _c in _pokemon_sorted + _others_sorted:
        _groups.get(_c.category, _groups["energy"]).append(_c)

    _cat_labels = {"pokemon": "Pokémon", "trainer": "Trainer", "energy": "Energy"}
    _dot_colors = {"pokemon": "#7ed68a", "trainer": "#7eb8ff", "energy": "#e6c573"}
    _badge_css = (
        "position:absolute;bottom:4px;left:4px;background:rgba(0,0,0,.75);"
        "color:var(--accent);border-radius:4px;width:22px;height:18px;font-size:12px;"
        "font-weight:bold;display:flex;align-items:center;justify-content:center;"
        "font-family:var(--mono);"
    )
    _cards_html = ""
    for _cat in ["pokemon", "trainer", "energy"]:
        _cat_cards = _groups[_cat]
        if not _cat_cards:
            continue
        _total = sum(c.quantity for c in _cat_cards)
        _dot = _dot_colors[_cat]
        _label = _cat_labels[_cat]
        _cards_html += (
            f'<div style="width:100%;margin:8px 0 4px;font-size:12px;font-weight:600;'
            f'color:var(--muted);text-transform:uppercase;letter-spacing:.6px;'
            f'display:flex;align-items:center;gap:6px;">'
            f'<span style="width:8px;height:8px;border-radius:50%;background:{_dot};flex-shrink:0;display:inline-block;"></span>'
            f'{_label} <span style="font-weight:400;color:#555;">{_total}</span></div>'
        )
        for _card in _cat_cards:
            # Encode all card metadata as a safe JSON attribute value
            _cd = _html.escape(json.dumps({
                "name": _card.name,
                "category": _card.category,
                "subcategory": _card.subcategory,
                "set_code": _card.set_code,
                "set_number": _card.set_number,
                "image": _card.image,
                "stage": _card.stage,
                "evolve_from": _card.evolve_from,
            }, ensure_ascii=False))
            if _card.image:
                _cards_html += (
                    f'<div class="ptcg-card" data-card="{_cd}" data-img="{_card.image}" onclick="openPtcgModal(this)">'
                    f'<img src="{_card.image}" width="84" style="border-radius:6px;display:block;" title="{_card.name}"/>'
                    f'<span style="{_badge_css}">{_card.quantity}</span>'
                    f"</div>"
                )
            else:
                _cards_html += (
                    f'<div class="ptcg-card" data-card="{_cd}" '
                    f'style="width:84px;height:117px;background:var(--s2);'
                    f"border-radius:6px;color:var(--muted);font-size:10px;text-align:center;"
                    f"display:inline-block;margin:4px;padding:8px 4px;box-sizing:border-box;"
                    f"border:1px solid var(--border);vertical-align:top;position:relative;"
                    f'padding-top:44px;cursor:pointer;" onclick="openPtcgModal(this)">'
                    f"{_card.name[:14]}"
                    f'<span style="{_badge_css}">{_card.quantity}</span>'
                    f"</div>"
                )

    _total_cards = sum(c.quantity for c in deck.cards)
    _rows = math.ceil(len(deck.cards) / 9)
    _height = max(200, _rows * 145 + 48)

    # Encode constants as JS string literals so f-string braces are never at risk
    _parent_script_js = json.dumps(_MODAL_PARENT_SCRIPT)
    _modal_html_js    = json.dumps(_MODAL_HTML)

    components.html(
        f"""
        <style>
        :root {{
            --s2:#1c1f26; --accent:#ffd740; --muted:#9aa0ad; --border:rgba(255,255,255,.07);
        }}
        body {{ margin:0; background:#16181d; }}
        .ptcg-card {{
            position:relative; display:inline-block; margin:4px;
            cursor:pointer; transition:transform .12s,opacity .12s;
            vertical-align:top;
        }}
        .ptcg-card:hover {{ transform:translateY(-3px); opacity:.9; }}
        </style>

        <div style="display:flex;flex-wrap:wrap;gap:0;align-items:flex-start;">{_cards_html}</div>

        <script>
        // ── Hover preview ────────────────────────────────────────────────────
        document.querySelectorAll('.ptcg-card[data-img]').forEach(function(card) {{
            card.addEventListener('mouseenter', function() {{
                var p = window.parent.document;
                var preview = p.getElementById('ptcg-hover');
                if (!preview) {{
                    preview = p.createElement('div');
                    preview.id = 'ptcg-hover';
                    preview.style.cssText = 'position:fixed;z-index:9998;pointer-events:none;'
                        + 'border-radius:12px;box-shadow:0 8px 32px rgba(0,0,0,.7);';
                    preview.innerHTML = '<img id="ptcg-hover-img" style="width:200px;border-radius:12px;display:block;"/>';
                    p.body.appendChild(preview);
                }}
                var iframe = window.frameElement;
                var ir = iframe.getBoundingClientRect();
                var cr = this.getBoundingClientRect();
                var cx = ir.left + cr.left + cr.width / 2;
                var cy = ir.top  + cr.top  + cr.height / 2;
                var pw = 200, ph = 279;
                var vw = window.parent.innerWidth, vh = window.parent.innerHeight;
                var left = Math.max(8, Math.min(cx - pw/2, vw - pw - 8));
                var top  = Math.max(8, Math.min(cy - ph/2, vh - ph - 8));
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

        // ── Parent-doc functions (injected once) ─────────────────────────────
        (function() {{
            var p = window.parent.document;
            if (p.getElementById('ptcg-modal-script')) return;
            var sc = p.createElement('script');
            sc.id = 'ptcg-modal-script';
            sc.textContent = {_parent_script_js};
            p.head.appendChild(sc);
        }})();

        // ── Open fullscreen modal ─────────────────────────────────────────────
        function openPtcgModal(el) {{
            var card = {{}};
            try {{ card = JSON.parse(el.getAttribute('data-card') || '{{}}'); }} catch(e) {{}}

            var p = window.parent.document;

            var modal = p.getElementById('ptcg-modal');
            if (!modal) {{
                modal = p.createElement('div');
                modal.id = 'ptcg-modal';
                modal.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;'
                    + 'background:rgba(0,0,0,.92);z-index:99999;display:flex;'
                    + 'align-items:center;justify-content:center;';
                modal.setAttribute('onclick', 'if(event.target===this)closePtcgModal()');
                modal.innerHTML = {_modal_html_js};
                p.body.appendChild(modal);
            }}

            // Stamp card identity on the modal element for savePtcgCorrection
            modal.dataset.setCode   = card.set_code   || '';
            modal.dataset.setNumber = card.set_number || '';

            // Populate image
            p.getElementById('ptcg-modal-img').src = card.image || '';

            // Populate read-only info
            p.getElementById('ptcg-edit-name').value      = card.name || '';
            p.getElementById('ptcg-detail-set').textContent   = (card.set_code || '—') + '  ·  ' + (card.set_number || '—');
            p.getElementById('ptcg-detail-stage').textContent = card.stage || '—';
            p.getElementById('ptcg-detail-evolve').textContent = card.evolve_from || '';
            p.getElementById('ptcg-detail-evolve-row').style.display = card.evolve_from ? '' : 'none';

            // Set category and rebuild subcategory options
            p.getElementById('ptcg-edit-category').value = card.category || 'pokemon';
            window.parent.ptcgCategoryChanged();
            p.getElementById('ptcg-edit-subcategory').value = card.subcategory || '';

            // Clear any previous status message
            p.getElementById('ptcg-save-status').textContent = '';

            modal.style.display = 'flex';
        }}
        </script>
        """,
        height=_height,
    )

# ─── Breakdown + Opening hand (2 cols) ────────────────────────────────────────
col_bd, col_op = st.columns(2)

with col_bd:
    with st.expander("Composition", expanded=True):
        st.markdown(
            f'<div class="cl-sec">Deck breakdown'
            f'{_tip("Distribution of card types in your deck. Bars show the proportion of each subcategory relative to the total 60 cards.", "r")}'
            f'<span class="cl-sec-count">{deck_size} cards</span></div>'
            + _html_breakdown(report.breakdown_df, deck_size),
            unsafe_allow_html=True,
        )

with col_op:
    with st.expander("Opening hand", expanded=True):
        st.markdown(
            '<div class="cl-sec">Opening hand probabilities'
            + _tip("Theoretical probabilities for your 7-card opening hand, calculated via hypergeometric distribution. Assumes no prior knowledge of hand contents.")
            + '</div>'
            + _html_opening(report.opening_df),
            unsafe_allow_html=True,
        )

# ─── Starters ─────────────────────────────────────────────────────────────────
with st.expander(f"Starters by basic Pokémon ({len(report.starters_df)})", expanded=True):
    st.markdown(
        '<div class="cl-sec">Starter probabilities'
        + _tip("For each Basic Pokémon: Possible Starter = P(≥1 copy in hand). Forced Starter = P(it is the ONLY Basic in hand, so you have no choice of starter).")
        + '</div>'
        + _html_starter_bars(report.starters_df, deck),
        unsafe_allow_html=True,
    )

# ─── Prizes + Target analysis (2 cols) ────────────────────────────────────────
col_pr, col_tg = st.columns(2)

with col_pr:
    with st.expander("Prize-card risk", expanded=True):
        st.markdown(
            '<div class="cl-sec">P(≥1 prized)'
            + _tip("Probability that at least 1 copy of a card ends up in your 6 Prize cards at game start, making it temporarily inaccessible. Higher % = bigger risk.")
            + '<span class="cl-sec-count">top 8</span></div>'
            + _html_prizes(report.prizes_df, deck),
            unsafe_allow_html=True,
        )

with col_tg:
    with st.expander("Supporter & dead hand", expanded=True):
        st.markdown(
            '<div class="cl-sec">Supporter & hand quality'
            + _tip("Supporter T1: P(≥1 Supporter in opening 7). Dead hand: P(no Supporters AND no Energy) — a hand nearly impossible to play from.")
            + '</div>'
            + _html_supporter(report.support_df),
            unsafe_allow_html=True,
        )

    if target_card_names or target_search_names:
        with st.expander("Target analysis", expanded=True):
            st.markdown(
                '<div class="cl-sec">Target draw probability'
                + _tip("P(drawing a target card or a searcher that can fetch it by turn N). Combines direct draw with searcher probability.")
                + '</div>'
                + _html_target(report.target_df),
                unsafe_allow_html=True,
            )

# ─── Draw heatmap ─────────────────────────────────────────────────────────────
with st.expander("Draw by turn — cumulative", expanded=True):
    st.markdown(
        '<div class="cl-sec">Draw by turn — cumulative'
        + _tip("Cumulative P(drawing ≥1 copy of a card by turn N). Accounts for the 7-card opening hand plus 1 draw per turn. Values are colour-coded: darker yellow = higher probability.")
        + '</div>'
        + _html_draw_heatmap(report.draw_df),
        unsafe_allow_html=True,
    )

# ─── Monte Carlo ──────────────────────────────────────────────────────────────
if report.comparison_df is not None:
    with st.expander(
        f"Monte Carlo — empirical vs theoretical ({int(mc_simulations):,} sims)",
        expanded=True,
    ):
        st.markdown(
            '<div class="cl-sec">Simulation vs theory'
            + _tip("Compares empirical probabilities from Monte Carlo simulation against exact hypergeometric calculations. Δ close to 0% means the simulation is converging correctly.")
            + '</div>'
            + _html_mc(report.comparison_df),
            unsafe_allow_html=True,
        )

# ─── Status bar ───────────────────────────────────────────────────────────────
st.markdown(
    f'<div class="cl-status">'
    f'<span style="color:var(--good);">✓ {ok_count}/{deck_size} cards classified</span>'
    f"<span>cache: card_cache.json</span>"
    f"<span>MC: {int(mc_simulations):,} sims · seed {int(mc_seed)}</span>"
    f"</div>",
    unsafe_allow_html=True,
)
