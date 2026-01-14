import streamlit as st
import anthropic
import base64
import json
import hashlib
from datetime import datetime
from pathlib import Path

# Optional imports
try:
    from streamlit_sortables import sort_items
    SORTABLES_AVAILABLE = True
except ImportError:
    SORTABLES_AVAILABLE = False

try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# ============================================================
# CONFIG
# ============================================================
st.set_page_config(
    page_title="CardForge",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_DIR = Path("cardforge_data")
DATA_DIR.mkdir(exist_ok=True)
HISTORY_FILE = DATA_DIR / "card_history.json"
STATS_FILE = DATA_DIR / "statistics.json"

# ============================================================
# DESIGN SYSTEM
# ============================================================
COLORS = {
    "light": {
        "bg": "#fafafa",
        "surface": "#ffffff",
        "surface_hover": "#f5f5f5",
        "primary": "#6366f1",
        "primary_light": "#818cf8",
        "primary_dark": "#4f46e5",
        "secondary": "#ec4899",
        "text": "#18181b",
        "text_muted": "#71717a",
        "border": "#e4e4e7",
        "success": "#10b981",
        "warning": "#f59e0b",
        "error": "#ef4444",
    },
    "dark": {
        "bg": "#09090b",
        "surface": "#18181b",
        "surface_hover": "#27272a",
        "primary": "#818cf8",
        "primary_light": "#a5b4fc",
        "primary_dark": "#6366f1",
        "secondary": "#f472b6",
        "text": "#fafafa",
        "text_muted": "#a1a1aa",
        "border": "#27272a",
        "success": "#34d399",
        "warning": "#fbbf24",
        "error": "#f87171",
    }
}

def get_css(theme="light"):
    c = COLORS[theme]
    return f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    /* Global Reset */
    .stApp {{
        background: {c['bg']};
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }}

    /* Hide Streamlit branding */
    #MainMenu, footer, header {{visibility: hidden;}}
    .stDeployButton {{display: none;}}

    /* Typography */
    h1, h2, h3, h4, h5, h6, p, span, div {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }}

    /* Brand Header */
    .brand {{
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 8px 0 24px 0;
    }}

    .brand-icon {{
        width: 40px;
        height: 40px;
        background: linear-gradient(135deg, {c['primary']} 0%, {c['secondary']} 100%);
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        color: white;
        font-weight: 700;
    }}

    .brand-text {{
        font-size: 24px;
        font-weight: 700;
        color: {c['text']};
        letter-spacing: -0.5px;
    }}

    /* Section Headers */
    .section-header {{
        font-size: 13px;
        font-weight: 600;
        color: {c['text_muted']};
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin: 24px 0 12px 0;
    }}

    /* Cards */
    .card {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 16px;
        padding: 20px;
        margin: 12px 0;
        transition: all 0.2s ease;
    }}

    .card:hover {{
        border-color: {c['primary']};
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.1);
    }}

    .card-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }}

    .card-number {{
        font-size: 12px;
        font-weight: 600;
        color: {c['primary']};
        background: {c['primary']}15;
        padding: 4px 10px;
        border-radius: 20px;
    }}

    .card-quality {{
        display: flex;
        gap: 2px;
    }}

    .star {{
        color: {c['warning']};
        font-size: 14px;
    }}

    .star-empty {{
        color: {c['border']};
        font-size: 14px;
    }}

    /* Flip Card */
    .flip-container {{
        perspective: 1000px;
        margin: 16px 0;
    }}

    .flip-card {{
        width: 100%;
        height: 180px;
        position: relative;
        transform-style: preserve-3d;
        transition: transform 0.6s cubic-bezier(0.4, 0, 0.2, 1);
        cursor: pointer;
    }}

    .flip-card.flipped {{
        transform: rotateY(180deg);
    }}

    .flip-face {{
        position: absolute;
        width: 100%;
        height: 100%;
        backface-visibility: hidden;
        border-radius: 16px;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 24px;
        text-align: center;
        font-size: 15px;
        line-height: 1.5;
    }}

    .flip-front {{
        background: linear-gradient(135deg, {c['primary']} 0%, {c['primary_dark']} 100%);
        color: white;
        font-weight: 500;
    }}

    .flip-back {{
        background: {c['surface']};
        border: 2px solid {c['primary']};
        color: {c['text']};
        transform: rotateY(180deg);
    }}

    .flip-hint {{
        font-size: 12px;
        color: {c['text_muted']};
        text-align: center;
        margin-top: 8px;
    }}

    /* Stats Grid */
    .stats-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 16px;
        margin: 16px 0;
    }}

    .stat-card {{
        background: {c['surface']};
        border: 1px solid {c['border']};
        border-radius: 16px;
        padding: 20px;
        text-align: center;
    }}

    .stat-value {{
        font-size: 32px;
        font-weight: 700;
        background: linear-gradient(135deg, {c['primary']} 0%, {c['secondary']} 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }}

    .stat-label {{
        font-size: 13px;
        color: {c['text_muted']};
        margin-top: 4px;
    }}

    /* Progress Bar */
    .progress-container {{
        margin: 8px 0;
    }}

    .progress-label {{
        display: flex;
        justify-content: space-between;
        font-size: 13px;
        margin-bottom: 6px;
    }}

    .progress-name {{
        color: {c['text']};
        font-weight: 500;
    }}

    .progress-value {{
        color: {c['text_muted']};
    }}

    .progress-bar {{
        height: 8px;
        background: {c['border']};
        border-radius: 4px;
        overflow: hidden;
    }}

    .progress-fill {{
        height: 100%;
        background: linear-gradient(90deg, {c['primary']} 0%, {c['secondary']} 100%);
        border-radius: 4px;
        transition: width 0.3s ease;
    }}

    /* Badges */
    .badge {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 13px;
        font-weight: 500;
    }}

    .badge-success {{
        background: {c['success']}15;
        color: {c['success']};
    }}

    .badge-warning {{
        background: {c['warning']}15;
        color: {c['warning']};
    }}

    .badge-error {{
        background: {c['error']}15;
        color: {c['error']};
    }}

    .badge-primary {{
        background: {c['primary']}15;
        color: {c['primary']};
    }}

    /* Empty State */
    .empty-state {{
        text-align: center;
        padding: 48px 24px;
        color: {c['text_muted']};
    }}

    .empty-icon {{
        font-size: 48px;
        margin-bottom: 16px;
        opacity: 0.5;
    }}

    .empty-title {{
        font-size: 18px;
        font-weight: 600;
        color: {c['text']};
        margin-bottom: 8px;
    }}

    .empty-desc {{
        font-size: 14px;
        max-width: 300px;
        margin: 0 auto;
    }}

    /* Sidebar Styling */
    section[data-testid="stSidebar"] {{
        background: {c['surface']};
        border-right: 1px solid {c['border']};
    }}

    section[data-testid="stSidebar"] .block-container {{
        padding: 24px 16px;
    }}

    /* Input Styling */
    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div {{
        border-radius: 12px !important;
        border-color: {c['border']} !important;
        font-family: 'Inter', sans-serif !important;
    }}

    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {{
        border-color: {c['primary']} !important;
        box-shadow: 0 0 0 3px {c['primary']}20 !important;
    }}

    /* Button Styling */
    .stButton > button {{
        border-radius: 12px !important;
        font-weight: 600 !important;
        font-family: 'Inter', sans-serif !important;
        padding: 12px 24px !important;
        transition: all 0.2s ease !important;
    }}

    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, {c['primary']} 0%, {c['primary_dark']} 100%) !important;
        border: none !important;
    }}

    .stButton > button[kind="primary"]:hover {{
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 12px {c['primary']}40 !important;
    }}

    /* Expander Styling */
    .streamlit-expanderHeader {{
        background: {c['surface']} !important;
        border: 1px solid {c['border']} !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
    }}

    .streamlit-expanderContent {{
        border: 1px solid {c['border']} !important;
        border-top: none !important;
        border-radius: 0 0 12px 12px !important;
    }}

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 0;
        background: {c['surface']};
        border-radius: 12px;
        padding: 4px;
        border: 1px solid {c['border']};
    }}

    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px;
        padding: 12px 20px;
        font-weight: 500;
        color: {c['text_muted']};
    }}

    .stTabs [aria-selected="true"] {{
        background: {c['primary']} !important;
        color: white !important;
    }}

    /* Metric Cards */
    [data-testid="stMetricValue"] {{
        font-size: 28px !important;
        font-weight: 700 !important;
    }}

    /* Download Button */
    .stDownloadButton > button {{
        border-radius: 12px !important;
        font-weight: 600 !important;
    }}

    /* Divider */
    hr {{
        border: none;
        border-top: 1px solid {c['border']};
        margin: 24px 0;
    }}

    /* Toggle */
    .stCheckbox label span {{
        font-weight: 500 !important;
    }}

    /* File Uploader */
    [data-testid="stFileUploader"] {{
        border-radius: 12px;
    }}

    [data-testid="stFileUploader"] section {{
        border-radius: 12px !important;
        border: 2px dashed {c['border']} !important;
        padding: 24px !important;
    }}

    [data-testid="stFileUploader"] section:hover {{
        border-color: {c['primary']} !important;
    }}

    /* Duplicate Warning */
    .duplicate-badge {{
        background: {c['warning']}15;
        color: {c['warning']};
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 500;
    }}
</style>
"""

# ============================================================
# STATE & PERSISTENCE
# ============================================================
def init_state():
    defaults = {
        "cards": [],
        "generated": False,
        "theme": "light",
        "history": [],
        "stats": {"total": 0, "by_subject": {}, "by_date": {}, "sessions": 0},
        "show_explanations": True,
        "bulk_mode": False,
        "preview_mode": False,
        "reorder_mode": False,
        "anki_connected": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v
    load_data()

def load_data():
    if HISTORY_FILE.exists():
        try:
            st.session_state.history = json.loads(HISTORY_FILE.read_text())
        except:
            pass
    if STATS_FILE.exists():
        try:
            st.session_state.stats = json.loads(STATS_FILE.read_text())
        except:
            pass

def save_data():
    HISTORY_FILE.write_text(json.dumps(st.session_state.history, indent=2))
    STATS_FILE.write_text(json.dumps(st.session_state.stats, indent=2))

def update_stats(count, subject):
    s = st.session_state.stats
    s["total"] += count
    s["sessions"] += 1
    s["by_subject"][subject] = s["by_subject"].get(subject, 0) + count
    today = datetime.now().strftime("%Y-%m-%d")
    s["by_date"][today] = s["by_date"].get(today, 0) + count
    save_data()

# ============================================================
# EXAM CONFIGS
# ============================================================
EXAMS = {
    "Auto-Detect": "Analyze content and determine the best approach.",
    "MCAT": "Focus on foundational sciences, AAMC high-yield topics.",
    "USMLE Step 1": "First Aid facts, pathophysiology, pharmacology.",
    "USMLE Step 2": "Clinical management, diagnosis, treatment.",
    "Medical School": "Mechanisms, pathways, integration.",
    "Nursing (NCLEX)": "Patient safety, prioritization, interventions.",
    "PA School": "Clinical medicine across specialties.",
    "Pharmacy": "Drug interactions, dosing, counseling.",
    "General": "Foundational concepts for any topic.",
}

FORMATS = {
    "Question & Answer": "Question\tAnswer",
    "Cloze (Fill-in-blank)": "Text with {{c1::hidden}} format",
    "Multiple Choice": "Question with A/B/C/D options",
    "Mixed": "Variety of all formats",
}

# ============================================================
# UTILITIES
# ============================================================
def get_hash(front, back):
    return hashlib.md5(f"{front.lower()}{back.lower()}".encode()).hexdigest()[:8]

def similarity(a, b):
    wa, wb = set(a.lower().split()), set(b.lower().split())
    if not wa or not wb:
        return 0
    return len(wa & wb) / len(wa | wb)

def find_duplicates(new_cards, existing):
    hashes = {get_hash(c["front"], c["back"]) for c in existing}
    dupes = []
    for i, card in enumerate(new_cards):
        if get_hash(card["front"], card["back"]) in hashes:
            dupes.append(i)
        elif any(similarity(card["front"], e["front"]) > 0.7 for e in existing):
            dupes.append(i)
    return dupes

def quality_score(card):
    score = 3
    f, b = card.get("front", ""), card.get("back", "")
    if 10 < len(f) < 200: score += 0.5
    if 5 < len(b) < 500: score += 0.5
    bad = ["the passage", "the figure", "the graph", "this question"]
    for p in bad:
        if p in f.lower() or p in b.lower(): score -= 1
    good = ["what", "how", "why", "which", "define", "explain"]
    if any(f.lower().startswith(w) for w in good): score += 0.5
    return max(1, min(5, round(score)))

def extract_pdf(file):
    if not PDF_AVAILABLE:
        return None
    try:
        reader = PyPDF2.PdfReader(file)
        return "\n\n".join(p.extract_text() for p in reader.pages)
    except:
        return None

def check_anki():
    try:
        import urllib.request
        req = urllib.request.Request(
            "http://localhost:8765",
            data=json.dumps({"action": "version", "version": 6}).encode()
        )
        resp = urllib.request.urlopen(req, timeout=1)
        return json.loads(resp.read())
    except:
        return None

def send_to_anki(cards, deck, tags):
    try:
        import urllib.request
        # Create deck
        urllib.request.urlopen(urllib.request.Request(
            "http://localhost:8765",
            data=json.dumps({"action": "createDeck", "version": 6, "params": {"deck": deck}}).encode()
        ), timeout=5)
        # Add notes
        notes = [{
            "deckName": deck,
            "modelName": "Basic",
            "fields": {"Front": c["front"], "Back": c["back"]},
            "tags": [t.strip() for t in tags.split(",")] if tags else []
        } for c in cards]
        resp = urllib.request.urlopen(urllib.request.Request(
            "http://localhost:8765",
            data=json.dumps({"action": "addNotes", "version": 6, "params": {"notes": notes}}).encode()
        ), timeout=10)
        return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# AI FUNCTIONS
# ============================================================
def detect_subject(client, content):
    try:
        resp = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[{"role": "user", "content": f"Categorize this content. Reply with ONLY one: MCAT, USMLE Step 1, USMLE Step 2, Medical School, Nursing (NCLEX), PA School, Pharmacy, General\n\n{content[:800]}"}]
        )
        detected = resp.content[0].text.strip()
        return detected if detected in EXAMS else "General"
    except:
        return "General"

def generate_cards(client, content, settings):
    prompt = f"""Create {settings['count']} Anki flashcards from this content.

RULES:
- Focus on transferable concepts, not specific question details
- Each card tests ONE clear concept
- Avoid references to "the passage" or "the figure"
- Make cards useful for anyone studying this topic

CONTEXT: {EXAMS[settings['exam']]}
FORMAT: {FORMATS[settings['format']]}
DIFFICULTY: {settings['difficulty']}

{"USER NOTE: " + settings['instructions'] if settings['instructions'] else ""}

For each card, output:
CARD: [front]<TAB>[back]
WHY: [one sentence explaining the concept tested]

Content:
{content}"""

    if settings.get("is_image"):
        messages = [{"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": content}}, {"type": "text", "text": prompt}]
    else:
        messages = [{"type": "text", "text": prompt}]

    resp = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        messages=[{"role": "user", "content": messages}]
    )

    # Parse response
    cards = []
    lines = resp.content[0].text.strip().split("\n")
    current = None

    for line in lines:
        line = line.strip()
        if line.startswith("CARD:"):
            content = line[5:].strip()
            if "\t" in content:
                parts = content.split("\t")
                current = {"front": parts[0].strip(), "back": parts[1].strip() if len(parts) > 1 else "", "keep": True, "explanation": ""}
            elif "<TAB>" in content:
                parts = content.split("<TAB>")
                current = {"front": parts[0].strip(), "back": parts[1].strip() if len(parts) > 1 else "", "keep": True, "explanation": ""}
        elif line.startswith("WHY:") and current:
            current["explanation"] = line[4:].strip()
            current["quality"] = quality_score(current)
            cards.append(current)
            current = None

    # Fallback parsing
    if not cards:
        for line in lines:
            if "\t" in line and not line.startswith(("CARD:", "WHY:")):
                parts = line.split("\t")
                card = {"front": parts[0].strip(), "back": parts[1].strip() if len(parts) > 1 else "", "keep": True, "explanation": "", "quality": 3}
                card["quality"] = quality_score(card)
                cards.append(card)

    return cards

# ============================================================
# UI COMPONENTS
# ============================================================
def render_brand():
    st.markdown("""
        <div class="brand">
            <div class="brand-icon">⚡</div>
            <span class="brand-text">CardForge</span>
        </div>
    """, unsafe_allow_html=True)

def render_stars(score):
    filled = "★" * score
    empty = "★" * (5 - score)
    return f'<span class="star">{filled}</span><span class="star-empty">{empty}</span>'

def render_flip_card(card, idx):
    front = card['front'][:120] + "..." if len(card['front']) > 120 else card['front']
    back = card['back'][:120] + "..." if len(card['back']) > 120 else card['back']
    st.markdown(f"""
        <div class="flip-container">
            <div class="flip-card" onclick="this.classList.toggle('flipped')">
                <div class="flip-face flip-front">{front}</div>
                <div class="flip-face flip-back">{back}</div>
            </div>
        </div>
        <p class="flip-hint">Click to flip</p>
    """, unsafe_allow_html=True)

def render_card_editor(card, idx):
    col1, col2 = st.columns([0.06, 0.94])

    with col1:
        card["keep"] = st.checkbox("", value=card.get("keep", True), key=f"keep_{idx}", label_visibility="collapsed")

    with col2:
        is_dupe = card.get("is_duplicate", False)
        q = card.get("quality", 3)

        preview = card['front'][:60] + "..." if len(card['front']) > 60 else card['front']
        header = f"Card {idx + 1}"

        with st.expander(header, expanded=False):
            if is_dupe:
                st.markdown('<span class="duplicate-badge">Possible duplicate</span>', unsafe_allow_html=True)

            st.markdown(f"Quality: {render_stars(q)}", unsafe_allow_html=True)

            card["front"] = st.text_area("Front", value=card["front"], key=f"front_{idx}", height=80, label_visibility="collapsed", placeholder="Front of card...")
            card["back"] = st.text_area("Back", value=card["back"], key=f"back_{idx}", height=80, label_visibility="collapsed", placeholder="Back of card...")

            if card.get("explanation") and st.session_state.show_explanations:
                st.caption(f"💡 {card['explanation']}")

    return card

def render_stats():
    s = st.session_state.stats

    st.markdown('<div class="section-header">Overview</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{s.get('total', 0)}</div>
                <div class="stat-label">Cards Created</div>
            </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value">{s.get('sessions', 0)}</div>
                <div class="stat-label">Sessions</div>
            </div>
        """, unsafe_allow_html=True)
    with col3:
        top = max(s.get("by_subject", {"None": 0}), key=s.get("by_subject", {}).get, default="None")
        st.markdown(f"""
            <div class="stat-card">
                <div class="stat-value" style="font-size: 20px;">{top}</div>
                <div class="stat-label">Top Subject</div>
            </div>
        """, unsafe_allow_html=True)

    if s.get("by_subject"):
        st.markdown('<div class="section-header">By Subject</div>', unsafe_allow_html=True)
        max_val = max(s["by_subject"].values())
        for subj, count in sorted(s["by_subject"].items(), key=lambda x: -x[1]):
            pct = (count / max_val) * 100
            st.markdown(f"""
                <div class="progress-container">
                    <div class="progress-label">
                        <span class="progress-name">{subj}</span>
                        <span class="progress-value">{count} cards</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: {pct}%"></div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

def render_history():
    if not st.session_state.history:
        st.markdown("""
            <div class="empty-state">
                <div class="empty-icon">📚</div>
                <div class="empty-title">No cards yet</div>
                <div class="empty-desc">Cards you create will appear here for easy access later.</div>
            </div>
        """, unsafe_allow_html=True)
        return

    search = st.text_input("Search cards", placeholder="Type to filter...", label_visibility="collapsed")

    filtered = st.session_state.history
    if search:
        filtered = [h for h in filtered if search.lower() in h.get("front", "").lower() or search.lower() in h.get("back", "").lower()]

    st.caption(f"Showing {len(filtered)} of {len(st.session_state.history)} cards")

    for i, card in enumerate(filtered[-30:]):
        with st.expander(f"{card.get('front', '')[:50]}..."):
            st.markdown(f"**Front:** {card.get('front', '')}")
            st.markdown(f"**Back:** {card.get('back', '')}")
            st.caption(f"{card.get('subject', 'General')} · {card.get('created', '')}")

# ============================================================
# MAIN APP
# ============================================================
def main():
    init_state()

    # Apply theme
    st.markdown(get_css(st.session_state.theme), unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        render_brand()

        # API Key
        st.markdown('<div class="section-header">API Key</div>', unsafe_allow_html=True)
        api_key = st.text_input("Anthropic API Key", type="password", label_visibility="collapsed", placeholder="sk-ant-...")

        if api_key:
            st.markdown('<span class="badge badge-success">Connected</span>', unsafe_allow_html=True)
        else:
            st.caption("Get your key at [console.anthropic.com](https://console.anthropic.com)")

        # Settings
        st.markdown('<div class="section-header">Card Settings</div>', unsafe_allow_html=True)

        exam = st.selectbox("Subject", list(EXAMS.keys()), label_visibility="collapsed")
        card_format = st.selectbox("Format", list(FORMATS.keys()), label_visibility="collapsed")
        num_cards = st.slider("Number of cards", 1, 15, 5)
        difficulty = st.select_slider("Difficulty", ["Basic", "Standard", "Advanced", "Expert"], value="Standard")

        # Export Settings
        st.markdown('<div class="section-header">Export</div>', unsafe_allow_html=True)
        deck_name = st.text_input("Deck name", value="My Cards", label_visibility="collapsed", placeholder="Deck name")
        tags = st.text_input("Tags", label_visibility="collapsed", placeholder="tag1, tag2, tag3")

        # Options
        st.markdown('<div class="section-header">Options</div>', unsafe_allow_html=True)
        st.session_state.show_explanations = st.toggle("Show explanations", value=True)
        st.session_state.bulk_mode = st.toggle("Bulk mode", value=False)
        st.session_state.preview_mode = st.toggle("Preview mode", value=False)

        # Theme toggle
        st.markdown('<div class="section-header">Appearance</div>', unsafe_allow_html=True)
        if st.toggle("Dark mode", value=st.session_state.theme == "dark"):
            st.session_state.theme = "dark"
        else:
            st.session_state.theme = "light"

        # Anki status
        anki = check_anki()
        if anki:
            st.markdown('<span class="badge badge-success">Anki Connected</span>', unsafe_allow_html=True)
            st.session_state.anki_connected = True
        else:
            st.session_state.anki_connected = False

    # Main content
    tab1, tab2, tab3 = st.tabs(["Create", "History", "Stats"])

    with tab1:
        col1, col2 = st.columns([1, 1], gap="large")

        with col1:
            st.markdown('<div class="section-header">Input</div>', unsafe_allow_html=True)

            input_type = st.radio(
                "Input type",
                ["Screenshot", "Text", "PDF"] if PDF_AVAILABLE else ["Screenshot", "Text"],
                horizontal=True,
                label_visibility="collapsed"
            )

            uploaded_files = []
            text_input = None
            pdf_text = None

            if input_type == "Screenshot":
                if st.session_state.bulk_mode:
                    uploaded_files = st.file_uploader("Upload screenshots", type=["png", "jpg", "jpeg"], accept_multiple_files=True, label_visibility="collapsed")
                else:
                    f = st.file_uploader("Upload screenshot", type=["png", "jpg", "jpeg"], label_visibility="collapsed")
                    if f:
                        st.image(f, use_container_width=True)
                        uploaded_files = [f]

            elif input_type == "Text":
                placeholder = "Question 1...\n---\nQuestion 2..." if st.session_state.bulk_mode else "Paste the question you got wrong..."
                text_input = st.text_area("Content", height=200, label_visibility="collapsed", placeholder=placeholder)

            elif input_type == "PDF":
                pdf_file = st.file_uploader("Upload PDF", type=["pdf"], label_visibility="collapsed")
                if pdf_file:
                    pdf_text = extract_pdf(pdf_file)
                    if pdf_text:
                        st.success(f"Extracted {len(pdf_text):,} characters")
                    else:
                        st.error("Could not extract text from PDF")

            instructions = st.text_input("Special instructions (optional)", placeholder="Focus on..., I struggle with...", label_visibility="collapsed")

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                generate = st.button("Generate Cards", type="primary", use_container_width=True)
            with col_btn2:
                regenerate = st.button("Regenerate", use_container_width=True)

        with col2:
            st.markdown('<div class="section-header">Cards</div>', unsafe_allow_html=True)

            if generate or regenerate:
                if not api_key:
                    st.error("Please enter your API key")
                else:
                    # Collect inputs
                    inputs = []
                    if uploaded_files:
                        for f in uploaded_files:
                            f.seek(0)
                            inputs.append({"type": "image", "content": base64.b64encode(f.read()).decode()})
                    elif text_input:
                        if st.session_state.bulk_mode and "---" in text_input:
                            for q in text_input.split("---"):
                                if q.strip():
                                    inputs.append({"type": "text", "content": q.strip()})
                        else:
                            inputs.append({"type": "text", "content": text_input})
                    elif pdf_text:
                        inputs.append({"type": "text", "content": pdf_text})

                    if not inputs:
                        st.warning("Please provide some content first")
                    else:
                        try:
                            client = anthropic.Anthropic(api_key=api_key)

                            # Auto-detect if needed
                            actual_exam = exam
                            if exam == "Auto-Detect" and inputs:
                                with st.spinner("Detecting subject..."):
                                    sample = inputs[0]["content"][:800] if inputs[0]["type"] == "text" else ""
                                    actual_exam = detect_subject(client, sample)
                                    st.info(f"Detected: **{actual_exam}**")

                            settings = {
                                "exam": actual_exam,
                                "format": card_format,
                                "count": num_cards,
                                "difficulty": difficulty,
                                "instructions": instructions + (" Make cards more general." if regenerate else ""),
                                "is_image": False
                            }

                            st.session_state.cards = []

                            progress = st.progress(0)
                            for i, inp in enumerate(inputs):
                                progress.progress((i + 1) / len(inputs))
                                settings["is_image"] = inp["type"] == "image"

                                with st.spinner("Creating cards..."):
                                    new_cards = generate_cards(client, inp["content"], settings)

                                    # Check duplicates
                                    dupes = find_duplicates(new_cards, st.session_state.cards + st.session_state.history)
                                    for d in dupes:
                                        if d < len(new_cards):
                                            new_cards[d]["is_duplicate"] = True

                                    st.session_state.cards.extend(new_cards)

                            progress.empty()
                            st.session_state.generated = True

                            # Update stats & history
                            update_stats(len(st.session_state.cards), actual_exam)
                            for card in st.session_state.cards:
                                st.session_state.history.append({
                                    **card,
                                    "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                    "subject": actual_exam
                                })
                            save_data()

                        except anthropic.AuthenticationError:
                            st.error("Invalid API key")
                        except Exception as e:
                            st.error(f"Error: {e}")

            # Display cards
            if st.session_state.cards:
                if st.session_state.preview_mode:
                    cols = st.columns(2)
                    for i, card in enumerate(st.session_state.cards):
                        with cols[i % 2]:
                            render_flip_card(card, i)
                    st.divider()

                for i, card in enumerate(st.session_state.cards):
                    st.session_state.cards[i] = render_card_editor(card, i)

                # Stats bar
                kept = [c for c in st.session_state.cards if c.get("keep", True)]

                st.divider()

                mcol1, mcol2, mcol3 = st.columns(3)
                with mcol1:
                    st.metric("Total", len(st.session_state.cards))
                with mcol2:
                    st.metric("Selected", len(kept))
                with mcol3:
                    avg_q = sum(c.get("quality", 3) for c in kept) / len(kept) if kept else 0
                    st.metric("Avg Quality", f"{avg_q:.1f}★")

                # Export
                if kept:
                    st.divider()

                    ecol1, ecol2 = st.columns(2)

                    with ecol1:
                        tag_str = " ".join(f"tags:{t.strip()}" for t in tags.split(",")) if tags else ""
                        export = "\n".join(f"{c['front']}\t{c['back']}\t{tag_str}".strip() for c in kept)

                        st.download_button(
                            f"Download {len(kept)} cards",
                            export,
                            f"{deck_name.replace(' ', '_')}.txt",
                            "text/plain",
                            use_container_width=True
                        )

                    with ecol2:
                        if st.session_state.anki_connected:
                            if st.button(f"Send to Anki", use_container_width=True):
                                result = send_to_anki(kept, deck_name, tags)
                                if "error" in result:
                                    st.error(result["error"])
                                else:
                                    st.success("Sent to Anki!")
                        else:
                            st.button("Send to Anki", disabled=True, use_container_width=True)
                            st.caption("Open Anki with AnkiConnect")

            elif st.session_state.generated:
                st.info("No cards generated. Try different content.")
            else:
                st.markdown("""
                    <div class="empty-state">
                        <div class="empty-icon">✨</div>
                        <div class="empty-title">Ready to create</div>
                        <div class="empty-desc">Upload a screenshot or paste a question to generate flashcards.</div>
                    </div>
                """, unsafe_allow_html=True)

    with tab2:
        render_history()

    with tab3:
        render_stats()

if __name__ == "__main__":
    main()
