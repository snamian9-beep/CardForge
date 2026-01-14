import streamlit as st
import anthropic
import base64

st.set_page_config(
    page_title="CardForge", 
    page_icon="🎴",
    layout="wide"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-header">🎴 CardForge</p>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Turn wrong answers into memorable flashcards</p>', unsafe_allow_html=True)

exam_context = {
    "MCAT": """This is for the MCAT. Focus on foundational physics, chemistry, biology, biochemistry concepts. Emphasize relationships and principles, not specific calculations. Target AAMC high-yield 
topics.""",
    "USMLE Step 1": """This is for USMLE Step 1. Focus on First Aid high-yield facts, pathophysiology, mechanisms, pharmacology MOA/side effects, microbiology, and pathology buzzwords.""",
    "USMLE Step 2 CK": """This is for USMLE Step 2 CK. Focus on clinical management, next best steps, diagnosis from presentation, treatment algorithms, and standard of care.""",
    "Medical School (Preclinical)": """This is for medical school preclinical courses. Focus on mechanisms, pathways, and integration across organ systems.""",
    "Medical School (Clinical)": """This is for clinical rotations/shelf exams. Focus on diagnosis, management, and clinical decision making.""",
    "Nursing (NCLEX)": """This is for NCLEX. Focus on patient safety, prioritization, delegation, and nursing interventions.""",
    "PA School": """This is for PA school/PANCE. Focus on clinical medicine, diagnosis, and treatment across specialties.""",
    "Pharmacy (NAPLEX)": """This is for NAPLEX. Focus on drug interactions, dosing, counseling points, and clinical pharmacology.""",
    "General": """Focus on foundational concepts useful for any learner studying this topic."""
}

card_format_instructions = {
    "Basic (Q&A)": """Create standard question and answer cards.
Format: Question text here	Answer text here""",
    
    "Cloze (Fill-in-blank)": """Create fill-in-the-blank cards using Anki cloze format.
Format: Text with {{c1::hidden answer}} in it	
Put the most important term in the {{c1::brackets}}.""",
    
    "Multiple Choice": """Create multiple choice questions with 4 options.
Format: Question (A) wrong (B) wrong (C) correct (D) wrong	C
Always put the correct answer as the Back, just the letter.""",
    
    "Mix of All Types": """Create a variety of card types - some basic Q&A, some cloze deletions, some multiple choice.
For basic: Question	Answer
For cloze: Text with {{c1::hidden}}	
For MC: Question (A) opt (B) opt (C) opt (D) opt	CorrectLetter"""
}

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

One card per line. No labels. No numbering. No asterisks or extra formatting.
"""

if "cards" not in st.session_state:
    st.session_state.cards = []
if "generated" not in st.session_state:
    st.session_state.generated = False

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
    num_cards = st.slider("📊 Number of cards", 1, 15, 5)
    
    st.divider()
    
    deck_name = st.text_input("📁 Deck name", value="My Cards")
    tags = st.text_input("🏷️ Tags (comma-separated)", placeholder="e.g., physics, ultrasound")
    
    st.divider()
    
    difficulty = st.select_slider(
        "💪 Difficulty",
        options=["Basic recall", "Standard", "Application", "Integration"],
        value="Standard"
    )

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📥 Input")
    
    input_method = st.radio("Choose input method:", ["📷 Upload Screenshot", "📝 Paste Text"], horizontal=True)
    
    if input_method == "📷 Upload Screenshot":
        uploaded_file = st.file_uploader("Drop your screenshot here", type=["png", "jpg", "jpeg"])
        if uploaded_file:
            st.image(uploaded_file, caption="Uploaded image", use_container_width=True)
        text_input = None
    else:
        uploaded_file = None
        text_input = st.text_area("Paste the question you got wrong:", height=250, placeholder="Include the question, answer choices, your answer, and the correct answer...")

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
            content = []
            
            difficulty_instruction = {
                "Basic recall": "Make simple factual recall cards.",
                "Standard": "Make standard difficulty cards testing understanding.",
                "Application": "Make cards that require applying concepts to scenarios.",
                "Integration": "Make challenging cards that integrate multiple concepts."
            }
            
            full_prompt = prompt_base + "\n\n" + exam_context[exam_type]
            full_prompt += "\n\n" + card_format_instructions[card_format]
            full_prompt += f"\n\n{difficulty_instruction[difficulty]}"
            full_prompt += f"\n\nGenerate exactly {num_cards} cards."
            
            if regenerate_btn:
                full_prompt += "\n\nPrevious cards were too specific. Make these MORE GENERAL - focus only on textbook-level concepts."
            
            if custom_instructions:
                full_prompt += f"\n\nUser instructions: {custom_instructions}"
            
            has_input = False
            if uploaded_file:
                uploaded_file.seek(0)
                bytes_data = uploaded_file.read()
                base64_image = base64.b64encode(bytes_data).decode("utf-8")
                content = [
                    {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64_image}},
                    {"type": "text", "text": full_prompt}
                ]
                has_input = True
            elif text_input:
                content = [{"type": "text", "text": full_prompt + "\n\n" + text_input}]
                has_input = True
            
            if not has_input:
                st.warning("⚠️ Please upload an image or paste text first")
            else:
                try:
                    client = anthropic.Anthropic(api_key=api_key)
                    
                    with st.spinner("🧠 Analyzing and creating cards..."):
                        message = client.messages.create(
                            model="claude-sonnet-4-20250514",
                            max_tokens=1500,
                            messages=[{"role": "user", "content": content}]
                        )
                        response = message.content[0].text
                        
                        st.session_state.cards = []
                        for line in response.strip().split("\n"):
                            if "\t" in line:
                                parts = line.split("\t")
                                if len(parts) >= 1:
                                    back = parts[1] if len(parts) > 1 else ""
                                    st.session_state.cards.append({
                                        "front": parts[0], 
                                        "back": back, 
                                        "keep": True
                                    })
                        st.session_state.generated = True
                except anthropic.AuthenticationError:
                    st.error("❌ Invalid API key. Please check and try again.")
                except Exception as e:
                    st.error(f"❌ Error: {str(e)}")
    
    if st.session_state.cards:
        for i, card in enumerate(st.session_state.cards):
            col_check, col_content = st.columns([0.08, 0.92])
            with col_check:
                st.session_state.cards[i]["keep"] = st.checkbox("", value=card["keep"], key=f"keep_{i}", label_visibility="collapsed")
            with col_content:
                with st.expander(f"**Card {i+1}:** {card['front'][:60]}{'...' if len(card['front']) > 60 else ''}", expanded=False):
                    st.session_state.cards[i]["front"] = st.text_area("Front", value=card["front"], key=f"front_{i}", height=80)
                    st.session_state.cards[i]["back"] = st.text_area("Back", value=card["back"], key=f"back_{i}", height=80)
        
        st.divider()
        
        kept_cards = [c for c in st.session_state.cards if c["keep"]]
        
        scol1, scol2, scol3 = st.columns(3)
        with scol1:
            st.metric("Total Cards", len(st.session_state.cards))
        with scol2:
            st.metric("Selected", len(kept_cards))
        with scol3:
            st.metric("Removed", len(st.session_state.cards) - len(kept_cards))
        
        if kept_cards:
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
                label=f"📥 Download {len(kept_cards)} cards",
                data=anki_export,
                file_name=f"{deck_name.replace(' ', '_')}_flashcards.txt",
                mime="text/plain",
                use_container_width=True
            )
            
            with st.expander("👀 Preview export"):
                st.code(anki_export)
    
    elif st.session_state.generated:
        st.info("No cards generated. Try adjusting your input.")
    else:
        st.info("👈 Upload a screenshot or paste a question to get started")

st.divider()
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.9rem;'>
    Built with Claude AI • Cards export directly to Anki
</div>
""", unsafe_allow_html=True)
