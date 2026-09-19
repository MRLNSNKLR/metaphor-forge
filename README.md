# Metaphor Forge v3

Version 3 adds true cloud persistence with Supabase.

## New in v3

- Email/password accounts
- Permanent cloud Library
- Permanent cloud Rhyme Bank
- Sync across devices
- Row Level Security so each account can access only its own rows
- Import a v2 JSON Library into the cloud
- JSON and Markdown backups

## Setup

### 1. Create a Supabase project
Create a Supabase project and copy its Project URL and publishable key (or legacy anon key).
Do not use the service-role key in this app.

### 2. Create the database tables
Open Supabase SQL Editor, paste the entire contents of `supabase_schema.sql`, and run it once.

### 3. Update Streamlit Secrets
Keep your existing OpenAI key and add:

```toml
OPENAI_API_KEY = "your_existing_openai_key"
SUPABASE_URL = "https://YOUR_PROJECT.supabase.co"
SUPABASE_PUBLISHABLE_KEY = "your_supabase_publishable_key"
```

If your project only exposes a legacy anon key, use `SUPABASE_KEY` instead.
Never use a service-role key.

### 4. Update GitHub
Replace `app.py` and `requirements.txt` in your existing repository. Add `supabase_schema.sql` and `.gitignore`.
Commit the changes; Streamlit should redeploy automatically.

### 5. Create your Metaphor Forge account
Open the app, choose **Create account**, and enter your email/password.
Hosted Supabase projects commonly require email confirmation by default. If prompted, confirm the email and then sign in.

### 6. Import v2 work
If you exported `metaphor_forge_library.json` from v2, open **Import/Backup**, upload it, and tap **Import into my cloud account**.

## Security
The app uses a publishable/anon Supabase client key with authenticated user sessions. Both tables have Row Level Security policies that require `auth.uid() = user_id`, so users can only read or change their own rows.

Your OpenAI API key remains in Streamlit Secrets and is never included in exported files.
