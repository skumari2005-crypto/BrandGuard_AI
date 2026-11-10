import re

DEFAULT_RESTRICTED = ["guaranteed", "100% guaranteed", "fake", "unlimited"]


def _split_items(value):
    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]
    return [x.strip() for x in re.split(r"[,\n;]+", str(value or "")) if x.strip()]


def analyze_brand_content(content, guidelines=None):
    """Deterministic fallback checks. These are rule-based, not generative AI."""
    guidelines = guidelines or {}
    issues, suggestions = [], []
    text = str(content or "").strip()
    if not text:
        return ([{"issue": "Empty content", "description": "Content is empty."}],
                ["Add content before submitting it for review."])

    restricted = list(dict.fromkeys(DEFAULT_RESTRICTED + _split_items(guidelines.get("restrictedWords"))))
    lower = text.lower()
    for word in restricted:
        if word and re.search(r"(?<!\w)" + re.escape(word.lower()) + r"(?!\w)", lower):
            issues.append({"issue": "Restricted term", "description": f"Restricted word or phrase detected: ‘{word}’."})
            suggestions.append(f"Remove ‘{word}’ or replace it with a verified, brand-approved statement.")

    approved = _split_items(guidelines.get("approvedKeywords"))
    if approved and not any(term.lower() in lower for term in approved):
        issues.append({"issue": "Approved keyword missing", "description": "None of the configured approved keywords appear in this content."})
        suggestions.append("Where relevant, include an approved brand keyword: " + ", ".join(approved[:5]) + ".")

    tone = str(guidelines.get("brandTone", "")).strip()
    if tone and re.search(r"\b(!!!+|WTF|OMG)\b", text, re.I):
        issues.append({"issue": "Tone mismatch", "description": f"The wording may not match the requested {tone} brand tone."})
        suggestions.append(f"Rewrite the expressive wording in a {tone.lower()} tone.")

    if re.search(r"\b(100%|always|never|guaranteed|cure|risk[- ]free|number one|#1)\b", text, re.I):
        issues.append({"issue": "Absolute or high-risk claim", "description": "An absolute or potentially misleading claim needs evidence before publication."})
        suggestions.append("Add verifiable evidence and qualify the claim, or remove the absolute wording.")

    if re.search(r"[A-Z]{5,}", text):
        issues.append({"issue": "Excessive capitalization", "description": "A word written in all capitals may look overly promotional or off-brand."})
        suggestions.append("Use normal sentence case unless the capitalized text is an approved acronym.")

    if len(text.split()) < 5:
        issues.append({"issue": "Insufficient context", "description": "The content is very short, so a complete brand review may not be possible."})
        suggestions.append("Provide more context, intended audience, and supporting details.")

    rules = str(guidelines.get("brandRules", "")).strip()
    if rules:
        # Surface configured rules for the AI prompt; do not pretend to semantically enforce arbitrary prose.
        if any(term.lower() in lower for term in _split_items(rules)):
            issues.append({"issue": "Custom brand rule review", "description": "Content overlaps with wording listed in the additional brand rules; verify it against the full rule."})
            suggestions.append("Review this wording against your additional brand rules and revise if it conflicts.")

    return issues, suggestions
