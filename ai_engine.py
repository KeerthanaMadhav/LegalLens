"""
ai_engine.py - LegalLens knowledge base and reasoning engine.

Step 1: Knowledge representation + predicates.
Step 2: Rules + the reasoning loop (this version).
"""

# ---------------------------------------------------------------
# 1. KNOWLEDGE REPRESENTATION
# The exact keys the frontend (script.js) expects in "agreement".
# ---------------------------------------------------------------
FIELDS = [
    "landlord",
    "tenant",
    "property_address",
    "rent",
    "security_deposit",
    "duration",
    "notice_period",
]


def create_knowledge_base():
    """Return a fresh knowledge base: every field exists, none is known yet."""
    return {field: None for field in FIELDS}


# ---------------------------------------------------------------
# 2. PREDICATES
# A predicate is a condition about ONE fact that is either True or False.
# In predicate logic:  Missing(x)  is true when fact x is not established.
# ---------------------------------------------------------------
def is_missing(kb, field):
    """Missing(field): True if the field is None or only whitespace."""
    value = kb.get(field)
    if value is None:
        return True
    return str(value).strip() == ""


def is_present(kb, field):
    """Present(field): the opposite of Missing(field)."""
    return not is_missing(kb, field)


# ---------------------------------------------------------------
# 3. RULES
# Each rule is:  IF condition(kb) THEN raise a finding.
# Logic form:    Missing(x) -> Flag(x)
# The condition is a small function (lambda) that takes the knowledge base
# and returns True/False by calling a predicate.
# ---------------------------------------------------------------
RULES = [
    {
        "id": "R1",
        "field": "landlord",
        "condition": lambda kb: is_missing(kb, "landlord"),
        "message": "Landlord (owner) name is missing.",
        "explanation": "The agreement must identify who is renting out the property. "
                       "No landlord or owner name was detected.",
    },
    {
        "id": "R2",
        "field": "tenant",
        "condition": lambda kb: is_missing(kb, "tenant"),
        "message": "Tenant name is missing.",
        "explanation": "The agreement must identify who is renting the property. "
                       "No tenant name was detected (a blank template placeholder also counts as missing).",
    },
    {
        "id": "R3",
        "field": "property_address",
        "condition": lambda kb: is_missing(kb, "property_address"),
        "message": "Rental property address is missing.",
        "explanation": "Without the property address it is unclear which property the agreement covers.",
    },
    {
        "id": "R4",
        "field": "rent",
        "condition": lambda kb: is_missing(kb, "rent"),
        "message": "Monthly rent amount is missing.",
        "explanation": "The rent is the core financial term. No monthly rent amount was detected.",
    },
    {
        "id": "R5",
        "field": "security_deposit",
        "condition": lambda kb: is_missing(kb, "security_deposit"),
        "message": "Security deposit amount is missing.",
        "explanation": "No security deposit amount was detected. Deposit terms are a common source of disputes, "
                       "so they should be stated clearly.",
    },
    {
        "id": "R6",
        "field": "duration",
        "condition": lambda kb: is_missing(kb, "duration"),
        "message": "Agreement duration is missing.",
        "explanation": "No agreement period or end date was detected, so it is unclear how long the tenancy lasts.",
    },
    {
        "id": "R7",
        "field": "notice_period",
        "condition": lambda kb: is_missing(kb, "notice_period"),
        "message": "Notice period is missing.",
        "explanation": "No notice period for ending the agreement was detected. "
                       "Without it, neither party knows how much warning to give before leaving or asking to leave.",
    },
]


# ---------------------------------------------------------------
# 4. THE REASONING ENGINE (inference loop)
# Take the facts, test every rule, collect the findings of the rules that fire.
# ---------------------------------------------------------------
def evaluate_rules(kb):
    """Run all rules against the knowledge base. Returns a list of findings."""
    findings = []
    for rule in RULES:
        if rule["condition"](kb):          # does the rule's IF part hold?
            findings.append({
                "rule_id": rule["id"],
                "field": rule["field"],
                "message": rule["message"],
                "explanation": rule["explanation"],
            })
    return findings


# ---------------------------------------------------------------
# Quick self-test: run `python ai_engine.py`
# ---------------------------------------------------------------
if __name__ == "__main__":
    # Test 1: a complete agreement -> no rule should fire
    complete = {
        "landlord": "Ramesh Kumar Verma", "tenant": "Priya Sharma",
        "property_address": "Flat No. 302, Sunrise Apartments, Vikas Nagar, Lucknow",
        "rent": "15000", "security_deposit": "30000",
        "duration": "11 months", "notice_period": "2 months",
    }
    print("COMPLETE agreement ->", len(evaluate_rules(complete)), "findings")

    # Test 2: matches sample_rental_agreement_incomplete.pdf
    incomplete = dict(complete, tenant=None, security_deposit=None, notice_period=None)
    results = evaluate_rules(incomplete)
    print("INCOMPLETE agreement ->", len(results), "findings")
    for f in results:
        print(f"  [{f['rule_id']}] {f['message']}")
        print(f"       why: {f['explanation']}")

    # Test 3: empty knowledge base -> all 7 rules should fire
    print("EMPTY knowledge base ->", len(evaluate_rules(create_knowledge_base())), "findings")
