BRANDGUARD AI - PATCHED VERSION

WHAT WAS FIXED
1. Brand Guidelines stored in browser localStorage are now sent with every analysis request.
2. The backend passes those guidelines to both the deterministic rules engine and Gemini prompt.
3. Rules engine now checks configured restricted words, approved keywords, tone-related signals,
   absolute/high-risk claims, excessive capitalization, and very short content.
4. Rule-based results are returned even if Gemini is unavailable. The interface labels this honestly
   as a rules-based fallback, not successful AI analysis.
5. Gemini model selection can be configured with GEMINI_MODEL; default is gemini-3.8-flash.

SETUP (WINDOWS / VS CODE)
1. Extract this ZIP.
2. Open the extracted BrandGuard_AI folder in VS Code.
3. Open Terminal > New Terminal.
4. Create/activate a virtual environment if needed:
   py -m venv .venv
   .venv\\Scripts\\activate
5. Install packages:
   py -m pip install -r requirements.txt
6. Copy .env.example to a new file named .env.
7. Add a NEW Gemini API key to .env (do not share or commit this file).
8. Run:
   py app.py
9. Open http://127.0.0.1:5000

IMPORTANT SECURITY
The ZIP uploaded for debugging contained a .env file. Treat that API key as exposed:
revoke/delete that key in Google AI Studio and create a new one. Do not upload the new .env.
The patched ZIP intentionally excludes .env, .venv, and the local database.

DEMO TEST
Save these guidelines:
Brand Tone: Professional and trustworthy
Approved Keywords: reliable, transparent, customer-first
Restricted Words: guaranteed, fake, unlimited

Then analyze:
"GUARANTEED! Our product is 100% risk-free and unlimited. Buy now!!!"
Expected: rule-based flags for restricted terms, high-risk claims, capitalization and missing
approved keywords, plus corrective suggestions. Gemini results will be added when API access works.
