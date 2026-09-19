import os
import json
import uuid
from datetime import datetime, timezone

import streamlit as st
from openai import OpenAI

st.set_page_config(
    page_title="Metaphor Forge v2",
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
- For multisyllabic rhymes, pay attention to stressed vowel sequence and nearby consonants.
- A metaphor should create a real conceptual link, not merely place two rhyming words together.
- Keep suggestions performable: natural syntax, believable phrasing, and strong cadence.
- Avoid filler that exists only to force a rhyme.
- When the writer asks to preserve wording, do not change their quoted original words.
- You may use profanity if the user's own writing or requested tone makes it appropriate.
- Do not imitate a living artist's exact style. Broad traits such as dense, conversational,
  technical, cinematic, aggressive, introspective, or punchline-heavy are fine.

MODES
Metaphor: create direct metaphor concepts and bars.
Simile: create comparisons using like/as or equivalent constructions.
Punchline: favor setup/payoff, surprise, and double interpretation.
Double Meaning: build bars that support two coherent readings.
Extended Metaphor: develop one image across multiple connected lines.
Rhyme Rescue: diagnose the target sound and offer ways to land the rhyme without sacrificing meaning.

OUTPUT STYLES
Concepts + Bars: give both the conceptual connection and usable lines.
Concepts Only: do not write finished bars. Give metaphor ideas, image directions, possible objects/actions,
and rhyme-friendly vocabulary so the writer can construct the bar themselves.
Bars Only: keep explanation minimal and prioritize usable lines.

OUTPUT
Start with a short "Sound map" only if a rhyme target exists. Describe the rhyme sound in plain language
and mention whether proposed matches are exact, multisyllabic, slant, or loose.

Then give the requested number of numbered options.

For Concepts + Bars:
### N. Short concept name
**Concept:** one sentence explaining the connection.
**Bar:** one or two usable lines, unless Extended Metaphor was requested.
**Rhyme fit:** brief note if a target exists.
Only add **Why it works:** when requested.

For Concepts Only:
### N. Short concept name
**Connection:** explain the metaphor.
**Images/actions:** 3–6 concrete directions the writer could use.
**Rhyme fuel:** useful words or short phrases that fit the requested sound when possible.
Do NOT provide a finished rap bar.

For Bars Only:
### N.
**Bar:** one or two usable lines.
**Rhyme fit:** brief note if a target exists.

When Extended Metaphor is selected, give 2–4 connected lines per option unless Concepts Only is selected.
When Rhyme Rescue is selected, include at least one option that preserves as much original wording as possible.
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

OUTPUT_STYLES = [
    "Concepts + Bars",
    "Concepts Only",
    "Bars Only",
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
    "Focused": "Stay close to the literal meaning and prioritize clean, usable ideas.",
    "Balanced": "Balance clarity, originality, and surprising connections.",
    "Wild": "Take bigger conceptual leaps, but keep every metaphor logically defensible.",
}


def init_state():
    defaults = {
        "last_result": "",
        "last_prompt": "",
        "last_metadata": {},
        "library": [],
        "rhyme_bank": [],
        "flash": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


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
    output_style,
    strictness,
    tone,
    complexity,
    imagery,
    count,
    preserve,
    avoid_cliches,
    explain,
    creativity,
    rhyme_bank_terms,
):
    imagery_text = ", ".join(imagery) if imagery else "No preference"
    bank_text = ", ".join(rhyme_bank_terms) if rhyme_bank_terms else "None"
    return f"""
WRITER INPUT:
{source}

REQUEST:
- Mode: {mode}
- Output style: {output_style}
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
- Writer's optional personal rhyme-bank terms: {bank_text}

Important:
- If the writer supplied multiple bars, infer their meaning and cadence before suggesting anything.
- Do not force every option into the same image family.
- Give genuinely different conceptual routes.
- Personal rhyme-bank terms are optional inspiration, not mandatory words.
"""


def call_model(client, model, prompt):
    response = client.responses.create(
        model=model,
        reasoning={"effort": "low"},
        instructions=SYSTEM_PROMPT,
        input=prompt,
    )
    return response.output_text


def make_library_markdown(items):
    lines = ["# Metaphor Forge Library", ""]
    if not items:
        lines.append("_No saved results yet._")
        return "\n".join(lines)

    for i, item in enumerate(items, 1):
        title = item.get("title") or f"Saved Result {i}"
        lines.extend([
            f"## {i}. {title}",
            "",
            f"- **Saved:** {item.get('saved_at', '')}",
            f"- **Mode:** {item.get('mode', '')}",
            f"- **Output:** {item.get('output_style', '')}",
            f"- **Rhyme target:** {item.get('rhyme_target') or 'None'}",
            f"- **Tags:** {', '.join(item.get('tags', [])) or 'None'}",
            "",
            "### Original input",
            "",
            item.get("source", ""),
            "",
        ])
        notes = item.get("notes", "").strip()
        if notes:
            lines.extend(["### Notes", "", notes, ""])
        lines.extend(["### Result", "", item.get("result", ""), "", "---", ""])
    return "\n".join(lines)


def library_json_bytes(items, rhyme_bank):
    payload = {
        "format": "metaphor-forge-library",
        "version": 2,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "library": items,
        "rhyme_bank": rhyme_bank,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def import_library(uploaded):
    data = json.loads(uploaded.getvalue().decode("utf-8"))
    if data.get("format") != "metaphor-forge-library":
        raise ValueError("This does not look like a Metaphor Forge library file.")
    library = data.get("library", [])
    rhyme_bank = data.get("rhyme_bank", [])
    if not isinstance(library, list) or not isinstance(rhyme_bank, list):
        raise ValueError("The library file is malformed.")
    return library, rhyme_bank


init_state()

st.title("🔥 Metaphor Forge v2")
st.caption("Metaphors, rhyme rescue, punchlines, a personal rhyme bank, and a saveable writing library.")

tabs = st.tabs(["✍️ Forge", "📚 Library", "🎵 Rhyme Bank"])

with st.sidebar:
    st.header("Engine")
    api_key = get_api_key()
    if not api_key:
        api_key = st.text_input(
            "OpenAI API key",
            type="password",
            help="Used only for this session unless OPENAI_API_KEY is configured in Streamlit secrets.",
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
    st.caption("API keys are not stored in your saved-result exports.")

with tabs[0]:
    if st.session_state.flash:
        st.success(st.session_state.flash)
        st.session_state.flash = ""

    source = st.text_area(
        "Your line, bars, idea, or theme",
        height=170,
        placeholder=(
            "Example:\n"
            "Every day it's the same thing, same grind.\n"
            "Can I catch me a break just one time?"
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
        output_style = st.selectbox("Output style", OUTPUT_STYLES)
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

    use_rhyme_bank = st.checkbox(
        "Use my personal rhyme bank as optional inspiration",
        value=False,
        disabled=not bool(st.session_state.rhyme_bank),
    )

    generate = st.button("Forge ideas", type="primary", use_container_width=True)

    if generate:
        if not source.strip():
            st.warning("Add a line, some bars, or an idea first.")
        elif not api_key:
            st.warning("Add an OpenAI API key or configure OPENAI_API_KEY in Streamlit secrets.")
        else:
            client = OpenAI(api_key=api_key)
            prompt = build_user_prompt(
                source=source,
                rhyme_target=rhyme_target,
                mode=mode,
                output_style=output_style,
                strictness=strictness,
                tone=tone,
                complexity=complexity,
                imagery=imagery,
                count=count,
                preserve=preserve,
                avoid_cliches=avoid_cliches,
                explain=explain,
                creativity=creativity,
                rhyme_bank_terms=st.session_state.rhyme_bank if use_rhyme_bank else [],
            )
            try:
                with st.spinner("Forging connections..."):
                    result = call_model(client, model, prompt)
                st.session_state.last_result = result
                st.session_state.last_prompt = prompt
                st.session_state.last_metadata = {
                    "source": source,
                    "rhyme_target": rhyme_target,
                    "mode": mode,
                    "output_style": output_style,
                    "strictness": strictness,
                    "tone": tone,
                    "complexity": complexity,
                    "imagery": imagery,
                    "creativity": creativity,
                }
            except Exception as exc:
                st.error(f"Generation failed: {exc}")

    if st.session_state.last_result:
        st.divider()
        st.subheader("Ideas")
        st.markdown(st.session_state.last_result)

        st.subheader("Save this result")
        s1, s2 = st.columns(2)
        with s1:
            save_title = st.text_input(
                "Title",
                placeholder="e.g. Same Grind / Break Metaphors",
                key="save_title",
            )
        with s2:
            save_tags_text = st.text_input(
                "Tags",
                placeholder="grind, work, frustration",
                key="save_tags",
            )
        save_notes = st.text_area(
            "Notes (optional)",
            placeholder="What I liked, which idea I want to use, etc.",
            height=80,
            key="save_notes",
        )

        if st.button("💾 Save to Library", use_container_width=True):
            meta = st.session_state.last_metadata
            item = {
                "id": str(uuid.uuid4()),
                "saved_at": datetime.now(timezone.utc).isoformat(),
                "title": save_title.strip() or f"{meta.get('mode', 'Idea')} — {meta.get('rhyme_target') or 'No rhyme target'}",
                "tags": [x.strip() for x in save_tags_text.split(",") if x.strip()],
                "notes": save_notes.strip(),
                "source": meta.get("source", ""),
                "rhyme_target": meta.get("rhyme_target", ""),
                "mode": meta.get("mode", ""),
                "output_style": meta.get("output_style", ""),
                "strictness": meta.get("strictness", ""),
                "tone": meta.get("tone", ""),
                "complexity": meta.get("complexity", ""),
                "imagery": meta.get("imagery", []),
                "creativity": meta.get("creativity", ""),
                "result": st.session_state.last_result,
            }
            st.session_state.library.insert(0, item)
            st.session_state.flash = "Saved to your Library. Export the Library if you want to keep it permanently."
            st.rerun()

        st.divider()
        st.subheader("Refine the result")
        refinement = st.text_input(
            "Tell the bot what to change",
            placeholder="Make #3 darker, keep the rhyme sound, but don't write the full bar.",
        )

        if st.button("Refine", use_container_width=True):
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

Revise only what the writer is asking to refine. Preserve useful parts and the writer's voice.
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

with tabs[1]:
    st.subheader("📚 Saved Results")
    st.caption(
        "Library saves last for this browser session. Export it to your phone if you want a permanent backup."
    )

    uploaded = st.file_uploader(
        "Import a Metaphor Forge library (.json)",
        type=["json"],
        key="library_import",
    )
    if uploaded is not None:
        if st.button("Import Library"):
            try:
                imported_library, imported_bank = import_library(uploaded)
                existing_ids = {x.get("id") for x in st.session_state.library}
                additions = [x for x in imported_library if x.get("id") not in existing_ids]
                st.session_state.library = additions + st.session_state.library

                existing_terms = {x.casefold() for x in st.session_state.rhyme_bank}
                for term in imported_bank:
                    if isinstance(term, str) and term.casefold() not in existing_terms:
                        st.session_state.rhyme_bank.append(term)
                        existing_terms.add(term.casefold())

                st.success(f"Imported {len(additions)} saved result(s).")
            except Exception as exc:
                st.error(f"Import failed: {exc}")

    if st.session_state.library:
        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "⬇️ Export Library (JSON)",
                data=library_json_bytes(st.session_state.library, st.session_state.rhyme_bank),
                file_name="metaphor_forge_library.json",
                mime="application/json",
                use_container_width=True,
            )
        with col2:
            st.download_button(
                "⬇️ Export Library (Markdown)",
                data=make_library_markdown(st.session_state.library),
                file_name="metaphor_forge_library.md",
                mime="text/markdown",
                use_container_width=True,
            )

        st.divider()

        search = st.text_input(
            "Search saved results",
            placeholder="title, tag, rhyme, phrase...",
            key="library_search",
        ).strip().casefold()

        filtered = []
        for item in st.session_state.library:
            haystack = " ".join([
                item.get("title", ""),
                " ".join(item.get("tags", [])),
                item.get("source", ""),
                item.get("result", ""),
                item.get("rhyme_target", ""),
                item.get("notes", ""),
            ]).casefold()
            if not search or search in haystack:
                filtered.append(item)

        st.caption(f"{len(filtered)} result(s) shown")

        for item in filtered:
            title = item.get("title", "Untitled")
            with st.expander(f"⭐ {title}"):
                st.caption(
                    f"{item.get('mode', '')} • {item.get('output_style', '')} • "
                    f"rhyme: {item.get('rhyme_target') or 'none'}"
                )

                tags = item.get("tags", [])
                if tags:
                    st.write("**Tags:** " + ", ".join(tags))

                notes = item.get("notes", "").strip()
                if notes:
                    st.write("**Notes:** " + notes)

                st.write("**Original input**")
                st.code(item.get("source", ""), language=None)

                st.write("**Saved result**")
                st.markdown(item.get("result", ""))

                if st.button(
                    "Delete from Library",
                    key=f"delete_{item.get('id')}",
                    use_container_width=True,
                ):
                    st.session_state.library = [
                        x for x in st.session_state.library
                        if x.get("id") != item.get("id")
                    ]
                    st.rerun()
    else:
        st.info("Nothing saved yet. Generate ideas in the Forge tab, then tap “Save to Library.”")

with tabs[2]:
    st.subheader("🎵 Personal Rhyme Bank")
    st.caption("Keep words and phrases you like. The Forge can use them as optional inspiration.")

    new_term = st.text_input(
        "Add a word or phrase",
        placeholder="e.g. trajectory, bottomless, temporal telepathy",
        key="new_rhyme_term",
    )

    if st.button("Add to Rhyme Bank", use_container_width=True):
        term = new_term.strip()
        if not term:
            st.warning("Enter a word or phrase first.")
        elif term.casefold() in {x.casefold() for x in st.session_state.rhyme_bank}:
            st.info("That term is already in your rhyme bank.")
        else:
            st.session_state.rhyme_bank.append(term)
            st.success(f"Added “{term}”.")

    if st.session_state.rhyme_bank:
        st.divider()
        for idx, term in enumerate(list(st.session_state.rhyme_bank)):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.write(term)
            with c2:
                if st.button("✕", key=f"rm_rhyme_{idx}", help=f"Remove {term}"):
                    st.session_state.rhyme_bank.pop(idx)
                    st.rerun()
    else:
        st.info("Your rhyme bank is empty.")

st.divider()
st.caption(
    "Tip: Export your JSON library after an important writing session. "
    "You can import it later to restore saved results and your rhyme bank."
)
