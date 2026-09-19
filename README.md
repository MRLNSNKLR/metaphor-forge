# Metaphor Forge v1

A small Streamlit bot for generating metaphor concepts, rhyme-aware bars, punchlines,
double meanings, extended metaphors, and "rhyme rescue" suggestions.

## What it does

- Accepts a line, several bars, an idea, or a theme.
- Optional rhyme target.
- Exact, multisyllabic, slant, loose, or no-rhyme modes.
- Metaphor, simile, punchline, double-meaning, extended-metaphor, and rhyme-rescue modes.
- Tone, complexity, imagery, and creativity controls.
- "Protect my wording" option.
- Follow-up refinement of the last result.

## Run it locally

1. Install Python 3.10+.
2. Open a terminal in this folder.
3. Create and activate a virtual environment (recommended).
4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Set your API key.

   macOS/Linux:
   ```bash
   export OPENAI_API_KEY="your_key_here"
   ```

   Windows PowerShell:
   ```powershell
   $env:OPENAI_API_KEY="your_key_here"
   ```

   You can also start the app and paste the key into the password field in the sidebar.

6. Run:

   ```bash
   streamlit run app.py
   ```

7. Open the local URL Streamlit shows in your browser.

## Model

The default is `gpt-5.6-luna` because this kind of high-volume creative ideation benefits
from a lower-cost model. Change `OPENAI_MODEL` or the Model field in the sidebar if desired.

## Security note

Do not hard-code or commit your API key. This project reads it from the environment,
Streamlit secrets, or the temporary password field.

## Suggested v2 features

- Save favorite metaphors and bars.
- Build a personal rhyme bank.
- Analyze syllables and stressed-vowel patterns locally.
- Highlight internal rhymes and multisyllabic chains.
- Song/project folders.
- "Don't write the bar for me" mode that gives concepts only.
- Mobile-first deployment.
