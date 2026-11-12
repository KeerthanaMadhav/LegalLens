"""
test_pipeline.py - runs the whole AI side without Flask:
    PDF -> text -> extract_clauses -> evaluate_rules -> findings

Usage:  python test_pipeline.py                      (runs both sample PDFs)
        python test_pipeline.py some_agreement.pdf   (runs your own file)
"""
import sys

import pymupdf

from ai_engine import evaluate_rules
from clause_extractor import extract_clauses, clean_text, extract_notice_period, extract_duration


def analyze_pdf(path):
    doc = pymupdf.open(path)
    raw = "".join(page.get_text() for page in doc)
    if not raw.strip():
        return None, None
    kb = extract_clauses(raw)
    return kb, evaluate_rules(kb)


def show(path):
    print("=" * 70)
    print(path)
    kb, findings = analyze_pdf(path)
    if kb is None:
        print("No readable text found in this PDF (scanned/image-only).")
        return
    for key, value in kb.items():
        print(f"  {key:18} {value if value is not None else 'Not detected'}")
    print(f"  -> {len(findings)} finding(s)")
    for f in findings:
        print(f"     [{f['rule_id']}] {f['message']}")


def wording_checks():
    """Small checks that different phrasings are understood."""
    print("=" * 70)
    print("Wording variations")
    for t in ["either party may end this by giving 30 days notice",
              "with a notice period of 2 months",
              "a written notice of three months shall be given",
              "the tenant may leave anytime"]:
        print(f"  notice: {extract_notice_period(clean_text(t))!s:12} <- {t}")
    for t in ["for a period of 12 months from today",
              "shall commence from 1st Jan 2027 and shall be valid till 31st Dec 2027, thereafter"]:
        print(f"  duration: {extract_duration(clean_text(t))!s}")


if __name__ == "__main__":
    paths = sys.argv[1:] or ["sample_documents/sample_rental_agreement.pdf",
                             "sample_documents/sample_rental_agreement_incomplete.pdf"]
    for p in paths:
        show(p)
    wording_checks()
