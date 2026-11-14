# BrandGuard AI
### AI-Powered Brand Governance and Content Review Platform

**Project:** BrandGuard AI  
**Hackathon:** CodeTitans India 2026  
**Team Name:** CodewithSweta  
**Technology Stack:** Python, Flask, SQLite, Gemini AI, HTML, CSS, JavaScript

## 1. Project Overview

BrandGuard AI is an intelligent brand-governance platform designed to review digital content before publication.

It helps organizations maintain consistent brand communication by checking submitted content against approved brand guidelines, verified information, and brand requirements.

## 2. Key Features

- **Brand Guidelines Management:** Configure brand tone, approved keywords, restricted words, brand rules, disclaimers, and approved colours.
- **AI-Powered Content Analysis:** Uses Gemini AI to evaluate submitted content against configured brand requirements.
- **Rule-Based Validation:** Detects restricted words, missing approved keywords, risky claims, excessive capitalization, and other content issues.
- **Actionable Recommendations:** Provides explanations and suggestions to improve content quality.
- **Analysis Fallback:** Provides rule-based results when Gemini AI is unavailable.
- **Content Review Workflow:** Supports reviewing submitted content before publication.

## 3. Technology Stack

| Technology | Purpose |
|---|---|
| Python | Backend development |
| Flask | Web framework |
| SQLite | Database |
| Gemini AI | AI-powered content analysis |
| HTML | Page structure |
| CSS | User interface styling |
| JavaScript | Frontend functionality |

## 4. Project Setup

### Prerequisites
- Python 3
- Visual Studio Code
- Gemini API Key

### Installation

1. Clone the project repository or open the existing project folder.
2. Open the project in Visual Studio Code.
3. Create a virtual environment:

   `py -m venv .venv`

4. Activate the environment:

   `.venv\Scripts\activate`

5. Install dependencies:

   `py -m pip install -r requirements.txt`

6. Configure the required environment variables using a local `.env` file.

7. Start the application:

   `py app.py`

8. Open the application in your browser:

   `http://127.0.0.1:5000`

## 5. Environment Configuration

Configure the following environment variables:

- `GEMINI_API_KEY` – Gemini API authentication key.
- `GEMINI_MODEL` – Optional Gemini model selection.

Keep API credentials private. Never commit `.env` files or secret keys to GitHub.

## 6. Demo Test Case

**Brand Guidelines**

- Brand Tone: Professional and trustworthy
- Approved Keywords: reliable, transparent, customer-first
- Restricted Words: guaranteed, fake, unlimited

**Sample Content**

"GUARANTEED! Our product is 100% risk-free and unlimited. Buy now!!!"

**Expected Analysis**

The system should identify restricted words, potentially misleading claims, excessive capitalization, and missing approved keywords, and provide corrective suggestions.

## 7. Project Objective

BrandGuard AI aims to reduce brand-related communication risks, improve content consistency, and help organizations publish accurate, trustworthy, and brand-aligned digital content.

**Developed for CodeTitans India 2026 – Round 3.**
