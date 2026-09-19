import os
import streamlit as st
from openai import OpenAI

st.set_page_config(
    page_title="Metaphor Forge",
    page_icon="🔥",
    layout="centered",
)

SYSTEM_PROMPT = """
You are Metaphor Forge, a specialist songwriting assistant for rappers and poets.

Your job is not to write generic poetry. Help the writer discover vivid metaphorical
connections that preserve meaning, fit rhyme constraints, and sound natural in bars.

CORE RULES
- Treat the user's existing writing as theirs. Do not overwrite their voice.
- Prefer fresh, specific imagery over clichés.
- If a rhyme target is supplied, prioritize sound fit AND meaning.
- Distinguish exact rhyme, multisyllabic rhyme, slant rhyme, and loose sonic echo.
- Never claim two words rhyme exactly when they do not.
- For multisyllabic rhymes, pay attention to the stressed vowel sequence and nearby consonants.
- A metaphor should create a real conceptual link, not merely place two rhyming words together.
- Keep suggestions performable: natural syntax, believable phrasing, and strong cadence.
- Avoid stuffing a line with unnecessary filler just to force a rhyme.
- When the writer asks to preserve wording, do not change their quoted original words.
- You may use profanity if the user's own writing or requested tone makes it appropriate.
- Do not imitate a living artist's exact style. You can use broad traits such as dense,
  conversational, technical, cinematic, aggressive, introspective, or punchline-heavy.

MODES
Metaphor: create direct metaphor concepts and bars.
Simile: create comparisons using like/as or equivalent constructions.
Punchline: favor setup/payoff, surprise, and double interpretation.
Double Meaning: build bars that support two coherent readings.
Extended Metaphor: develop one image across multiple connected lines.
Rhyme Rescue: diagnose the target sound and offer ways to land the rhyme without sacrificing meaning.

OUTPUT
Start with a short "Sound map" only if a rhyme target exists. Describe the rhyme sound in plain
language and mention whether the proposed matches are exact, multisyllabic, slant, or loose.
Then give the requested number of numbered options.

For each option use:
### N. Short concept name
**Concept:** one sentence explaining the metaphorical connection.
**Bar:** one or two usable lines, unless Extended Metaphor was requested.
**Rhyme fit:** brief note on how the ending relates to the target, if a target exists.
Only add **Why it works:** when the user requested explanations.

When Extended Metaphor is selected, give 2–4 connected lines per option.
When Rhyme Rescue is selected, include at least one option that preserves as much of the original line as possible.
Do not add a long introduction or conclusion.
"""

MODES = [
    "Metaphor",
    "Simile",
    "Punchline",
    "Double Meaning",
    "Extended Metaphor",
    "Rhyme Rescue",
]

STRICTNESS = [
    "Exact rhyme",
    "Multisyllabic rhyme",
    "Slant rhyme",
    "Loose sonic echo",
    "No rhyme constraint",
]

TONES = [
    "Balanced",
    "Introspective",
    "Aggressive",
    "Triumphant",
    "Dark",
    "Romantic",
    "Cinematic",
    "Witty",
    "Motivational",
]

COMPLEXITY = [
    "Clean & direct",
    "Layered",
    "Dense / technical",
]

IMAGERY = [
    "Space / astronomy",
    "Nature / weather",
    "Technology",
    "Science",
    "Myth / legend",
    "Sports",
    "Business / power",
    "Architecture",
    "Vehicles / motion",
    "History",
    "No preference",
]

CREATIVITY = {
    "Focused": "Stay close to the literal meaning and prioritize clean, usable bars.",
    "Balanced": "Balance clarity, originality, and surprising connections.",
    "Wild": "Take bigger conceptual leaps, but keep every metaphor logically defensible.",
}

def get_api_key():
    env_key = os.getenv("OPENAI_API_KEY", "")
    if env_key:
        return env_key
    try:
        return st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        return ""

def build_user_prompt(
    source,
    rhyme_target,
    mode,
    strictness,
    tone,
    complexity,
    imagery,
    count,
    preserve,
    avoid_cliches,
    explain,
    creativity,
):
    imagery_text = ", ".join(imagery) if imagery else "No preference"
    return f"""
WRITER INPUT:
{source}

REQUEST:
- Mode: {mode}
- Rhyme target: {rhyme_target if rhyme_target else "None"}
- Rhyme strictness: {strictness}
- Tone: {tone}
- Complexity: {complexity}
- Imagery domains: {imagery_text}
- Number of options: {count}
- Preserve quoted/original wording: {"Yes" if preserve else "No"}
- Avoid clichés: {"Yes" if avoid_cliches else "No"}
- Explain why each option works: {"Yes" if explain else "No"}
- Creativity direction: {CREATIVITY[creativity]}

Important: If the writer supplied multiple bars, infer their existing meaning and cadence before suggesting
anything. Do not force every option into the same image family. Give genuinely different conceptual routes.
"""

def call_model(client, model, prompt):
    response = client.responses.create(
        model=model,
        reasoning={"effort": "low"},
        instructions=SYSTEM_PROMPT,
        input=prompt,
    )
    return response.output_text

st.title("🔥 Metaphor Forge")
st.caption("Metaphors, punchlines, double meanings, and rhyme rescue for rap & poetry.")

with st.sidebar:
    st.header("Engine")
    api_key = get_api_key()
    if not api_key:
        api_key = st.text_input(
            "OpenAI API key",
            type="password",
            help="Used only for this session unless you set OPENAI_API_KEY in your environment.",
        )
    model = st.text_input(
        "Model",
        value=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"),
        help="Change this if your OpenAI account uses a different available model.",
    )
    creativity = st.select_slider(
        "Creativity",
        options=["Focused", "Balanced", "Wild"],
        value="Balanced",
    )
    st.divider()
    st.caption("Your API key is never written to this project's source files.")

source = st.text_area(
    "Your line, bars, idea, or theme",
    height=170,
    placeholder=(
        "Example:\n"
        "I kept climbing even when everybody expected me to fall.\n"
        "I need an image for ambition and survival."
    ),
)

c1, c2 = st.columns(2)
with c1:
    rhyme_target = st.text_input(
        "Rhyme target (optional)",
        placeholder="e.g. trajectory, better now, dominance",
    )
    mode = st.selectbox("Mode", MODES)
    tone = st.selectbox("Tone", TONES)
with c2:
    strictness = st.selectbox("Rhyme strictness", STRICTNESS, index=2)
    complexity = st.selectbox("Complexity", COMPLEXITY, index=1)
    count = st.slider("Number of ideas", 4, 12, 6)

imagery = st.multiselect(
    "Imagery you want to explore (optional)",
    IMAGERY,
    default=[],
)

o1, o2, o3 = st.columns(3)
with o1:
    preserve = st.checkbox("Protect my wording", value=True)
with o2:
    avoid_cliches = st.checkbox("Avoid clichés", value=True)
with o3:
    explain = st.checkbox("Explain connections", value=False)

if "last_result" not in st.session_state:
    st.session_state.last_result = ""
if "last_prompt" not in st.session_state:
    st.session_state.last_prompt = ""

generate = st.button("Forge ideas", type="primary", use_container_width=True)

if generate:
    if not source.strip():
        st.warning("Add a line, some bars, or an idea first.")
    elif not api_key:
        st.warning("Add an OpenAI API key in the sidebar or set OPENAI_API_KEY.")
    else:
        client = OpenAI(api_key=api_key)
        prompt = build_user_prompt(
            source=source,
            rhyme_target=rhyme_target,
            mode=mode,
            strictness=strictness,
            tone=tone,
            complexity=complexity,
            imagery=imagery,
            count=count,
            preserve=preserve,
            avoid_cliches=avoid_cliches,
            explain=explain,
            creativity=creativity,
        )
        try:
            with st.spinner("Forging connections..."):
                result = call_model(client, model, prompt)
            st.session_state.last_result = result
            st.session_state.last_prompt = prompt
        except Exception as exc:
            st.error(f"Generation failed: {exc}")

if st.session_state.last_result:
    st.divider()
    st.subheader("Ideas")
    st.markdown(st.session_state.last_result)

    st.divider()
    st.subheader("Refine the result")
    refinement = st.text_input(
        "Tell the bot what to change",
        placeholder="Make #3 darker, keep the same rhyme sound, and turn it into a 2-bar punchline.",
    )
    refine = st.button("Refine", use_container_width=True)

    if refine:
        if not api_key:
            st.warning("Add an OpenAI API key first.")
        elif not refinement.strip():
            st.warning("Tell the bot what you want changed.")
        else:
            client = OpenAI(api_key=api_key)
            refinement_prompt = f"""
ORIGINAL WRITER REQUEST:
{st.session_state.last_prompt}

PREVIOUS RESPONSE:
{st.session_state.last_result}

WRITER'S REFINEMENT:
{refinement}

Revise only what the writer is asking to refine. Preserve the useful parts and their voice.
"""
            try:
                with st.spinner("Refining..."):
                    result = call_model(client, model, refinement_prompt)
                st.session_state.last_result = result
                st.rerun()
            except Exception as exc:
                st.error(f"Refinement failed: {exc}")

st.divider()
with st.expander("What each mode does"):
    st.markdown(
        """
- **Metaphor:** turns the idea into a direct image or conceptual comparison.
- **Simile:** builds explicit comparisons without losing cadence.
- **Punchline:** prioritizes setup/payoff and surprise.
- **Double Meaning:** looks for two coherent readings of the same wording.
- **Extended Metaphor:** carries one image through multiple connected bars.
- **Rhyme Rescue:** works backward from your rhyme target to preserve meaning and land the sound.
        """
    )
