# Deploy the dashboard (Streamlit Community Cloud)

The dashboard can live at a permanent URL, independent of your machine. This guide
deploys it and makes your notes persist and your shared link safe.

## Why notes need an external store (read first)

Streamlit Community Cloud runs the app in an **ephemeral container**: its disk is
rebuilt from the repo on every restart (sleep→wake, each push, maintenance).
Anything the app writes to a local file (e.g. `data/user_data.csv`) is wiped on the
next restart. So notes are stored in **Google Sheets** when configured — writes go
to the Sheet (outside the container) and survive every restart. Without it, the app
still runs but shows an "edits won't persist" banner.

## Step 1 — Get the dataset into the repo

The dashboard reads the newest `data/yc_dataset_ai_*.parquet` (else `_base_`).
Produce it by running the two workflows (`Actions → Build Dataset`, then
`Build AI Summary`) — they commit the dated files. Or, from Colab, run the two
notebooks with the output switch on `commit` and push. (It's public YC data.)

## Step 2 — Deploy on Streamlit Community Cloud

1. Go to <https://share.streamlit.io> and sign in with GitHub.
2. **New app** → pick this repo, the branch, and main file **`app.py`**.
3. Deploy. First build installs `requirements.txt` (a couple of minutes).

You now have a permanent URL that redeploys automatically whenever a workflow (or
you) commits a new dataset. It sleeps after ~12 h idle and wakes on the next visit.

## Step 3 — Make notes persist (Google Sheets)

**a) Service account + key (free, no card).** In
<https://console.cloud.google.com>: create a project → **Enable** the *Google
Sheets API* and *Google Drive API* → **Credentials → Create credentials → Service
account** → on it, **Keys → Add key → JSON** (downloads the key). Use a *service
account*, not an API key, so no billing is required.

**b) Sheet + share.** Create a Google Sheet, **Share** it as **Editor** with the
service account's `client_email` (from the JSON). Copy the sheet URL.

**c) Secrets.** Streamlit Cloud → your app → **Settings → Secrets** → paste the
contents of `.streamlit/secrets.toml.example`, filled in from the JSON and the
sheet URL. Save; the app restarts and the banner turns into "Google Sheets ✅". Keep
the `\n` escapes in `private_key` intact — that's the #1 setup mistake.

## Step 4 — Share the link safely

Add an owner lock so visitors can't change your notes:

```toml
[app]
owner_key = "some-long-random-passphrase"
```

- **You**: expand **🔒 Режим владельца** in the sidebar, enter the key once → the
  **💾 Save** button appears and writes to Google Sheets.
- **Visitors**: get a view/explore mode — they can filter, chart, compare, and even
  edit the notes table for themselves, but there's no Save; their changes are
  session-only and never touch your Sheet. Make the app public in
  Streamlit **Settings → Sharing** and send the URL.

## Environment variables (optional)

- `YC_SCOUTER_DATASET` — force a specific parquet instead of the newest dated one.
- `YC_SCOUTER_USERDATA` — path for the local-CSV notes fallback.

## Phase 2 — a full website (later)

Reuse the same dataset as a data contract (parquet/JSON with pre-computed
`score`/`investability`/`ai_*`), build a static front-end (e.g. Cloudflare Pages),
and add a database (e.g. Supabase) only when multi-user notes/auth are needed. The
pipeline is unchanged.
