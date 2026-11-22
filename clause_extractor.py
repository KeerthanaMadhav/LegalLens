"""
clause_extractor.py - turns raw agreement text into the facts dict.

Pipeline:  raw text -> clean_text -> one extractor per field -> knowledge base.
Rule for every extractor: return the value if found, otherwise None.
We never guess ("Not detected" is better than a wrong answer).

Placeholders from blank templates, like "(Name of the Tenant)", are treated as
NOT found. Most patterns below achieve this by refusing to start with "(".
"""
import re

from ai_engine import create_knowledge_base


# ---------------------------------------------------------------
# 1. PREPROCESSING
# PyMuPDF breaks lines in the middle of sentences, so a phrase like
# "security deposit of Rs." can be split across two lines and a regex
# would miss it. We flatten everything into one clean line of text.
# ---------------------------------------------------------------
def clean_text(text):
    """Join broken lines and collapse repeated spaces. Keeps original casing."""
    if not text:
        return ""
    text = text.replace("\r", " ").replace("\n", " ")   # line breaks -> spaces
    text = re.sub(r"\s+", " ", text)                    # many spaces -> one space
    return text.strip()


# ---------------------------------------------------------------
# Shared pieces
# ---------------------------------------------------------------
CURRENCY = r"(?:Rs\.?|INR|₹)"                 # Rs. / Rs / INR / rupee sign
NUMBER_WORDS = (r"\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
                r"fifteen|thirty|forty[- ]five|sixty|ninety")
TIME_UNITS = r"months?|days?|weeks?|years?"


def _clean_value(value):
    """Trim spaces and trailing punctuation from a captured value."""
    return value.strip(" ,.;:")


def _extract_amount(text, phrase):
    """Find '<phrase> of Rs. 15,000' and return '15000', else None."""
    pattern = rf"{phrase}\s+of\s+{CURRENCY}\s*([\d,]+)"
    match = re.search(pattern, text, re.IGNORECASE)
    if match is None:
        return None
    digits = match.group(1).replace(",", "")
    return digits if digits else None


# ---------------------------------------------------------------
# 2. FIELD EXTRACTORS
# ---------------------------------------------------------------
def extract_landlord(text):
    """Name right after 'by and between:' (the owner is listed first)."""
    # [^,(]+?  = any characters except a comma or "(" -> rejects "(Name of the Owner)"
    match = re.search(r"by\s+and\s+between\s*:?\s*([^,(]+?)\s*,", text, re.IGNORECASE)
    return _clean_value(match.group(1)) if match else None


def extract_tenant(text):
    """Name right after 'in favour of:'."""
    match = re.search(r"in\s+favou?r\s+of\s*:?\s*([^,(]+?)\s*,", text, re.IGNORECASE)
    return _clean_value(match.group(1)) if match else None


def extract_property_address(text):
    """Text after 'property situated at' up to 'as detailed' / 'hereinafter'."""
    match = re.search(
        r"property\s+situated\s+at\s+([^(].+?)\s+(?:as\s+detailed|hereinafter)",
        text, re.IGNORECASE)
    return _clean_value(match.group(1)) if match else None


def extract_rent(text):
    """'monthly rent of Rs. 15,000' -> '15000'."""
    return _extract_amount(text, r"monthly\s+rent")


def extract_security_deposit(text):
    """'security deposit of Rs. 30,000' -> '30000'."""
    return _extract_amount(text, r"security\s+deposit")


def extract_duration(text):
    """Return e.g. '11 months (1st December 2026 to 31st October 2027)'.

    Looks for a stated period ('a period of 11 months') and for start/end dates
    ('commence from X and shall be valid till Y'). Uses whatever it finds.
    """
    period = None
    match = re.search(rf"a\s+period\s+of\s+(\d+)\s+({TIME_UNITS})", text, re.IGNORECASE)
    if match:
        period = f"{match.group(1)} {match.group(2).lower()}"

    dates = None
    match = re.search(
        r"commence\s+from\s+([^(]+?)\s+and\s+shall\s+be\s+valid\s+till\s+([^(]+?)(?:,|\.\s)",
        text, re.IGNORECASE)
    if match:
        dates = f"{_clean_value(match.group(1))} to {_clean_value(match.group(2))}"

    if period and dates:
        return f"{period} ({dates})"
    return period or dates


def extract_notice_period(text):
    """Find wording like 'two months' prior written notice' or 'notice of 30 days'."""
    # Pattern A: "<number> <unit> [prior/written/advance] notice"
    match = re.search(
        rf"({NUMBER_WORDS})\s+({TIME_UNITS})['’]?\s+(?:(?:prior|advance|written)\s+)*notice",
        text, re.IGNORECASE)
    # Pattern B: "notice [period] of [at least] <number> <unit>"
    if match is None:
        match = re.search(
            rf"notice\s+(?:period\s+)?of\s+(?:at\s+least\s+)?({NUMBER_WORDS})\s+({TIME_UNITS})",
            text, re.IGNORECASE)
    if match is None:
        return None
    return f"{match.group(1).lower()} {match.group(2).lower()}"


# ---------------------------------------------------------------
# 3. MAIN FUNCTION
# ---------------------------------------------------------------
def extract_clauses(text):
    """Return the knowledge base (7 keys) filled with whatever was found."""
    text = clean_text(text)
    kb = create_knowledge_base()
    kb["landlord"] = extract_landlord(text)
    kb["tenant"] = extract_tenant(text)
    kb["property_address"] = extract_property_address(text)
    kb["rent"] = extract_rent(text)
    kb["security_deposit"] = extract_security_deposit(text)
    kb["duration"] = extract_duration(text)
    kb["notice_period"] = extract_notice_period(text)
    return kb


# ---------------------------------------------------------------
# 4. ONE-CALL ENTRY POINT FOR app.py
# Returns exactly the pieces the frontend expects: "agreement" and "findings".
# ---------------------------------------------------------------
def analyze_text(text):
    """text -> {"agreement": {...7 fields...}, "findings": [...]}"""
    from ai_engine import evaluate_rules   # imported here to keep the top tidy
    kb = extract_clauses(text)
    return {"agreement": kb, "findings": evaluate_rules(kb)}
