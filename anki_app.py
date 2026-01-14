import streamlit as st
import anthropic
import base64
import json
import hashlib
import re
from datetime import datetime
from pathlib import Path
import time

# Try to import sortables for drag-and-drop (optional)
try:
    from streamlit_sortables import sort_items
    SORTABLES_AVAILABLE = True
except ImportError:
    SORTABLES_AVAILABLE = False

# ============================================================
# PAGE CONFIG & CONSTANTS
# ============================================================
st.set_page_config(
    page_title="CardForge",
    page_icon="🎴",
    layout="wide",
    initial_sidebar_state="expanded"
)

DATA_DIR = Path("cardforge_data")
DATA_DIR.mkdir(exist_ok=True)
HISTORY_FILE = DATA_DIR / "card_history.json"
STATS_FILE = DATA_DIR / "statistics.json"

# ============================================================
# THEME CONFIGURATION
# ============================================================
THEMES = {
    "light": {
        "bg_primary": "#ffffff",
        "bg_secondary": "#f8f9fa",
        "bg_card": "#ffffff",
        "text_primary": "#1a1a2e",
        "text_secondary": "#666666",
        "accent": "#667eea",
        "accent_secondary": "#764ba2",
        "border": "#e0e0e0",
        "success": "#28a745",
        "warning": "#ffc107",
        "error": "#dc3545",
    },
    "dark": {
        "bg_primary": "#1a1a2e",
        "bg_secondary": "#16213e",
        "bg_card": "#0f3460",
        "text_primary": "#eaeaea",
        "text_secondary": "#b0b0b0",
        "accent": "#667eea",
        "accent_secondary": "#764ba2",
        "border": "#2a2a4a",
        "success": "#4ecca3",
        "warning": "#ffd369",
        "error": "#ff6b6b",
    }
}

def get_theme_css(theme_name):
    t = THEMES.get(theme_name, THEMES["light"])
    return f"""
    <style>
        /* Base Theme */
        .stApp {{
            background-color: {t['bg_primary']};
        }}

        .main-header {{
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(90deg, {t['accent']} 0%, {t['accent_secondary']} 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0;
        }}

        .sub-header {{
            font-size: 1.1rem;
            color: {t['text_secondary']};
            margin-bottom: 2rem;
        }}

        /* Card Styles */
        .card-container {{
            background: {t['bg_card']};
            border: 1px solid {t['border']};
            border-radius: 12px;
            padding: 1rem;
            margin: 0.5rem 0;
            transition: all 0.3s ease;
        }}

        .card-container:hover {{
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
            transform: translateY(-2px);
        }}

        /* Flip Card Animation */
        .flip-card {{
            background-color: transparent;
            width: 100%;
            height: 200px;
            perspective: 1000px;
            cursor: pointer;
        }}

        .flip-card-inner {{
            position: relative;
            width: 100%;
            height: 100%;
            text-align: center;
            transition: transform 0.6s;
            transform-style: preserve-3d;
        }}

        .flip-card.flipped .flip-card-inner {{
            transform: rotateY(180deg);
        }}

        .flip-card-front, .flip-card-back {{
            position: absolute;
            width: 100%;
            height: 100%;
            -webkit-backface-visibility: hidden;
            backface-visibility: hidden;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 1rem;
            font-size: 1.1rem;
        }}

        .flip-card-front {{
            background: linear-gradient(135deg, {t['accent']} 0%, {t['accent_secondary']} 100%);
            color: white;
        }}

        .flip-card-back {{
            background: {t['bg_card']};
            border: 2px solid {t['accent']};
            color: {t['text_primary']};
            transform: rotateY(180deg);
        }}

        /* Quality Score Stars */
        .quality-stars {{
            color: {t['warning']};
            font-size: 1.2rem;
        }}

        /* Stats Cards */
        .stat-card {{
            background: linear-gradient(135deg, {t['bg_secondary']} 0%, {t['bg_card']} 100%);
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            border: 1px solid {t['border']};
        }}

        .stat-number {{
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(90deg, {t['accent']} 0%, {t['accent_secondary']} 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        /* Keyboard shortcut hints */
        .kbd {{
            background: {t['bg_secondary']};
            border: 1px solid {t['border']};
            border-radius: 4px;
            padding: 2px 6px;
            font-family: monospace;
            font-size: 0.85rem;
        }}

        /* LaTeX styling */
        .latex-content {{
            font-size: 1.1rem;
            line-height: 1.6;
        }}

        /* Duplicate warning */
        .duplicate-warning {{
            background: {t['warning']}22;
            border-left: 4px solid {t['warning']};
            padding: 0.5rem 1rem;
            border-radius: 0 8px 8px 0;
            margin: 0.5rem 0;
        }}

        /* Tab styling */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
        }}

        .stTabs [data-baseweb="tab"] {{
            background-color: {t['bg_secondary']};
            border-radius: 8px 8px 0 0;
            padding: 10px 20px;
        }}

        .stTabs [aria-selected="true"] {{
            background: linear-gradient(90deg, {t['accent']} 0%, {t['accent_secondary']} 100%);
        }}
    </style>
    """

# ============================================================
# SESSION STATE INITIALIZATION
# ============================================================
def init_session_state():
    defaults = {
        "cards": [],
        "generated": False,
        "theme": "light",
        "history": [],
        "current_tab": "generate",
        "bulk_mode": False,
        "preview_mode": False,
        "show_explanations": True,
        "card_order": [],
        "reorder_mode": False,
        "image_cards_mode": False,
        "statistics": {
            "total_cards_created": 0,
            "cards_by_subject": {},
            "cards_by_date": {},
            "sessions": 0
        },
        "anki_connect_enabled": False,
        "detected_subject": None,
        "card_images": {},  # Store images for cards: {card_index: {"front_img": base64, "back_img": base64}}
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

    # Load history and stats from disk
    load_history()
    load_statistics()

def load_history():
    if HISTORY_FILE.exists():
        try:
            with open(HISTORY_FILE, "r") as f:
                st.session_state.history = json.load(f)
        except:
            st.session_state.history = []

def save_history():
    with open(HISTORY_FILE, "w") as f:
        json.dump(st.session_state.history, f, indent=2)

def load_statistics():
    if STATS_FILE.exists():
        try:
            with open(STATS_FILE, "r") as f:
                st.session_state.statistics = json.load(f)
        except:
            pass

def save_statistics():
    with open(STATS_FILE, "w") as f:
        json.dump(st.session_state.statistics, f, indent=2)

def update_statistics(num_cards, subject):
    stats = st.session_state.statistics
    stats["total_cards_created"] += num_cards
    stats["sessions"] += 1

    # By subject
    if subject not in stats["cards_by_subject"]:
        stats["cards_by_subject"][subject] = 0
    stats["cards_by_subject"][subject] += num_cards

    # By date
    today = datetime.now().strftime("%Y-%m-%d")
    if today not in stats["cards_by_date"]:
        stats["cards_by_date"][today] = 0
    stats["cards_by_date"][today] += num_cards

    save_statistics()

# ============================================================
# EXAM CONTEXTS & CARD FORMATS
# ============================================================
exam_context = {
    "MCAT": """This is for the MCAT. Focus on foundational physics, chemistry, biology, biochemistry concepts. Emphasize relationships and principles, not specific calculations. Target AAMC high-yield topics.""",
    "USMLE Step 1": """This is for USMLE Step 1. Focus on First Aid high-yield facts, pathophysiology, mechanisms, pharmacology MOA/side effects, microbiology, and pathology buzzwords.""",
    "USMLE Step 2 CK": """This is for USMLE Step 2 CK. Focus on clinical management, next best steps, diagnosis from presentation, treatment algorithms, and standard of care.""",
    "Medical School (Preclinical)": """This is for medical school preclinical courses. Focus on mechanisms, pathways, and integration across organ systems.""",
    "Medical School (Clinical)": """This is for clinical rotations/shelf exams. Focus on diagnosis, management, and clinical decision making.""",
    "Nursing (NCLEX)": """This is for NCLEX. Focus on patient safety, prioritization, delegation, and nursing interventions.""",
    "PA School": """This is for PA school/PANCE. Focus on clinical medicine, diagnosis, and treatment across specialties.""",
    "Pharmacy (NAPLEX)": """This is for NAPLEX. Focus on drug interactions, dosing, counseling points, and clinical pharmacology.""",
    "General": """Focus on foundational concepts useful for any learner studying this topic.""",
    "Auto-Detect": """Analyze the content and determine the most appropriate subject area, then create cards accordingly."""
}

card_format_instructions = {
    "Basic (Q&A)": """Create standard question and answer cards.
Format: Question text here\tAnswer text here""",

    "Cloze (Fill-in-blank)": """Create fill-in-the-blank cards using Anki cloze format.
Format: Text with {{c1::hidden answer}} in it\t
Put the most important term in the {{c1::brackets}}.""",

    "Multiple Choice": """Create multiple choice questions with 4 options.
Format: Question (A) wrong (B) wrong (C) correct (D) wrong\tC
Always put the correct answer as the Back, just the letter.""",

    "Mix of All Types": """Create a variety of card types - some basic Q&A, some cloze deletions, some multiple choice.
For basic: Question\tAnswer
For cloze: Text with {{c1::hidden}}\t
For MC: Question (A) opt (B) opt (C) opt (D) opt\tCorrectLetter"""
}

# ============================================================
# UTILITY FUNCTIONS
# ============================================================
def get_card_hash(front, back):
    """Generate hash for duplicate detection"""
    content = f"{front.lower().strip()}{back.lower().strip()}"
    return hashlib.md5(content.encode()).hexdigest()[:8]

def find_duplicates(new_cards, existing_cards):
    """Find potential duplicates based on content similarity"""
    existing_hashes = {get_card_hash(c["front"], c["back"]) for c in existing_cards}
    duplicates = []
    for i, card in enumerate(new_cards):
        card_hash = get_card_hash(card["front"], card["back"])
        if card_hash in existing_hashes:
            duplicates.append(i)
        # Also check for similar content using simple word overlap
        for existing in existing_cards:
            if calculate_similarity(card["front"], existing["front"]) > 0.7:
                if i not in duplicates:
                    duplicates.append(i)
    return duplicates

def calculate_similarity(text1, text2):
    """Simple word-based similarity calculation"""
    words1 = set(text1.lower().split())
    words2 = set(text2.lower().split())
    if not words1 or not words2:
        return 0
    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union)

def calculate_quality_score(card):
    """Calculate quality score for a card (1-5)"""
    score = 3  # Base score
    front = card.get("front", "")
    back = card.get("back", "")

    # Length checks
    if 10 < len(front) < 200:
        score += 0.5
    if 5 < len(back) < 500:
        score += 0.5

    # Penalize vague references
    bad_patterns = ["the passage", "the figure", "the graph", "this question", "the experiment"]
    for pattern in bad_patterns:
        if pattern in front.lower() or pattern in back.lower():
            score -= 1

    # Reward clear question words
    good_starts = ["what", "how", "why", "which", "where", "when", "define", "explain"]
    if any(front.lower().strip().startswith(w) for w in good_starts):
        score += 0.5

    # Ensure score is within bounds
    return max(1, min(5, round(score)))

def render_latex(text):
    """Convert LaTeX notation for display"""
    # Streamlit supports LaTeX with st.latex() and $...$ in markdown
    return text

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file"""
    try:
        import PyPDF2
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n\n"
        return text
    except ImportError:
        return None
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"

# ============================================================
# ANKI CONNECT INTEGRATION
# ============================================================
def check_anki_connect():
    """Check if AnkiConnect is available"""
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:8765",
            data=json.dumps({"action": "version", "version": 6}).encode())
        response = urllib.request.urlopen(req, timeout=1)
        return json.loads(response.read())
    except:
        return None

def send_to_anki(cards, deck_name, tags):
    """Send cards directly to Anki via AnkiConnect"""
    try:
        import urllib.request

        # First, ensure deck exists
        create_deck = {
            "action": "createDeck",
            "version": 6,
            "params": {"deck": deck_name}
        }
        req = urllib.request.Request("http://localhost:8765",
            data=json.dumps(create_deck).encode())
        urllib.request.urlopen(req, timeout=5)

        # Add notes
        notes = []
        for card in cards:
            note = {
                "deckName": deck_name,
                "modelName": "Basic",
                "fields": {
                    "Front": card["front"],
                    "Back": card["back"]
                },
                "tags": tags.split(",") if tags else []
            }
            notes.append(note)

        add_notes = {
            "action": "addNotes",
            "version": 6,
            "params": {"notes": notes}
        }
        req = urllib.request.Request("http://localhost:8765",
            data=json.dumps(add_notes).encode())
        response = urllib.request.urlopen(req, timeout=10)
        result = json.loads(response.read())
        return result
    except Exception as e:
        return {"error": str(e)}

# ============================================================
# AI FUNCTIONS
# ============================================================
def detect_subject(client, content):
    """Auto-detect the subject/exam type from content"""
    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=100,
            messages=[{
                "role": "user",
                "content": f"""Analyze this educational content and respond with ONLY the most appropriate category from this list:
MCAT, USMLE Step 1, USMLE Step 2 CK, Medical School (Preclinical), Medical School (Clinical), Nursing (NCLEX), PA School, Pharmacy (NAPLEX), General

Content: {content[:1000]}

Respond with just the category name, nothing else."""
            }]
        )
        detected = message.content[0].text.strip()
        if detected in exam_context:
            return detected
        return "General"
    except:
        return "General"

def generate_cards_with_explanation(client, content, settings):
    """Generate cards with explanations for each"""
    prompt_base = """You are an expert at creating Anki flashcards from wrong test answers.

YOUR GOAL: Create cards that will help on FUTURE questions about this topic.

QUALITY RULES:
1. Focus on transferable concepts, principles, and relationships
2. Front of card must have ONE clear, unambiguous answer
3. Ask about mechanisms, definitions, and general principles
4. Cards should be useful even to someone who never saw this question

AVOID (these make cards useless for future studying):
- Referencing "the passage," "the figure," "the graph," or "the experiment"
- Using specific numbers, values, or data points from the question
- Asking about experimental setups or scenarios from the question
- Comparisons that only make sense with the original context

IMPORTANT: For each card, also provide a brief explanation of WHY you created this card and what concept it tests.

Format each card as:
CARD: [front of card]\t[back of card]
EXPLANATION: [why this card is useful]

One card per CARD/EXPLANATION pair. No other formatting."""

    difficulty_instruction = {
        "Basic recall": "Make simple factual recall cards.",
        "Standard": "Make standard difficulty cards testing understanding.",
        "Application": "Make cards that require applying concepts to scenarios.",
        "Integration": "Make challenging cards that integrate multiple concepts."
    }

    full_prompt = prompt_base + "\n\n" + exam_context[settings["exam_type"]]
    full_prompt += "\n\n" + card_format_instructions[settings["card_format"]]
    full_prompt += f"\n\n{difficulty_instruction[settings['difficulty']]}"
    full_prompt += f"\n\nGenerate exactly {settings['num_cards']} cards."

    if settings.get("custom_instructions"):
        full_prompt += f"\n\nUser instructions: {settings['custom_instructions']}"

    if settings.get("is_image"):
        messages_content = [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": content}},
            {"type": "text", "text": full_prompt}
        ]
    else:
        messages_content = [{"type": "text", "text": full_prompt + "\n\n" + content}]

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        messages=[{"role": "user", "content": messages_content}]
    )

    response = message.content[0].text

    # Parse response with explanations
    cards = []
    lines = response.strip().split("\n")
    current_card = None

    for line in lines:
        line = line.strip()
        if line.startswith("CARD:"):
            card_content = line[5:].strip()
            if "\t" in card_content:
                parts = card_content.split("\t")
                current_card = {
                    "front": parts[0].strip(),
                    "back": parts[1].strip() if len(parts) > 1 else "",
                    "keep": True,
                    "explanation": "",
                    "quality_score": 3
                }
        elif line.startswith("EXPLANATION:") and current_card:
            current_card["explanation"] = line[12:].strip()
            current_card["quality_score"] = calculate_quality_score(current_card)
            cards.append(current_card)
            current_card = None

    # Fallback parsing for simpler format
    if not cards:
        for line in response.strip().split("\n"):
            if "\t" in line and not line.startswith("CARD:") and not line.startswith("EXPLANATION:"):
                parts = line.split("\t")
                if len(parts) >= 1:
                    card = {
                        "front": parts[0].strip(),
                        "back": parts[1].strip() if len(parts) > 1 else "",
                        "keep": True,
                        "explanation": "Standard card generation",
                        "quality_score": 3
                    }
                    card["quality_score"] = calculate_quality_score(card)
                    cards.append(card)

    return cards

# ============================================================
# UI COMPONENTS
# ============================================================
def render_flip_card(card, index):
    """Render an interactive flip card preview"""
    st.markdown(f"""
    <div class="flip-card" onclick="this.classList.toggle('flipped')" id="flip-{index}">
        <div class="flip-card-inner">
            <div class="flip-card-front">
                <div>{card['front'][:150]}{'...' if len(card['front']) > 150 else ''}</div>
            </div>
            <div class="flip-card-back">
                <div>{card['back'][:150]}{'...' if len(card['back']) > 150 else ''}</div>
            </div>
        </div>
    </div>
    <p style="text-align: center; color: #888; font-size: 0.8rem;">Click to flip</p>
    """, unsafe_allow_html=True)

def render_quality_stars(score):
    """Render quality score as stars"""
    filled = "★" * score
    empty = "☆" * (5 - score)
    return f'<span class="quality-stars">{filled}{empty}</span>'

def render_card_editor(card, index):
    """Render an editable card with all features"""
    col_check, col_content = st.columns([0.05, 0.95])

    with col_check:
        card["keep"] = st.checkbox("", value=card.get("keep", True), key=f"keep_{index}", label_visibility="collapsed")

    with col_content:
        # Check for duplicates
        is_duplicate = card.get("is_duplicate", False)

        header = f"**Card {index+1}** "
        header += render_quality_stars(card.get("quality_score", 3))

        if is_duplicate:
            st.markdown(f'<div class="duplicate-warning">⚠️ Possible duplicate detected</div>', unsafe_allow_html=True)

        with st.expander(f"{header} - {card['front'][:50]}{'...' if len(card['front']) > 50 else ''}", expanded=False):
            card["front"] = st.text_area("Front", value=card["front"], key=f"front_{index}", height=80)
            card["back"] = st.text_area("Back", value=card["back"], key=f"back_{index}", height=80)

            # Image cards mode - allow adding images to front/back
            if st.session_state.get("image_cards_mode", False):
                st.markdown("**🖼️ Card Images:**")
                img_col1, img_col2 = st.columns(2)

                with img_col1:
                    front_img = st.file_uploader(
                        "Front image",
                        type=["png", "jpg", "jpeg"],
                        key=f"front_img_{index}"
                    )
                    if front_img:
                        front_img.seek(0)
                        img_data = base64.b64encode(front_img.read()).decode("utf-8")
                        card["front_image"] = img_data
                        st.image(f"data:image/png;base64,{img_data}", width=150)
                    elif card.get("front_image"):
                        st.image(f"data:image/png;base64,{card['front_image']}", width=150)

                with img_col2:
                    back_img = st.file_uploader(
                        "Back image",
                        type=["png", "jpg", "jpeg"],
                        key=f"back_img_{index}"
                    )
                    if back_img:
                        back_img.seek(0)
                        img_data = base64.b64encode(back_img.read()).decode("utf-8")
                        card["back_image"] = img_data
                        st.image(f"data:image/png;base64,{img_data}", width=150)
                    elif card.get("back_image"):
                        st.image(f"data:image/png;base64,{card['back_image']}", width=150)

            # LaTeX preview
            if "$" in card["front"] or "$" in card["back"]:
                st.markdown("**LaTeX Preview:**")
                if "$" in card["front"]:
                    st.markdown(card["front"])
                if "$" in card["back"]:
                    st.markdown(card["back"])

            # Show explanation if available
            if card.get("explanation") and st.session_state.show_explanations:
                st.info(f"💡 **Why this card:** {card['explanation']}")

            # Quality score display
            st.markdown(f"Quality: {render_quality_stars(card.get('quality_score', 3))}", unsafe_allow_html=True)

    return card

def render_statistics_dashboard():
    """Render the statistics dashboard"""
    stats = st.session_state.statistics

    st.markdown("## 📊 Your CardForge Statistics")

    # Main stats
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{stats.get('total_cards_created', 0)}</div>
            <div>Total Cards Created</div>
        </div>
        """, unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number">{stats.get('sessions', 0)}</div>
            <div>Study Sessions</div>
        </div>
        """, unsafe_allow_html=True)

    with col3:
        subjects = stats.get('cards_by_subject', {})
        top_subject = max(subjects, key=subjects.get) if subjects else "None"
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-number" style="font-size: 1.5rem;">{top_subject}</div>
            <div>Top Subject</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # Cards by subject
    if stats.get("cards_by_subject"):
        st.markdown("### 📚 Cards by Subject")
        for subject, count in sorted(stats["cards_by_subject"].items(), key=lambda x: x[1], reverse=True):
            progress = count / max(stats["cards_by_subject"].values())
            st.progress(progress, text=f"{subject}: {count} cards")

    # Recent activity
    if stats.get("cards_by_date"):
        st.markdown("### 📅 Recent Activity")
        dates = list(stats["cards_by_date"].items())[-7:]  # Last 7 days
        for date, count in dates:
            st.text(f"{date}: {'🎴' * min(count, 20)} ({count})")

def render_history_panel():
    """Render the card history panel"""
    st.markdown("## 📜 Card History")

    if not st.session_state.history:
        st.info("No cards in history yet. Generate some cards to see them here!")
        return

    # Search and filter
    search = st.text_input("🔍 Search cards", placeholder="Search by content...")

    filtered_history = st.session_state.history
    if search:
        filtered_history = [
            h for h in st.session_state.history
            if search.lower() in h.get("front", "").lower() or search.lower() in h.get("back", "").lower()
        ]

    st.markdown(f"Showing {len(filtered_history)} of {len(st.session_state.history)} cards")

    # Display cards
    for i, card in enumerate(filtered_history[-50:]):  # Show last 50
        with st.expander(f"📝 {card.get('front', '')[:60]}...", expanded=False):
            st.markdown(f"**Front:** {card.get('front', '')}")
            st.markdown(f"**Back:** {card.get('back', '')}")
            st.markdown(f"**Created:** {card.get('created_at', 'Unknown')}")
            st.markdown(f"**Subject:** {card.get('subject', 'Unknown')}")

            if st.button("♻️ Reuse this card", key=f"reuse_{i}"):
                if card not in st.session_state.cards:
                    st.session_state.cards.append({
                        "front": card.get("front", ""),
                        "back": card.get("back", ""),
                        "keep": True,
                        "explanation": "Reused from history",
                        "quality_score": card.get("quality_score", 3)
                    })
                    st.success("Card added!")
                    st.rerun()

    # Clear history button
    st.markdown("---")
    if st.button("🗑️ Clear History", type="secondary"):
        if st.checkbox("Confirm clear history"):
            st.session_state.history = []
            save_history()
            st.success("History cleared!")
            st.rerun()

# ============================================================
# MAIN APPLICATION
# ============================================================
def main():
    init_session_state()

    # Apply theme
    st.markdown(get_theme_css(st.session_state.theme), unsafe_allow_html=True)

    # Header
    col_title, col_theme = st.columns([4, 1])
    with col_title:
        st.markdown('<p class="main-header">🎴 CardForge</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">Turn wrong answers into memorable flashcards</p>', unsafe_allow_html=True)
    with col_theme:
        theme_toggle = st.toggle("🌙 Dark Mode", value=st.session_state.theme == "dark")
        st.session_state.theme = "dark" if theme_toggle else "light"

    # Sidebar
    with st.sidebar:
        st.header("🔑 API Key")
        api_key = st.text_input(
            "Enter your Anthropic API key",
            type="password",
            help="Get your key at console.anthropic.com"
        )

        if api_key:
            st.success("✓ API key entered")
        else:
            st.warning("Enter your API key to generate cards")
            st.markdown("[Get an API key →](https://console.anthropic.com)")

        st.divider()
        st.header("⚙️ Settings")

        exam_type = st.selectbox("📚 Exam/Course", list(exam_context.keys()))
        card_format = st.selectbox("🃏 Card Format", list(card_format_instructions.keys()))
        num_cards = st.slider("📊 Number of cards", 1, 20, 5)

        st.divider()

        deck_name = st.text_input("📁 Deck name", value="My Cards")
        tags = st.text_input("🏷️ Tags (comma-separated)", placeholder="e.g., physics, ultrasound")

        st.divider()

        difficulty = st.select_slider(
            "💪 Difficulty",
            options=["Basic recall", "Standard", "Application", "Integration"],
            value="Standard"
        )

        st.divider()
        st.header("🎛️ Features")

        st.session_state.show_explanations = st.checkbox("💡 Show AI explanations", value=True)
        st.session_state.bulk_mode = st.checkbox("📑 Bulk mode (multiple questions)", value=False)
        st.session_state.preview_mode = st.checkbox("🎴 Card preview mode", value=False)
        st.session_state.image_cards_mode = st.checkbox("🖼️ Image cards mode", value=False)
        if SORTABLES_AVAILABLE:
            st.session_state.reorder_mode = st.checkbox("↕️ Reorder cards mode", value=False)
        else:
            st.caption("↕️ Drag-drop: `pip install streamlit-sortables`")

        # AnkiConnect status
        st.divider()
        st.header("🔗 Anki Integration")
        anki_status = check_anki_connect()
        if anki_status:
            st.success(f"✓ AnkiConnect v{anki_status.get('result', '?')}")
            st.session_state.anki_connect_enabled = True
        else:
            st.info("AnkiConnect not detected")
            st.markdown("[Setup AnkiConnect →](https://ankiweb.net/shared/info/2055492159)")
            st.session_state.anki_connect_enabled = False

        # Keyboard shortcuts help
        st.divider()
        st.markdown("### ⌨️ Shortcuts")
        st.markdown("""
        <span class="kbd">Ctrl</span>+<span class="kbd">Enter</span> Generate<br>
        <span class="kbd">Ctrl</span>+<span class="kbd">S</span> Download
        """, unsafe_allow_html=True)

    # Main content with tabs
    tab1, tab2, tab3 = st.tabs(["✨ Generate", "📜 History", "📊 Statistics"])

    with tab1:
        render_generate_tab(api_key, exam_type, card_format, num_cards, deck_name, tags, difficulty)

    with tab2:
        render_history_panel()

    with tab3:
        render_statistics_dashboard()

    # Footer
    st.divider()
    st.markdown("""
    <div style='text-align: center; color: #888; font-size: 0.9rem;'>
        Built with Claude AI • Cards export directly to Anki • <a href="https://github.com">View on GitHub</a>
    </div>
    """, unsafe_allow_html=True)

def render_generate_tab(api_key, exam_type, card_format, num_cards, deck_name, tags, difficulty):
    """Render the main card generation tab"""
    col1, col2 = st.columns([1, 1])

    with col1:
        st.subheader("📥 Input")

        if st.session_state.bulk_mode:
            input_method = st.radio("Choose input method:", ["📷 Upload Screenshots", "📝 Paste Text", "📄 Upload PDF"], horizontal=True)
        else:
            input_method = st.radio("Choose input method:", ["📷 Upload Screenshot", "📝 Paste Text", "📄 Upload PDF"], horizontal=True)

        uploaded_files = []
        text_input = None
        pdf_text = None

        if "Screenshot" in input_method:
            if st.session_state.bulk_mode:
                uploaded_files = st.file_uploader(
                    "Drop your screenshots here (multiple allowed)",
                    type=["png", "jpg", "jpeg"],
                    accept_multiple_files=True
                )
                if uploaded_files:
                    cols = st.columns(min(len(uploaded_files), 3))
                    for i, f in enumerate(uploaded_files[:3]):
                        with cols[i]:
                            st.image(f, caption=f"Image {i+1}", use_container_width=True)
                    if len(uploaded_files) > 3:
                        st.info(f"+{len(uploaded_files) - 3} more images")
            else:
                uploaded_file = st.file_uploader("Drop your screenshot here", type=["png", "jpg", "jpeg"])
                if uploaded_file:
                    st.image(uploaded_file, caption="Uploaded image", use_container_width=True)
                    uploaded_files = [uploaded_file]

        elif "Text" in input_method:
            if st.session_state.bulk_mode:
                text_input = st.text_area(
                    "Paste multiple questions (separate with '---'):",
                    height=300,
                    placeholder="Question 1...\n---\nQuestion 2...\n---\nQuestion 3..."
                )
            else:
                text_input = st.text_area(
                    "Paste the question you got wrong:",
                    height=250,
                    placeholder="Include the question, answer choices, your answer, and the correct answer..."
                )

        elif "PDF" in input_method:
            pdf_file = st.file_uploader("Upload PDF document", type=["pdf"])
            if pdf_file:
                with st.spinner("Extracting text from PDF..."):
                    pdf_text = extract_text_from_pdf(pdf_file)
                    if pdf_text and not pdf_text.startswith("Error"):
                        st.success(f"Extracted {len(pdf_text)} characters")
                        with st.expander("Preview extracted text"):
                            st.text(pdf_text[:2000] + "..." if len(pdf_text) > 2000 else pdf_text)
                    elif pdf_text:
                        st.error(pdf_text)
                        st.info("Install PyPDF2 for PDF support: `pip install PyPDF2`")
                    else:
                        st.warning("Could not extract text. Install PyPDF2: `pip install PyPDF2`")

        custom_instructions = st.text_area(
            "💬 Special instructions (optional)",
            placeholder="e.g., I keep confusing X with Y, focus on the mechanism...",
            height=80
        )

        bcol1, bcol2 = st.columns(2)
        with bcol1:
            generate_btn = st.button("✨ Generate Cards", type="primary", use_container_width=True)
        with bcol2:
            regenerate_btn = st.button("🔄 Regenerate", use_container_width=True)

    with col2:
        st.subheader("🎴 Generated Cards")

        if generate_btn or regenerate_btn:
            if not api_key:
                st.error("⚠️ Please enter your API key in the sidebar")
            else:
                # Collect all inputs
                all_inputs = []

                if uploaded_files:
                    for f in uploaded_files:
                        f.seek(0)
                        bytes_data = f.read()
                        base64_image = base64.b64encode(bytes_data).decode("utf-8")
                        all_inputs.append({"type": "image", "content": base64_image})
                elif text_input:
                    if st.session_state.bulk_mode and "---" in text_input:
                        questions = [q.strip() for q in text_input.split("---") if q.strip()]
                        for q in questions:
                            all_inputs.append({"type": "text", "content": q})
                    else:
                        all_inputs.append({"type": "text", "content": text_input})
                elif pdf_text and not pdf_text.startswith("Error"):
                    all_inputs.append({"type": "text", "content": pdf_text})

                if not all_inputs:
                    st.warning("⚠️ Please upload an image, paste text, or upload a PDF first")
                else:
                    try:
                        client = anthropic.Anthropic(api_key=api_key)

                        # Auto-detect subject if selected
                        actual_exam_type = exam_type
                        if exam_type == "Auto-Detect":
                            with st.spinner("🔍 Detecting subject..."):
                                sample_content = all_inputs[0]["content"][:1000] if all_inputs[0]["type"] == "text" else "image content"
                                actual_exam_type = detect_subject(client, sample_content)
                                st.info(f"📚 Detected subject: **{actual_exam_type}**")
                                st.session_state.detected_subject = actual_exam_type

                        settings = {
                            "exam_type": actual_exam_type,
                            "card_format": card_format,
                            "num_cards": num_cards,
                            "difficulty": difficulty,
                            "custom_instructions": custom_instructions + ("\n\nPrevious cards were too specific. Make these MORE GENERAL." if regenerate_btn else ""),
                            "is_image": False
                        }

                        st.session_state.cards = []

                        # Process each input
                        progress = st.progress(0, text="Generating cards...")
                        for i, inp in enumerate(all_inputs):
                            progress.progress((i + 1) / len(all_inputs), text=f"Processing input {i+1}/{len(all_inputs)}...")

                            settings["is_image"] = inp["type"] == "image"

                            with st.spinner(f"🧠 Analyzing input {i+1} and creating cards..."):
                                new_cards = generate_cards_with_explanation(client, inp["content"], settings)

                                # Check for duplicates
                                duplicates = find_duplicates(new_cards, st.session_state.cards + st.session_state.history)
                                for idx in duplicates:
                                    if idx < len(new_cards):
                                        new_cards[idx]["is_duplicate"] = True

                                st.session_state.cards.extend(new_cards)

                        progress.empty()
                        st.session_state.generated = True

                        # Update statistics
                        update_statistics(len(st.session_state.cards), actual_exam_type)

                        # Add to history
                        for card in st.session_state.cards:
                            history_card = {
                                **card,
                                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                                "subject": actual_exam_type
                            }
                            st.session_state.history.append(history_card)
                        save_history()

                    except anthropic.AuthenticationError:
                        st.error("❌ Invalid API key. Please check and try again.")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

        # Display cards
        if st.session_state.cards:
            # Preview mode toggle
            if st.session_state.preview_mode:
                st.markdown("### 🎴 Card Preview (click to flip)")
                cols = st.columns(2)
                for i, card in enumerate(st.session_state.cards):
                    with cols[i % 2]:
                        render_flip_card(card, i)
                st.markdown("---")
                st.markdown("### ✏️ Edit Cards")

            # Drag-and-drop reorder mode
            if st.session_state.get("reorder_mode", False) and SORTABLES_AVAILABLE:
                st.markdown("### ↕️ Drag to Reorder Cards")
                st.caption("Drag cards to change their order, then click 'Apply Order'")

                # Create sortable items
                card_items = [f"Card {i+1}: {card['front'][:40]}..." for i, card in enumerate(st.session_state.cards)]
                sorted_items = sort_items(card_items, direction="vertical")

                if sorted_items != card_items:
                    # Extract new order from sorted items
                    new_order = []
                    for item in sorted_items:
                        # Extract card number from "Card X: ..."
                        card_num = int(item.split(":")[0].replace("Card ", "")) - 1
                        new_order.append(card_num)

                    if st.button("✅ Apply New Order", type="primary"):
                        # Reorder cards based on new order
                        st.session_state.cards = [st.session_state.cards[i] for i in new_order]
                        st.success("Cards reordered!")
                        st.rerun()

                st.markdown("---")

            # Editable cards
            for i, card in enumerate(st.session_state.cards):
                st.session_state.cards[i] = render_card_editor(card, i)

            st.divider()

            kept_cards = [c for c in st.session_state.cards if c.get("keep", True)]

            scol1, scol2, scol3, scol4 = st.columns(4)
            with scol1:
                st.metric("Total Cards", len(st.session_state.cards))
            with scol2:
                st.metric("Selected", len(kept_cards))
            with scol3:
                st.metric("Removed", len(st.session_state.cards) - len(kept_cards))
            with scol4:
                avg_quality = sum(c.get("quality_score", 3) for c in kept_cards) / len(kept_cards) if kept_cards else 0
                st.metric("Avg Quality", f"{avg_quality:.1f} ★")

            if kept_cards:
                # Export options
                st.markdown("### 📤 Export Options")

                export_col1, export_col2 = st.columns(2)

                with export_col1:
                    # File download
                    tag_str = ""
                    if tags:
                        tag_list = [t.strip() for t in tags.split(",")]
                        tag_str = " ".join([f"tags:{t}" for t in tag_list])

                    anki_lines = []
                    for c in kept_cards:
                        line = f"{c['front']}\t{c['back']}"
                        if tag_str:
                            line += f"\t{tag_str}"
                        anki_lines.append(line)

                    anki_export = "\n".join(anki_lines)

                    st.download_button(
                        label=f"📥 Download {len(kept_cards)} cards (.txt)",
                        data=anki_export,
                        file_name=f"{deck_name.replace(' ', '_')}_flashcards.txt",
                        mime="text/plain",
                        use_container_width=True
                    )

                with export_col2:
                    # AnkiConnect direct send
                    if st.session_state.anki_connect_enabled:
                        if st.button(f"🚀 Send to Anki ({len(kept_cards)} cards)", use_container_width=True):
                            with st.spinner("Sending to Anki..."):
                                result = send_to_anki(kept_cards, deck_name, tags)
                                if "error" in result:
                                    st.error(f"Failed: {result['error']}")
                                else:
                                    st.success(f"✓ Sent {len(kept_cards)} cards to '{deck_name}'!")
                    else:
                        st.button("🚀 Send to Anki (not connected)", disabled=True, use_container_width=True)

                # JSON export for sharing
                st.markdown("#### 📦 Share Deck")
                json_export = json.dumps({
                    "deck_name": deck_name,
                    "tags": tags,
                    "cards": [{"front": c["front"], "back": c["back"]} for c in kept_cards],
                    "created_at": datetime.now().isoformat(),
                    "card_count": len(kept_cards)
                }, indent=2)

                st.download_button(
                    label="📤 Export as JSON (shareable)",
                    data=json_export,
                    file_name=f"{deck_name.replace(' ', '_')}_deck.json",
                    mime="application/json",
                    use_container_width=True
                )

                # Import shared deck
                with st.expander("📥 Import Shared Deck"):
                    import_file = st.file_uploader("Upload JSON deck file", type=["json"], key="import_deck")
                    if import_file:
                        try:
                            imported = json.load(import_file)
                            st.info(f"Found {imported.get('card_count', len(imported.get('cards', [])))} cards in '{imported.get('deck_name', 'Unknown')}'")
                            if st.button("Import Cards"):
                                for card in imported.get("cards", []):
                                    st.session_state.cards.append({
                                        "front": card.get("front", ""),
                                        "back": card.get("back", ""),
                                        "keep": True,
                                        "explanation": "Imported from shared deck",
                                        "quality_score": 3
                                    })
                                st.success(f"Imported {len(imported.get('cards', []))} cards!")
                                st.rerun()
                        except Exception as e:
                            st.error(f"Invalid file: {e}")

                with st.expander("👀 Preview export"):
                    st.code(anki_export)

        elif st.session_state.generated:
            st.info("No cards generated. Try adjusting your input.")
        else:
            st.info("👈 Upload a screenshot or paste a question to get started")

if __name__ == "__main__":
    main()
