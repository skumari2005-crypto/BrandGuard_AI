# BrandGuard AI — CodeTitan Final Round Build

A Flask + SQLite brand-governance demo that combines deterministic rules, Gemini AI review, visual checks, compliance scoring, and human approval.

## Features

1. **Advanced Brand Rule Validation** — restricted terms, required disclaimers, approved keywords, high-risk claims, tone signals, excessive capitalization/punctuation, and actionable suggestions. Gemini reviews the full custom brand rules semantically when its API is configured.
2. **Visual Brand Analysis** — upload a creative image; extract dominant colours; compare them approximately with configured HEX brand colours; optionally compare a submitted image with an approved logo reference; send the creative image to Gemini for a visual review.
3. **Detailed Compliance Reports** — 0–100 score, grade, issue counts and severity, report sections, print/save-as-PDF, and a persisted review activity timeline (created, re-analyzed, approved).
4. **Existing workflow retained** — dashboard, guidelines, content submission, AI analysis, issue detection, correction suggestions, human approval, review history, edit/re-analyze and delete.

## Requirements

- Python 3.10 or newer
- A Gemini API key from Google AI Studio (optional for deterministic rule checks; required for Gemini text/image analysis)

## Run on Windows / VS Code

1. Extract the ZIP.
2. Open the `BrandGuard_AI` folder in VS Code.
3. Open **Terminal → New Terminal**.
4. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .venv\Scripts\activate
   ```

5. Install packages:

   ```powershell
   py -m pip install -r requirements.txt
   ```

6. Copy `.env.example` and name the copy `.env`.
7. Open `.env` and paste your **new** Gemini API key after `GEMINI_API_KEY=`. Never share or commit this file.
8. Start the app:

   ```powershell
   py app.py
   ```

9. Open `http://127.0.0.1:5000` in your browser.

## Configure the brand

Open **Brand Guidelines** and enter the brand name, tone, approved keywords, restricted words, custom rules, optional required disclaimer, and comma-separated HEX colours (example: `#172554, #2563EB, #FFFFFF`). Optionally upload an approved logo reference (under 2 MB). Click **Save Guidelines**.

Open **Content Submission**, enter a title and content, and optionally upload a JPG, PNG, or WebP creative image (under 5 MB). Click **Analyze Content**. Review the score, findings, visual checks, suggestions, and report. A human reviewer can approve a pending review.

## Demo test

Use these sample settings:

- Brand tone: `Professional and trustworthy`
- Approved keywords: `reliable, transparent, customer-first`
- Restricted words: `guaranteed, fake, unlimited`
- Brand colours: `#172554, #2563EB, #FFFFFF`

Test content:

`GUARANTEED! Our product is 100% risk-free and unlimited. Buy now!!!`

Expected deterministic findings include restricted wording, an absolute/high-risk claim, excessive capitalization/punctuation, and missing approved keywords. Gemini findings appear only when the API key, model access, network, and quota are valid.

## Important notes and limitations

- A rules-only result is clearly labelled when Gemini is unavailable; the app does not pretend the AI request succeeded.
- The colour comparison uses approximate RGB distance. Logo comparison is a basic resized-pixel similarity estimate and is **not** proof of authenticity. Image layout, cropping, transparency, backgrounds, and resizing can affect it.
- Compliance score is a transparent heuristic, not a legal or regulatory certification. A human reviewer makes the final decision.
- Brand guidelines and the logo reference are saved in browser local storage. Review records and activity events are stored in SQLite (`brandguard.db`). Keep backups if you need to preserve review data.
- Uploaded images are processed in memory for the review and are not stored as retrievable image files in this build.

## Security

Do not include `.env`, API keys, `.venv`, or personal credentials in shared ZIPs or Git commits. If an API key was previously included in a shared archive, revoke it in Google AI Studio and create a new key.

## Run the deterministic rules tests

```powershell
py -m unittest discover -s tests -v
```

The tests cover restricted wording, high-risk claims, required disclaimers, and empty content. They do not call Gemini or replace the end-to-end browser test.
