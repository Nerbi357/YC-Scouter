# Hosting the dashboard on Streamlit Community Cloud

The dashboard can live at a permanent URL, independent of Colab. This guide sets
that up and — importantly — makes your **notes/tags/stages persist** across
restarts.

## Why persistence needs an external store (read this first)

Streamlit Community Cloud runs your app in an **ephemeral container**: its disk is
rebuilt from your GitHub repo on every restart (sleep→wake, each `git push`,
platform maintenance). Anything the app writes to a local file — e.g.
`data/user_data.csv` — is therefore **wiped on the next restart**.

So the app stores annotations in **Google Sheets** when configured. Writes go to
the Sheet (outside the container) and survive every restart. Without it, the app
still runs but shows a "edits won't persist" banner and uses a temp CSV.

---

## Step 1 — Put the dataset in the repo

The dashboard reads `data/processed/yc_radar.parquet`. That path is normally
gitignored, but `.gitignore` has an explicit exception for this one file.

1. Download `yc_radar.parquet` from your Google Drive (`VC PROJECT FINAL/processed/`).
2. Put it at `data/processed/yc_radar.parquet` in the repo and commit it:
   ```bash
   git add -f data/processed/yc_radar.parquet
   git commit -m "Add dashboard dataset"
   git push
   ```
   (It's public YC data, safe to commit. ~a few MB.)

## Step 2 — Deploy on Streamlit Community Cloud

1. Go to <https://share.streamlit.io> and sign in with GitHub.
2. **New app** → pick this repo, branch, and main file **`app.py`**.
3. Deploy. First build installs `requirements.txt` (a couple of minutes).

You now have a permanent URL. It sleeps after inactivity and wakes on the next
visit (~10 s). Editing notes shows a banner until you do Step 3.

## Step 3 — Make notes persist (Google Sheets)

**a) Create a service account + key**
1. <https://console.cloud.google.com> → create/select a project.
2. APIs & Services → **Enable APIs** → enable **Google Sheets API** and **Google Drive API**.
3. IAM & Admin → **Service Accounts** → Create → give it a name (e.g. `yc-radar`).
4. On the service account → **Keys** → Add key → **JSON** → download it.

**b) Create the Sheet and share it**
1. Create a new Google Sheet (any name).
2. Click **Share** and add the service account's email
   (`...@...iam.gserviceaccount.com`, from the JSON) as **Editor**.
3. Copy the sheet URL (or its ID from the URL).

**c) Give the secrets to Streamlit**
1. In Streamlit Cloud → your app → **⋮ → Settings → Secrets**.
2. Paste the contents of `.streamlit/secrets.toml.example`, filled in from your
   downloaded JSON (`private_key`, `client_email`, …) and your sheet URL.
3. Save. The app restarts and the banner turns into "Google Sheets ✅".

That's it — notes/tags/stages now survive restarts, and you can even open the
Sheet to view/edit them by hand.

> Testing locally with Sheets? Put the same content in `.streamlit/secrets.toml`
> (gitignored) and run `streamlit run app.py`.

## Step 4 — Share the link so visitors can't change your notes

You want to send the URL to other people, let them explore, but keep **your**
notes private and untouched — their edits should be temporary. That's built in:

1. In your secrets, add an owner lock (already in the example):
   ```toml
   [app]
   owner_key = "some-long-random-passphrase"
   ```
2. Save. Now:
   - **You** open the app, expand **🔒 Режим владельца** in the sidebar, enter the
     key once → the **💾 Save** button appears and writes to Google Sheets.
   - **Visitors** (no key) get a **👀 view mode**: they can filter, chart, compare,
     and even edit the notes table *for themselves*, but there's **no Save** — their
     changes live only in their browser session and vanish on refresh. Your Sheet is
     never modified. They can download their temporary edits as CSV if they want.
3. Make the app public: Streamlit Cloud → app **Settings → Sharing** → set it so
   "anyone with the link can view". Send them the URL.

> Without `[app] owner_key`, the app is single-user: anyone who opens it can save.
> Fine for just you; add the key before sharing.

### Other sharing models (if you need more)

- **Hide your notes from visitors** too (they see blank annotation columns instead
  of your notes) — a small tweak; ask and I'll add a `hide_owner_notes` flag.
- **Per-visitor persistent notes** (each person logs in and keeps their *own* saved
  notes) — needs real login (Streamlit `st.login` / Google OIDC) and a per-user tab
  in the Sheet. More setup; doable if you want a true multi-user tool.

---

## Alternatives (if you outgrow the free tier)

| Option | When to pick it |
|---|---|
| **Hugging Face Spaces** | Same idea, always-on; still needs Sheets for persistence. |
| **Render / Railway / Fly.io** | Want a persistent disk or a real DB (SQLite/Postgres) instead of Sheets. |
| **Small VPS (~$5/mo)** | Full control, everything on one always-on box. |

The app code doesn't change for any of these — only where the dataset and the
annotations store live.
