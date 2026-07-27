# How to deploy the dashboard

This guide takes you from a copy of this repository to a **live dashboard at a
permanent URL** that anyone can open, with your personal notes stored safely and
your link shareable without risk.

It is written for someone who has never deployed anything. Every step says where
to click and what you should see afterwards. The whole thing costs **nothing** —
no credit card, no server.

**Time:** ~10 minutes for the dashboard, ~15 more if you want notes that survive
restarts.

---

## What you are building

```
   GitHub repository                  Streamlit Community Cloud
   ┌──────────────────┐               ┌─────────────────────────┐
   │ app.py           │  reads code   │  your-app.streamlit.app │
   │ data/*.parquet   │ ────────────► │  (public URL, always on)│
   │ requirements.txt │               └───────────┬─────────────┘
   └──────────────────┘                           │ notes read/write
                                                  ▼
                                        ┌──────────────────┐
                                        │  Google Sheet    │  (optional but
                                        │  (your notes)    │   recommended)
                                        └──────────────────┘
```

The dashboard is a **reader**. It never fetches from the internet and never calls
an AI — it opens the newest dataset file already committed in `data/`. That is why
it is fast, free to run, and impossible to break by using it.

---

## Before you start

You need:

- a **GitHub account** with this repository (yours or a fork);
- the **dataset committed** — at least one `data/yc_dataset_ai_*.parquet` (or
  `..._base_*.parquet`). If `data/` is empty, build it first: see
  [`HOW_TO_UPDATE.md`](HOW_TO_UPDATE.md) — press the two buttons in **Actions**,
  they commit the dated files for you.

Check now: open the repository on GitHub, click `data/`. You should see files like
`yc_dataset_ai_2026-07-25.parquet`. If yes, continue.

---

## Step 1 — Publish the app (5 minutes)

1. Go to **<https://share.streamlit.io>** and click **Sign in with GitHub**.
   Authorise it to read your repositories.
2. Click **Create app** → **Deploy a public app from GitHub**.
3. Fill in three fields:
   - **Repository:** `<your-account>/<this-repo>`
   - **Branch:** `main`
   - **Main file path:** `app.py`
4. *(Optional)* click **Advanced settings** and set **Python version 3.11** — the
   version this project is pinned to. It also works on newer versions; 3.11 is what
   the tests run on.
5. Click **Deploy**.

The first build takes 2–5 minutes: it installs every package from
`requirements.txt`. You will see the log scrolling — that is normal. When it
finishes, the dashboard opens at a URL like
`https://<account>-<repo>.streamlit.app`.

**What you should see:** the title *🛰️ YC Scouter*, a line saying
`Source: yc_dataset_ai_<date>.parquet`, filters on the left, four tabs.

> **From now on the app redeploys itself.** Every commit to `main` — including the
> ones the update buttons make — triggers a rebuild. You never touch this screen
> again.

### If something goes wrong here

| What you see | What it means | Fix |
|---|---|---|
| `ModuleNotFoundError` | the branch you deployed is missing code, or `requirements.txt` is not in the repository root | check the branch in **Settings → General**; `requirements.txt` must be at the top level |
| "No dataset found" | no dataset file is committed | run the two buttons (see `HOW_TO_UPDATE.md`), then reload |
| The build log stops at installing packages | a version conflict | re-lock the dependencies (`HOW_TO_UPDATE.md` → *Dependencies drift*) |
| The app is blank / says it is sleeping | free-tier apps sleep after ~12 h idle | click once and wait ~15 s — this is normal, not a fault |

---

## Step 2 — Understand where notes live (read this before sharing)

The dashboard lets you mark favourites, set a funnel stage, add tags and write
notes. Where those go depends on how you set it up:

| Setup | Where notes are stored | Survives a restart? |
|---|---|---|
| Nothing configured (local / Colab) | `data/user_data.csv` on disk | Yes locally, **no** on the hosted app |
| **Hosted + Google Sheet configured** | your Google Sheet | **Yes** — this is the one you want |
| A visitor on your public link | their browser session only | No — and that is deliberate |

**Why the hosted app cannot use a file.** Streamlit Community Cloud runs your app
in a container whose disk is rebuilt from the repository on every restart (sleep →
wake, every push, maintenance). Anything the app writes locally is erased. So on
the hosted app, notes must live **outside** the container — that is what the Google
Sheet is for.

Without a Sheet the dashboard still works perfectly; it just shows a banner saying
edits will not persist.

---

## Step 3 — Make notes permanent with a Google Sheet (15 minutes)

Free, no credit card. You create a robot account ("service account"), give it
Editor rights on one spreadsheet, and hand its key to the app.

### 3a. Create the service account and its key

1. Open **<https://console.cloud.google.com>** and create a project (any name).
2. **APIs & Services → Library** → find and **Enable** both:
   - *Google Sheets API*
   - *Google Drive API*
3. **APIs & Services → Credentials → Create credentials → Service account**.
   Name it (e.g. `yc-scouter`), create it, skip the optional steps.
4. Open the new service account → **Keys → Add key → Create new key → JSON**.
   A `.json` file downloads. **This file is a password — never commit it.**

### 3b. Create the sheet and share it

1. Create a new Google Sheet (any name, e.g. *YC Scouter notes*).
2. Open the downloaded JSON and copy the value of **`client_email`** — it looks
   like `yc-scouter@your-project.iam.gserviceaccount.com`.
3. In the Sheet click **Share**, paste that address, give it **Editor**, send.
4. Copy the Sheet's URL from the address bar.

> This is the step people miss: the robot cannot see a sheet nobody shared with it.
> If you skip it, the app will say the sheet is unavailable.

### 3c. Give the app the credentials

1. On <https://share.streamlit.io>, open your app → **⋮ → Settings → Secrets**.
2. Paste the template from `.streamlit/secrets.toml.example` and fill it in from
   the JSON file and the sheet URL:

```toml
[gcp_service_account]
type = "service_account"
project_id = "your-project"
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "yc-scouter@your-project.iam.gserviceaccount.com"
client_id = "..."
token_uri = "https://oauth2.googleapis.com/token"

[gsheets]
spreadsheet = "https://docs.google.com/spreadsheets/d/<ID>/edit"
worksheet = "annotations"

[app]
owner_key = "some-long-random-passphrase"      # see Step 4 — required here
```

3. **Save.** The app restarts by itself.

**Copy `private_key` exactly, including the `\n` sequences** — mangling them is the
number-one setup mistake, and it shows up as `invalid_grant` later.

**What you should see:** a green banner — *“Full access. Your notes go to permanent
storage (a Google Sheet).”* The worksheet is created automatically
on the first save; you can open the Sheet any time and read your notes as a normal
table (one row per company, keyed by the company's immutable `id`).

### If the sheet does not connect

| Message in the app | Cause | Fix |
|---|---|---|
| `invalid_grant` / *account not found* | the key is mangled or the service account was deleted | create a **new** JSON key, re-paste all fields, keep the `\n` |
| *The Google Sheet is unavailable* | the sheet was not shared with `client_email`, or the APIs are not enabled | redo 3b; check both APIs are Enabled |
| Notes save but you cannot see them in the Sheet | you are looking at the wrong worksheet tab | the tab name is the `worksheet` value (default `annotations`) |

The app is deliberately careful here: while the sheet cannot be **read**, saving is
**blocked** rather than allowed — otherwise an empty in-memory table would be
written over your notes and erase them.

---

## Step 4 — Share the link safely

Your dashboard is public. Anyone with the URL can explore everything — and that is
fine, the data is public. What must be protected is **your** notes.

Set an owner key in **Secrets** (same screen as Step 3c):

```toml
[app]
owner_key = "some-long-random-passphrase"
```

Then:

- **You:** open the sidebar → **🔒 Access key** → paste the passphrase once per
  browser session. Saving now writes to your Google Sheet.
- **Visitors:** get full read access — filters, charts, comparison, export — and
  their own **working** notes that live only in their browser tab. Nothing they do
  is visible to you, and nothing of yours is visible to them.

**With a Google Sheet configured, this key is mandatory.** If it is missing or
blank, the app makes *everyone* — including you — a visitor, so nobody can write to
the sheet, and the sidebar says so in red. An empty password must never silently
hand strangers your data. (Running locally with no sheet? Then no key is needed —
that is single-user mode.)

To publish the link: **Settings → Sharing → "This app is public"**, then send the
URL.

---

## Environment variables (optional)

Useful when running locally or testing:

| Variable | Effect |
|---|---|
| `YC_SCOUTER_DATASET` | use a specific parquet instead of the newest dated one |
| `YC_SCOUTER_USERDATA` | path of the local CSV used when no Sheet is configured |
| `ANTHROPIC_API_KEY` / `GROQ_API_KEY` | only needed to *build* AI summaries, never by the dashboard |

Run the dashboard on your own machine with:

```bash
pip install -r requirements.txt --require-hashes
streamlit run app.py
```

---

## Deploying somewhere else

Nothing in the dashboard is tied to Streamlit Cloud — it is a normal Streamlit app
reading a Parquet file. Any host that can run
`streamlit run app.py --server.port $PORT` works (Hugging Face Spaces, Render,
Fly.io, a VPS). Two things to carry over: install from `requirements.txt`, and
provide the same secrets (as a `.streamlit/secrets.toml` file or environment
configuration).

If you later want a full website instead of a dashboard, the dataset is already a
clean data contract: `parquet`/JSON with `score`, `investability` and the `ai_*`
fields pre-computed, so a static front-end can be built on top without touching the
pipeline.
