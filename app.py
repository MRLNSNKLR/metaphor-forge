import os, json, uuid
from datetime import datetime, timezone
import streamlit as st
from openai import OpenAI
from supabase import create_client

st.set_page_config(page_title="Metaphor Forge v3", page_icon="🔥", layout="centered")

SYSTEM_PROMPT = """
You are Metaphor Forge, a specialist songwriting assistant for rappers and poets.
Help the writer discover vivid metaphorical connections that preserve meaning, fit rhyme constraints,
and sound natural in bars. Prefer fresh, specific imagery over clichés. If a rhyme target is supplied,
prioritize sound fit and meaning. Distinguish exact, multisyllabic, slant, and loose rhymes; never call
a near rhyme exact. Preserve the writer's voice and quoted wording when requested. Avoid filler used
only to force rhyme. Do not imitate a living artist's exact style.

Modes: Metaphor, Simile, Punchline, Double Meaning, Extended Metaphor, Rhyme Rescue.
Output styles:
- Concepts + Bars: give a concept, usable bar(s), and rhyme-fit note when relevant.
- Concepts Only: do not write finished bars; give connections, images/actions, and rhyme fuel.
- Bars Only: prioritize usable lines and keep explanation minimal.
If a rhyme target exists, begin with a brief Sound map. Give the requested number of genuinely different
options. Extended Metaphor may use 2–4 connected lines. Rhyme Rescue should include at least one option
that preserves as much of the original line as possible.
"""

MODES = ["Metaphor", "Simile", "Punchline", "Double Meaning", "Extended Metaphor", "Rhyme Rescue"]
OUTPUT_STYLES = ["Concepts + Bars", "Concepts Only", "Bars Only"]
STRICTNESS = ["Exact rhyme", "Multisyllabic rhyme", "Slant rhyme", "Loose sonic echo", "No rhyme constraint"]
TONES = ["Balanced", "Introspective", "Aggressive", "Triumphant", "Dark", "Romantic", "Cinematic", "Witty", "Motivational"]
COMPLEXITY = ["Clean & direct", "Layered", "Dense / technical"]
IMAGERY = ["Space / astronomy", "Nature / weather", "Technology", "Science", "Myth / legend", "Sports", "Business / power", "Architecture", "Vehicles / motion", "History", "No preference"]
CREATIVITY = {
    "Focused": "Stay close to the literal meaning and prioritize clean, usable ideas.",
    "Balanced": "Balance clarity, originality, and surprising connections.",
    "Wild": "Take bigger conceptual leaps, but keep every metaphor logically defensible.",
}


def init_state():
    defaults = {
        "last_result": "", "last_prompt": "", "last_metadata": {},
        "access_token": "", "refresh_token": "", "user_id": "", "user_email": "", "flash": ""
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def get_secret(name):
    if os.getenv(name):
        return os.getenv(name)
    try:
        return st.secrets.get(name, "")
    except Exception:
        return ""


def clear_auth():
    for k in ["access_token", "refresh_token", "user_id", "user_email"]:
        st.session_state[k] = ""


def save_auth_response(resp):
    session = getattr(resp, "session", None)
    user = getattr(resp, "user", None)
    if session:
        st.session_state.access_token = session.access_token
        st.session_state.refresh_token = session.refresh_token
    if user:
        st.session_state.user_id = str(user.id)
        st.session_state.user_email = user.email or ""


def get_supabase():
    url = get_secret("SUPABASE_URL")
    key = get_secret("SUPABASE_PUBLISHABLE_KEY") or get_secret("SUPABASE_KEY") or get_secret("SUPABASE_ANON_KEY")
    if not url or not key:
        return None, None, "Supabase is not configured yet."
    sb = create_client(url, key)
    if not st.session_state.access_token or not st.session_state.refresh_token:
        return sb, None, None
    try:
        resp = sb.auth.set_session(st.session_state.access_token, st.session_state.refresh_token)
        save_auth_response(resp)
        user_resp = sb.auth.get_user()
        user = getattr(user_resp, "user", None)
        if not user:
            clear_auth()
            return sb, None, None
        st.session_state.user_id = str(user.id)
        st.session_state.user_email = user.email or ""
        return sb, user, None
    except Exception:
        clear_auth()
        return sb, None, None


def call_model(model, prompt):
    client = OpenAI(api_key=get_secret("OPENAI_API_KEY"))
    resp = client.responses.create(model=model, reasoning={"effort": "low"}, instructions=SYSTEM_PROMPT, input=prompt)
    return resp.output_text


def build_prompt(source, rhyme_target, mode, output_style, strictness, tone, complexity, imagery, count,
                 preserve, avoid_cliches, explain, creativity, rhyme_terms):
    return f"""
WRITER INPUT:
{source}

REQUEST:
- Mode: {mode}
- Output style: {output_style}
- Rhyme target: {rhyme_target or 'None'}
- Rhyme strictness: {strictness}
- Tone: {tone}
- Complexity: {complexity}
- Imagery domains: {', '.join(imagery) if imagery else 'No preference'}
- Number of options: {count}
- Preserve original wording: {'Yes' if preserve else 'No'}
- Avoid clichés: {'Yes' if avoid_cliches else 'No'}
- Explain connections: {'Yes' if explain else 'No'}
- Creativity direction: {CREATIVITY[creativity]}
- Optional personal rhyme-bank terms: {', '.join(rhyme_terms) if rhyme_terms else 'None'}

If multiple bars are supplied, infer their meaning and cadence first. Give genuinely different conceptual routes.
Personal rhyme-bank terms are optional inspiration, not mandatory words.
"""


def fetch_library(sb):
    return (sb.table("saved_results").select("*").order("created_at", desc=True).execute().data or [])


def fetch_rhymes(sb):
    return (sb.table("rhyme_bank").select("id,term,created_at").order("created_at", desc=False).execute().data or [])


def save_result(sb, meta, result, title, tags, notes):
    row = {
        "user_id": st.session_state.user_id,
        "title": title.strip() or f"{meta.get('mode','Idea')} — {meta.get('rhyme_target') or 'No rhyme target'}",
        "tags": [x.strip() for x in tags.split(",") if x.strip()],
        "notes": notes.strip(), "source": meta.get("source", ""), "result": result,
        "rhyme_target": meta.get("rhyme_target", ""), "mode": meta.get("mode", ""),
        "output_style": meta.get("output_style", ""), "strictness": meta.get("strictness", ""),
        "tone": meta.get("tone", ""), "complexity": meta.get("complexity", ""),
        "imagery": meta.get("imagery", []), "creativity": meta.get("creativity", ""),
    }
    sb.table("saved_results").insert(row).execute()


def export_json(library, rhymes):
    payload = {
        "format": "metaphor-forge-library", "version": 3,
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "library": library, "rhyme_bank": [r.get("term", "") for r in rhymes],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")


def export_markdown(items):
    lines = ["# Metaphor Forge Cloud Library", ""]
    for i, item in enumerate(items, 1):
        lines += [f"## {i}. {item.get('title') or 'Untitled'}", "",
                  f"- **Saved:** {item.get('created_at','')}",
                  f"- **Mode:** {item.get('mode','')}",
                  f"- **Rhyme target:** {item.get('rhyme_target') or 'None'}", "",
                  "### Original input", "", item.get("source", ""), ""]
        if (item.get("notes") or "").strip():
            lines += ["### Notes", "", item.get("notes", ""), ""]
        lines += ["### Result", "", item.get("result", ""), "", "---", ""]
    return "\n".join(lines)


def valid_uuid(value):
    try:
        return str(uuid.UUID(str(value)))
    except Exception:
        return str(uuid.uuid4())


def import_backup(sb, uploaded):
    data = json.loads(uploaded.getvalue().decode("utf-8"))
    if data.get("format") != "metaphor-forge-library":
        raise ValueError("This is not a Metaphor Forge library export.")
    library, rhyme_bank = data.get("library", []), data.get("rhyme_bank", [])
    if not isinstance(library, list) or not isinstance(rhyme_bank, list):
        raise ValueError("The library file is malformed.")
    result_count = 0
    for item in library:
        if not isinstance(item, dict):
            continue
        row = {
            "id": valid_uuid(item.get("id")), "user_id": st.session_state.user_id,
            "title": item.get("title") or "Imported result",
            "tags": item.get("tags") if isinstance(item.get("tags"), list) else [],
            "notes": item.get("notes") or "", "source": item.get("source") or "", "result": item.get("result") or "",
            "rhyme_target": item.get("rhyme_target") or "", "mode": item.get("mode") or "",
            "output_style": item.get("output_style") or "", "strictness": item.get("strictness") or "",
            "tone": item.get("tone") or "", "complexity": item.get("complexity") or "",
            "imagery": item.get("imagery") if isinstance(item.get("imagery"), list) else [],
            "creativity": item.get("creativity") or "",
        }
        sb.table("saved_results").upsert(row, on_conflict="id").execute()
        result_count += 1
    existing = {(r.get("term") or "").casefold() for r in fetch_rhymes(sb)}
    term_count = 0
    for term in rhyme_bank:
        if not isinstance(term, str) or not term.strip() or term.strip().casefold() in existing:
            continue
        try:
            sb.table("rhyme_bank").insert({"user_id": st.session_state.user_id, "term": term.strip()}).execute()
            existing.add(term.strip().casefold())
            term_count += 1
        except Exception:
            pass
    return result_count, term_count


def auth_screen(sb):
    st.title("🔥 Metaphor Forge v3")
    st.caption("Sign in to sync your writing library and rhyme bank across devices.")
    login_tab, signup_tab = st.tabs(["Sign in", "Create account"])
    with login_tab:
        with st.form("login"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign in", use_container_width=True)
        if submit:
            try:
                resp = sb.auth.sign_in_with_password({"email": email.strip(), "password": password})
                save_auth_response(resp)
                st.rerun()
            except Exception as exc:
                st.error(f"Sign-in failed: {exc}")
    with signup_tab:
        st.caption("Supabase may require email verification before your first sign-in.")
        with st.form("signup"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_pw")
            confirm = st.text_input("Confirm password", type="password")
            submit = st.form_submit_button("Create account", use_container_width=True)
        if submit:
            if not email.strip():
                st.warning("Enter your email.")
            elif len(password) < 8:
                st.warning("Use a password with at least 8 characters.")
            elif password != confirm:
                st.warning("The passwords do not match.")
            else:
                try:
                    resp = sb.auth.sign_up({"email": email.strip(), "password": password})
                    if getattr(resp, "session", None):
                        save_auth_response(resp)
                        st.rerun()
                    else:
                        st.success("Account created. Check your email for the confirmation link, then return and sign in.")
                except Exception as exc:
                    st.error(f"Account creation failed: {exc}")


init_state()
sb, user, config_error = get_supabase()
if config_error:
    st.error(config_error)
    st.info("Add SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY to Streamlit Secrets, then reboot the app.")
    st.stop()
if user is None:
    auth_screen(sb)
    st.stop()
if not get_secret("OPENAI_API_KEY"):
    st.error("OPENAI_API_KEY is missing from Streamlit Secrets.")
    st.stop()

st.title("🔥 Metaphor Forge v3")
st.caption("Your saved results and rhyme bank now sync to your cloud account.")
with st.sidebar:
    st.write(f"**Signed in as**  \n{st.session_state.user_email}")
    if st.button("Sign out", use_container_width=True):
        try: sb.auth.sign_out()
        except Exception: pass
        clear_auth(); st.rerun()
    st.divider()
    model = st.text_input("Model", value=os.getenv("OPENAI_MODEL", "gpt-5.6-luna"))
    creativity = st.select_slider("Creativity", options=["Focused", "Balanced", "Wild"], value="Balanced")
    st.caption("Your OpenAI API key stays in Streamlit Secrets and is never exported.")

tabs = st.tabs(["✍️ Forge", "☁️ Library", "🎵 Rhyme Bank", "⬆️ Import/Backup"])

with tabs[0]:
    if st.session_state.flash:
        st.success(st.session_state.flash); st.session_state.flash = ""
    try:
        rhyme_terms = [r.get("term", "") for r in fetch_rhymes(sb)]
    except Exception:
        rhyme_terms = []
    source = st.text_area("Your line, bars, idea, or theme", height=170,
                          placeholder="Example:\nEvery day it's the same thing, same grind.\nCan I catch me a break just one time?")
    c1, c2 = st.columns(2)
    with c1:
        rhyme_target = st.text_input("Rhyme target (optional)", placeholder="e.g. trajectory, better now, dominance")
        mode = st.selectbox("Mode", MODES)
        tone = st.selectbox("Tone", TONES)
    with c2:
        output_style = st.selectbox("Output style", OUTPUT_STYLES)
        strictness = st.selectbox("Rhyme strictness", STRICTNESS, index=2)
        complexity = st.selectbox("Complexity", COMPLEXITY, index=1)
    count = st.slider("Number of ideas", 4, 12, 6)
    imagery = st.multiselect("Imagery you want to explore (optional)", IMAGERY, default=[])
    o1, o2, o3 = st.columns(3)
    with o1: preserve = st.checkbox("Protect my wording", value=True)
    with o2: avoid_cliches = st.checkbox("Avoid clichés", value=True)
    with o3: explain = st.checkbox("Explain connections", value=False)
    use_bank = st.checkbox("Use my cloud rhyme bank as optional inspiration", value=False, disabled=not bool(rhyme_terms))
    if st.button("Forge ideas", type="primary", use_container_width=True):
        if not source.strip():
            st.warning("Add a line, some bars, or an idea first.")
        else:
            prompt = build_prompt(source, rhyme_target, mode, output_style, strictness, tone, complexity, imagery,
                                  count, preserve, avoid_cliches, explain, creativity, rhyme_terms if use_bank else [])
            try:
                with st.spinner("Forging connections..."):
                    result = call_model(model, prompt)
                st.session_state.last_result = result
                st.session_state.last_prompt = prompt
                st.session_state.last_metadata = {
                    "source": source, "rhyme_target": rhyme_target, "mode": mode, "output_style": output_style,
                    "strictness": strictness, "tone": tone, "complexity": complexity, "imagery": imagery,
                    "creativity": creativity,
                }
            except Exception as exc:
                st.error(f"Generation failed: {exc}")
    if st.session_state.last_result:
        st.divider(); st.subheader("Ideas"); st.markdown(st.session_state.last_result)
        st.subheader("Save to cloud")
        s1, s2 = st.columns(2)
        with s1: save_title = st.text_input("Title", placeholder="e.g. Same Grind / Break Metaphors")
        with s2: save_tags = st.text_input("Tags", placeholder="grind, work, frustration")
        save_notes = st.text_area("Notes (optional)", height=80)
        if st.button("☁️ Save permanently", use_container_width=True):
            try:
                save_result(sb, st.session_state.last_metadata, st.session_state.last_result, save_title, save_tags, save_notes)
                st.session_state.flash = "Saved permanently to your cloud Library."; st.rerun()
            except Exception as exc:
                st.error(f"Cloud save failed: {exc}")
        st.divider()
        refinement = st.text_input("Refine this result", placeholder="Make #3 darker, keep the rhyme sound, but don't write the full bar.")
        if st.button("Refine", use_container_width=True):
            if not refinement.strip():
                st.warning("Tell the bot what you want changed.")
            else:
                refine_prompt = f"ORIGINAL REQUEST:\n{st.session_state.last_prompt}\n\nPREVIOUS RESPONSE:\n{st.session_state.last_result}\n\nREFINEMENT:\n{refinement}\nRevise only what the writer asked to refine."
                try:
                    with st.spinner("Refining..."): st.session_state.last_result = call_model(model, refine_prompt)
                    st.rerun()
                except Exception as exc:
                    st.error(f"Refinement failed: {exc}")

with tabs[1]:
    st.subheader("☁️ Cloud Library")
    st.caption("These results are stored in Supabase and follow your account across devices.")
    try: library = fetch_library(sb)
    except Exception as exc: st.error(f"Could not load your Library: {exc}"); library = []
    search = st.text_input("Search saved results", placeholder="title, tag, rhyme, phrase...").strip().casefold()
    filtered = []
    for item in library:
        hay = " ".join([item.get("title") or "", " ".join(item.get("tags") or []), item.get("source") or "",
                        item.get("result") or "", item.get("rhyme_target") or "", item.get("notes") or ""]).casefold()
        if not search or search in hay: filtered.append(item)
    st.caption(f"{len(filtered)} result(s) shown")
    for item in filtered:
        with st.expander(f"⭐ {item.get('title') or 'Untitled'}"):
            st.caption(f"{item.get('mode') or ''} • {item.get('output_style') or ''} • rhyme: {item.get('rhyme_target') or 'none'}")
            if item.get("tags"): st.write("**Tags:** " + ", ".join(item.get("tags") or []))
            if (item.get("notes") or "").strip(): st.write("**Notes:** " + item.get("notes"))
            st.write("**Original input**"); st.code(item.get("source") or "", language=None)
            st.write("**Saved result**"); st.markdown(item.get("result") or "")
            if st.button("Delete", key=f"delete_{item.get('id')}", use_container_width=True):
                try: sb.table("saved_results").delete().eq("id", item.get("id")).execute(); st.rerun()
                except Exception as exc: st.error(f"Delete failed: {exc}")
    if not library: st.info("Your cloud Library is empty. Save a Forge result to start it.")

with tabs[2]:
    st.subheader("🎵 Cloud Rhyme Bank")
    new_term = st.text_input("Add a word or phrase", placeholder="e.g. trajectory, bottomless, temporal telepathy")
    if st.button("Add to Rhyme Bank", use_container_width=True):
        term = new_term.strip()
        if not term: st.warning("Enter a word or phrase first.")
        else:
            try: sb.table("rhyme_bank").insert({"user_id": st.session_state.user_id, "term": term}).execute(); st.rerun()
            except Exception as exc:
                if "duplicate" in str(exc).lower() or "unique" in str(exc).lower(): st.info("That term is already in your rhyme bank.")
                else: st.error(f"Could not add the term: {exc}")
    try: rhyme_rows = fetch_rhymes(sb)
    except Exception as exc: st.error(f"Could not load your rhyme bank: {exc}"); rhyme_rows = []
    for row in rhyme_rows:
        c1, c2 = st.columns([5, 1])
        with c1: st.write(row.get("term", ""))
        with c2:
            if st.button("✕", key=f"rm_{row.get('id')}"):
                try: sb.table("rhyme_bank").delete().eq("id", row.get("id")).execute(); st.rerun()
                except Exception as exc: st.error(f"Delete failed: {exc}")
    if not rhyme_rows: st.info("Your rhyme bank is empty.")

with tabs[3]:
    st.subheader("⬆️ Import v2 / Backup v3")
    st.write("Upload your v2 JSON Library once to move those saved results and rhyme-bank terms into your cloud account.")
    uploaded = st.file_uploader("Import Metaphor Forge JSON", type=["json"])
    if uploaded is not None and st.button("Import into my cloud account"):
        try:
            a, b = import_backup(sb, uploaded); st.success(f"Import complete: {a} result(s) and {b} rhyme-bank term(s) processed.")
        except Exception as exc: st.error(f"Import failed: {exc}")
    st.divider(); st.subheader("Backup")
    try:
        backup_library, backup_rhymes = fetch_library(sb), fetch_rhymes(sb)
        c1, c2 = st.columns(2)
        with c1: st.download_button("⬇️ JSON backup", data=export_json(backup_library, backup_rhymes), file_name="metaphor_forge_v3_backup.json", mime="application/json", use_container_width=True)
        with c2: st.download_button("⬇️ Markdown backup", data=export_markdown(backup_library), file_name="metaphor_forge_v3_library.md", mime="text/markdown", use_container_width=True)
    except Exception as exc: st.error(f"Could not prepare backup: {exc}")
