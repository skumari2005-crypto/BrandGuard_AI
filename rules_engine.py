"""Deterministic brand-governance checks used alongside Gemini AI."""
import re

DEFAULT_RESTRICTED = ["guaranteed", "100% guaranteed", "fake", "unlimited"]
HIGH_RISK_PATTERNS = [
    (r"(?<!\w)(100\s*%|always|never|guaranteed|risk[- ]free|number one|#1)(?!\w)", "High", "Absolute or high-risk claim"),
    (r"\b(cure|cures|cured|miracle|clinically proven|zero side effects)\b", "High", "Potentially regulated or medical claim"),
    (r"\b(best in the world|world's best|market leader)\b", "Medium", "Comparative claim requiring evidence"),
]


def split_items(value):
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return [x.strip() for x in re.split(r"[,\n;]+", str(value or "")) if x.strip()]


def analyze_brand_content(content, guidelines=None):
    guidelines = guidelines or {}
    issues, suggestions = [], []
    text = str(content or "").strip()
    if not text:
        return ([{"issue": "Empty content", "description": "Content is empty.", "severity": "High", "category": "Completeness"}], ["Add content before submitting it for review."])

    def add(issue, description, severity="Medium", category="Brand compliance", suggestion=None):
        issues.append({"issue": issue, "description": description, "severity": severity, "category": category, "source": "Rules Engine"})
        if suggestion:
            suggestions.append(suggestion)

    restricted = list(dict.fromkeys(DEFAULT_RESTRICTED + split_items(guidelines.get("restrictedWords"))))
    lower = text.casefold()
    for phrase in restricted:
        if phrase and re.search(r"(?<!\w)" + re.escape(phrase.casefold()) + r"(?!\w)", lower):
            add("Restricted term", f"Restricted word or phrase detected: ‘{phrase}’.", "High", "Restricted language", f"Remove ‘{phrase}’ or replace it with a verified, brand-approved statement.")

    approved = split_items(guidelines.get("approvedKeywords"))
    if approved:
        matched = [term for term in approved if re.search(r"(?<!\w)" + re.escape(term.casefold()) + r"(?!\w)", lower)]
        if not matched:
            add("Approved keyword missing", "None of the configured approved keywords appear in this content.", "Low", "Brand messaging", "Where relevant, include an approved brand keyword: " + ", ".join(approved[:5]) + ".")

    tone = str(guidelines.get("brandTone", "")).strip()
    tone_signals = {
        "professional": (r"\b(OMG|WTF|lol|!!!+)\b", "Avoid slang and excessive punctuation for a professional tone."),
        "friendly": (r"\b(aforementioned|hereby|pursuant)\b", "Consider warmer, more conversational wording for a friendly tone."),
        "formal": (r"\b(hey|gonna|wanna|lol)\b", "Replace casual wording with formal language."),
    }
    for key, (pattern, advice) in tone_signals.items():
        if key in tone.casefold() and re.search(pattern, text, re.I):
            add("Possible tone mismatch", f"Some wording may conflict with the requested {tone} tone.", "Low", "Tone", advice)
            break

    for pattern, severity, label in HIGH_RISK_PATTERNS:
        if re.search(pattern, text, re.I):
            add(label, "A strong, absolute or regulated claim may require substantiation before publication.", severity, "Claims and accuracy", "Attach reliable evidence, qualify the statement, or remove the claim if it cannot be substantiated.")

    for term in split_items(guidelines.get("requiredDisclaimer")):
        if term.casefold() not in lower:
            add("Required disclaimer missing", f"The configured disclaimer or phrase ‘{term}’ was not found.", "High", "Required disclosures", f"Add the approved disclaimer: {term}")

    if re.search(r"[A-Z]{5,}", text):
        add("Excessive capitalization", "A word written in all capitals may look overly promotional or off-brand.", "Low", "Tone and formatting", "Use normal sentence case unless the capitalized text is an approved acronym.")
    if re.search(r"!{2,}|\?{2,}", text):
        add("Excessive punctuation", "Repeated punctuation may reduce clarity or conflict with a professional brand voice.", "Low", "Tone and formatting", "Use standard punctuation and a calm, clear sentence structure.")
    if len(text.split()) < 5:
        add("Insufficient context", "The content is very short, so a complete brand review may not be possible.", "Low", "Completeness", "Provide more context, intended audience, and supporting details.")

    rules = str(guidelines.get("brandRules", "")).strip()
    if rules:
        suggestions.append("Confirm that the content follows every additional free-text brand rule; Gemini provides a semantic review, but a human reviewer makes the final decision.")

    # De-duplicate repeated findings while retaining the most useful first occurrence.
    seen, unique_issues = set(), []
    for item in issues:
        key = (item["issue"], item["description"])
        if key not in seen:
            seen.add(key); unique_issues.append(item)
    return unique_issues, list(dict.fromkeys(suggestions))
