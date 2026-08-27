"""Kautilya UI — custom CSS and theme constants."""

# Color palette
NAVY = "#1a1a2e"
DARK_BG = "#0e1117"
CARD_BG = "#16213e"
GOLD = "#b8960c"
GOLD_DIM = "#c9a90e"
BLUE = "#4fc3f7"
GREEN = "#4caf50"
ORANGE = "#ff9800"
RED = "#ef5350"
CREAM = "#f5f0e8"
TEXT_LIGHT = "#e0e0e0"
TEXT_DIM = "#9e9e9e"
BORDER = "#2a2a4a"

APP_CSS = """
<style>
/* ── global ─────────────────────────────────────────────────────────── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --navy: %(navy)s;
    --dark-bg: %(dark_bg)s;
    --card-bg: %(card_bg)s;
    --gold: %(gold)s;
    --blue: %(blue)s;
    --green: %(green)s;
    --orange: %(orange)s;
    --red: %(red)s;
    --cream: %(cream)s;
    --text-light: %(text_light)s;
    --text-dim: %(text_dim)s;
    --border: %(border)s;
}

/* ── header ─────────────────────────────────────────────────────────── */
.app-header {
    background: linear-gradient(135deg, #1a1a2e 0%%, #16213e 100%%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 20px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.3);
}
.app-header .logo {
    font-size: 3em;
    filter: drop-shadow(0 0 4px rgba(184,150,12,0.2));
}
.app-header .title-block h1 {
    font-family: 'Inter', sans-serif;
    font-weight: 700;
    font-size: 1.8em;
    color: var(--gold);
    margin: 0;
    letter-spacing: -0.5px;
}
.app-header .title-block p {
    font-family: 'Inter', sans-serif;
    color: var(--text-dim);
    margin: 4px 0 0 0;
    font-size: 0.95em;
}
.app-header .badges {
    margin-left: auto;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
}
.badge {
    display: inline-block;
    font-family: 'Inter', sans-serif;
    font-size: 0.75em;
    font-weight: 600;
    padding: 4px 10px;
    border-radius: 20px;
    letter-spacing: 0.3px;
}
.badge-gold { background: rgba(184,150,12,0.15); color: var(--gold); border: 1px solid rgba(184,150,12,0.3); }
.badge-blue { background: rgba(79,195,247,0.12); color: var(--blue); border: 1px solid rgba(79,195,247,0.25); }
.badge-green { background: rgba(76,175,80,0.12); color: var(--green); border: 1px solid rgba(76,175,80,0.25); }

/* ── sidebar ────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0e1117 0%%, #1a1a2e 100%%);
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    color: var(--gold) !important;
}

/* ── chat messages ──────────────────────────────────────────────────── */
div[data-testid="stChatMessage"] {
    border-radius: 16px;
    padding: 16px 20px;
    margin: 8px 0;
    border: 1px solid var(--border);
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
    transition: all 0.2s ease;
}
div[data-testid="stChatMessage"]:hover {
    box-shadow: 0 4px 16px rgba(0,0,0,0.25);
}

/* user messages */
div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) {
    background: linear-gradient(135deg, rgba(79,195,247,0.08) 0%%, rgba(79,195,247,0.03) 100%%);
    border-left: 3px solid var(--blue);
}
/* assistant messages */
div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) {
    background: linear-gradient(135deg, rgba(184,150,12,0.06) 0%%, rgba(184,150,12,0.02) 100%%);
    border-left: 3px solid var(--gold);
}

/* ── answer cards ───────────────────────────────────────────────────── */
.answer-card {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    margin: 12px 0;
    box-shadow: 0 2px 12px rgba(0,0,0,0.2);
}
.answer-card.legal {
    border-left: 4px solid var(--gold);
}
.answer-card.simple {
    border-left: 4px solid var(--blue);
}
.answer-card.error-card {
    border-left: 4px solid #ef5350;
    background: rgba(239, 83, 80, 0.08);
    border-color: rgba(239, 83, 80, 0.35);
}
.answer-card.error-card h4 { color: #ef5350; }
.answer-card.error-card .content { color: #ffaaaa; }
.answer-card .error-detail {
    margin-top: 10px;
    padding-top: 10px;
    border-top: 1px dashed rgba(239, 83, 80, 0.35);
    color: #d98080;
    font-size: 0.82em;
    font-family: 'JetBrains Mono', monospace;
    word-break: break-word;
}
.answer-card h4 {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 0.85em;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin: 0 0 10px 0;
}
.answer-card.legal h4 { color: var(--gold); }
.answer-card.simple h4 { color: var(--blue); }
.answer-card .content {
    font-family: 'Inter', sans-serif;
    color: var(--text-light);
    line-height: 1.7;
    font-size: 0.95em;
}
.answer-card.legal .content {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.88em;
    color: #c8d6c8;
}

/* ── citation chips ─────────────────────────────────────────────────── */
.citation-chip {
    display: inline-block;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.8em;
    font-weight: 500;
    background: rgba(79,195,247,0.1);
    color: var(--blue);
    border: 1px solid rgba(79,195,247,0.25);
    border-radius: 20px;
    padding: 2px 10px;
    margin: 2px 3px;
    transition: all 0.2s ease;
    cursor: default;
}
.citation-chip:hover {
    background: rgba(79,195,247,0.2);
    box-shadow: 0 0 8px rgba(79,195,247,0.15);
}

/* ── badges ─────────────────────────────────────────────────────────── */
.status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    font-family: 'Inter', sans-serif;
    font-size: 0.82em;
    font-weight: 600;
    padding: 6px 14px;
    border-radius: 20px;
    letter-spacing: 0.3px;
}
.status-pass {
    background: rgba(76,175,80,0.12);
    color: var(--green);
    border: 1px solid rgba(76,175,80,0.3);
}
.status-fail {
    background: rgba(255,152,0,0.12);
    color: var(--orange);
    border: 1px solid rgba(255,152,0,0.3);
}
.status-refuse {
    background: rgba(239,83,80,0.12);
    color: var(--red);
    border: 1px solid rgba(239,83,80,0.3);
}

/* ── info panel ─────────────────────────────────────────────────────── */
.info-panel {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px;
    margin: 8px 0;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
}
.info-panel h3 {
    font-family: 'Inter', sans-serif;
    font-weight: 600;
    font-size: 0.85em;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: var(--gold);
    margin: 0 0 12px 0;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border);
}
.info-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 6px 0;
    font-family: 'Inter', sans-serif;
    font-size: 0.85em;
}
.info-row .label { color: var(--text-dim); }
.info-row .value { color: var(--text-light); font-weight: 500; }

/* ── pipeline stages ────────────────────────────────────────────────── */
.pipeline-stages {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin: 12px 0;
}
.stage {
    display: flex;
    align-items: center;
    gap: 5px;
    font-family: 'Inter', sans-serif;
    font-size: 0.78em;
    font-weight: 500;
    padding: 5px 10px;
    border-radius: 8px;
    background: rgba(255,255,255,0.04);
    color: var(--text-dim);
    border: 1px solid transparent;
    transition: all 0.3s ease;
}
.stage.active {
    background: rgba(184,150,12,0.1);
    color: var(--gold);
    border-color: rgba(184,150,12,0.3);
    animation: pulse 1.5s infinite;
}
.stage.done {
    background: rgba(76,175,80,0.08);
    color: var(--green);
    border-color: rgba(76,175,80,0.2);
}

@keyframes pulse {
    0%%, 100%% { opacity: 1; }
    50%% { opacity: 0.6; }
}

/* ── equivalence table ──────────────────────────────────────────────── */
.equiv-table {
    width: 100%%;
    border-collapse: collapse;
    font-family: 'Inter', sans-serif;
    font-size: 0.85em;
    margin: 8px 0;
}
.equiv-table th {
    color: var(--gold);
    font-weight: 600;
    text-align: left;
    padding: 8px 12px;
    border-bottom: 2px solid var(--border);
    font-size: 0.9em;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.equiv-table td {
    padding: 8px 12px;
    color: var(--text-light);
    border-bottom: 1px solid rgba(255,255,255,0.05);
}
.equiv-table tr:hover td {
    background: rgba(184,150,12,0.04);
}
.equiv-arrow {
    color: var(--gold);
    font-weight: 700;
    font-size: 1.1em;
}

/* ── loading animation ──────────────────────────────────────────────── */
.loading-container {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    padding: 24px;
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    margin: 16px 0;
}
.loading-spinner {
    width: 40px;
    height: 40px;
    border: 3px solid var(--border);
    border-top-color: var(--gold);
    border-radius: 50%%;
    animation: spin 0.8s linear infinite;
}
@keyframes spin {
    to { transform: rotate(360deg); }
}
.loading-text {
    font-family: 'Inter', sans-serif;
    color: var(--text-dim);
    font-size: 0.9em;
    animation: pulse 1.5s infinite;
}

/* ── disclaimer ─────────────────────────────────────────────────────── */
.disclaimer {
    font-family: 'Inter', sans-serif;
    color: var(--text-dim);
    font-size: 0.8em;
    text-align: center;
    padding: 16px;
    border-top: 1px solid var(--border);
    margin-top: 24px;
}

/* ── stChatInput styling ────────────────────────────────────────────── */
div[data-testid="stChatInput"] {
    border-radius: 16px;
    border: 1px solid var(--border);
    background: var(--card-bg);
    box-shadow: 0 2px 12px rgba(0,0,0,0.2);
}
div[data-testid="stChatInput"]:focus-within {
    border-color: var(--gold);
    box-shadow: 0 0 0 2px rgba(184,150,12,0.15);
}

/* ── expander ───────────────────────────────────────────────────────── */
details[data-testid="stExpander"] {
    background: var(--card-bg);
    border: 1px solid var(--border);
    border-radius: 12px;
    overflow: hidden;
}
details[data-testid="stExpander"] summary {
    font-family: 'Inter', sans-serif;
    font-weight: 500;
    color: var(--text-light);
    padding: 12px 16px;
}

/* ── equity row (sidebar health) ─────────────────────────────────────── */
.health-pill {
    display: flex;
    align-items: center;
    gap: 8px;
    font-family: 'Inter', sans-serif;
    font-size: 0.78em;
    padding: 6px 10px;
    margin: 4px 0;
    border-radius: 8px;
    background: rgba(255,255,255,0.03);
    border: 1px solid var(--border);
}
.health-pill .dot {
    width: 9px;
    height: 9px;
    border-radius: 50%%;
    flex-shrink: 0;
}
.health-pill .dot.ok { background: var(--green); box-shadow: 0 0 6px rgba(76,175,80,0.6); }
.health-pill .dot.bad { background: var(--red); box-shadow: 0 0 6px rgba(239,83,80,0.6); }
.health-pill .hname { color: var(--text-dim); font-weight: 600; }
.health-pill .hmsg { color: var(--text-light); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* ── divider ────────────────────────────────────────────────────────── */
hr {
    border: none;
    border-top: 1px solid var(--border);
    margin: 16px 0;
}

/* ── general streamlit overrides ────────────────────────────────────── */
.stMarkdown {
    font-family: 'Inter', sans-serif;
    color: var(--text-light);
}
.stCaption {
    font-family: 'Inter', sans-serif;
    color: var(--text-dim) !important;
}
</style>
""" % {
    "navy": NAVY,
    "dark_bg": DARK_BG,
    "card_bg": CARD_BG,
    "gold": GOLD,
    "blue": BLUE,
    "green": GREEN,
    "orange": ORANGE,
    "red": RED,
    "cream": CREAM,
    "text_light": TEXT_LIGHT,
    "text_dim": TEXT_DIM,
    "border": BORDER,
}


def header_html():
    """Render the app header bar."""
    return """
<div class="app-header">
    <div class="logo">&#9878;</div>
    <div class="title-block">
        <h1>Kautilya</h1>
        <p>Time-Aware Legal RAG over Indian Law</p>
    </div>
    <div class="badges">
        <span class="badge badge-gold">BNS / BNSS / BSA</span>
        <span class="badge badge-blue">8 Languages</span>
        <span class="badge badge-green">NLI Verified</span>
    </div>
</div>
"""


def answer_card_html(register: str, title: str, content: str) -> str:
    """Render a styled answer card."""
    css_class = "legal" if register == "legal" else "simple"
    return f"""
<div class="answer-card {css_class}">
    <h4>{title}</h4>
    <div class="content">{content}</div>
</div>
"""


def error_card_html(error: str, detail: str = "") -> str:
    """Render a styled error card for LLM/answer failures."""
    detail_html = f'<div class="error-detail">{detail}</div>' if detail else ""
    return f"""
<div class="answer-card error-card">
    <h4>&#9888;&#65039; Could not generate the answer</h4>
    <div class="content">{error}</div>
    {detail_html}
</div>
"""


def citation_chips_html(citations: list[str]) -> str:
    """Render citations as styled chips."""
    if not citations:
        return ""
    chips = "".join(f'<span class="citation-chip">{c}</span>' for c in citations)
    return f'<div style="margin: 8px 0;">{chips}</div>'


def status_badge_html(verification: str) -> str:
    """Render verification status badge."""
    if verification == "pass":
        return '<span class="status-badge status-pass">&#10003; Verified</span>'
    elif verification == "fail":
        return '<span class="status-badge status-fail">&#9888; Unverified</span>'
    return ""


def stage_progress_html(active_idx: int, labels: list[str],
                        elapsed: float) -> str:
    """Render pipeline stage chips (done / active / pending) for live UX."""
    chips = ""
    for i, label in enumerate(labels):
        cls = "stage done" if i < active_idx else "stage active" if i == active_idx else "stage"
        mark = "&#10003;" if i < active_idx else ("&#9679;" if i == active_idx else "&#9637;")
        chips += f'<span class="{cls}">{mark}&nbsp;{label}</span>'
    return f"""
<div class="pipeline-stages">{chips}</div>
<div class="stage-elapsed" style="font-family:'Inter',sans-serif;
     color:var(--text-dim); font-size:0.78em; margin: 4px 0 12px 0;">
    &#9201; {elapsed:.1f}s elapsed</div>
"""


def health_pill_html(name: str, ok: bool, msg: str) -> str:
    """Render a sidebar status pill (live backend health)."""
    dot = "ok" if ok else "bad"
    return (f'<div class="health-pill"><span class="dot {dot}"></span>'
            f'<span class="hname">{name}</span>'
            f'<span class="hmsg">{msg}</span></div>')


def equivalence_table_html(equivalences) -> str:
    """Render equivalences as a styled table."""
    if not equivalences:
        return ""
    rows = ""
    for e in equivalences:
        rows += f"<tr><td>{e.old_id}</td><td class='equiv-arrow'>&rarr;</td><td>{e.note}</td></tr>"
    return f"""
<table class="equiv-table">
<thead><tr><th>Old</th><th></th><th>Mapping</th></tr></thead>
<tbody>{rows}</tbody>
</table>
"""


def info_panel_html(result: dict) -> str:
    """Render the side info panel with pipeline results."""
    route = result.get("route", "")
    verification = result.get("verification", "")
    citations = result.get("citations", [])
    regimes = result.get("regimes", {})

    regime_bads = ""
    for domain, regime in regimes.items():
        color = "green" if regime == "current" else "blue"
        label = regime.upper()
        regime_bads += f'<span class="badge badge-{color}" style="font-size:0.7em">{domain}: {label}</span> '

    return f"""
<div class="info-panel">
    <h3>Pipeline Status</h3>
    <div class="info-row">
        <span class="label">Route</span>
        <span class="value">{route or 'answer'}</span>
    </div>
    <div class="info-row">
        <span class="label">Verification</span>
        <span class="value">{status_badge_html(verification) or 'Skipped'}</span>
    </div>
    <div class="info-row">
        <span class="label">Citations</span>
        <span class="value">{len(citations)}</span>
    </div>
</div>

<div class="info-panel">
    <h3>Regime Routing</h3>
    {regime_bads or '<span style="color:var(--text-dim);font-size:0.85em">General</span>'}
</div>

<div class="info-panel">
    <h3>Sources</h3>
    {citation_chips_html(citations) or '<span style="color:var(--text-dim);font-size:0.85em">No citations</span>'}
</div>
"""
