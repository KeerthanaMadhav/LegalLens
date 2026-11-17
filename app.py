
from flask import Flask, render_template, request, jsonify
import fitz
import re

app = Flask(__name__)

# Maximum PDF upload size: 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


# --------------------------------------------------
# 1. HELPER FUNCTION: CLEAN EXTRACTED TEXT
# --------------------------------------------------

def clean_text(value):
    if not value:
        return None

    value = re.sub(r"\s+", " ", value)
    value = value.strip(" \t\n\r,;:")

    return value if value else None


# --------------------------------------------------
# 2. FIELD EXTRACTION FUNCTION
# --------------------------------------------------

def extract_agreement_fields(text):

    agreement = {
        "landlord": None,
        "tenant": None,
        "property_address": None,
        "rent": None,
        "security_deposit": None,
        "duration": None,
        "notice_period": None
    }

    patterns = {
        "landlord": (
            r"by and between:\s*(.*?)\s*,\s*"
            r"(?:S/o|D/o|W/o|C/o)\b"
        ),

        "tenant": (
            r"AND,\s*in favour of:\s*(.*?)\s*,\s*"
            r"(?:S/o|D/o|W/o|C/o)\b"
        ),

        "property_address": (
            r"property situated at\s*(.*?)\s*"
            r"as detailed in Annexure"
        ),

        "rent": (
            r"monthly rent of\s*(Rs\.?\s*[\d,]+\s*/?-?)"
        ),

        "security_deposit": (
            r"security deposit of\s*(Rs\.?\s*[\d,]+\s*/?-?)"
        ),

        "duration": (
            r"shall commence from\s*(.*?)\s+"
            r"and shall be valid till\s*(.*?)(?:\.|,|\n)"
        ),

        "notice_period": (
            r"serving\s+(.*?)\s+prior notice"
        )
    }

    for field, pattern in patterns.items():

        match = re.search(
            pattern,
            text,
            re.IGNORECASE | re.DOTALL
        )

        if match:

            if field == "duration":
                start_date = clean_text(match.group(1))
                end_date = clean_text(match.group(2))

                if start_date and end_date:
                    agreement[field] = (
                        f"{start_date} to {end_date}"
                    )

            else:
                agreement[field] = clean_text(match.group(1))

    return agreement


# --------------------------------------------------
# 3. RULE-BASED COMPLETENESS CHECKER
# --------------------------------------------------

def evaluate_rules(agreement):

    findings = []

    rules = {
        "landlord": {
            "rule_id": "R001",
            "message": "Landlord information is missing.",
            "explanation": (
                "The agreement does not clearly identify "
                "the landlord or property owner."
            )
        },

        "tenant": {
            "rule_id": "R002",
            "message": "Tenant information is missing.",
            "explanation": (
                "The agreement does not clearly identify "
                "the tenant."
            )
        },

        "property_address": {
            "rule_id": "R003",
            "message": "Property address is missing.",
            "explanation": (
                "The rental property's address could not "
                "be identified."
            )
        },

        "rent": {
            "rule_id": "R004",
            "message": "Monthly rent is missing.",
            "explanation": (
                "The agreement does not specify the "
                "monthly rental amount."
            )
        },

        "security_deposit": {
            "rule_id": "R005",
            "message": "Security deposit is missing.",
            "explanation": (
                "The agreement does not specify the "
                "security deposit amount."
            )
        },

        "duration": {
            "rule_id": "R006",
            "message": "Agreement duration is missing.",
            "explanation": (
                "The rental commencement date or "
                "expiry date could not be identified."
            )
        },

        "notice_period": {
            "rule_id": "R007",
            "message": "Notice period is missing.",
            "explanation": (
                "The agreement does not specify the "
                "required notice period."
            )
        }
    }

    # Evaluate each predefined completeness rule
    for field, rule in rules.items():

        if not agreement.get(field):

            findings.append({
                "rule_id": rule["rule_id"],
                "message": rule["message"],
                "explanation": rule["explanation"]
            })

    return findings


# --------------------------------------------------
# 4. HOMEPAGE ROUTE
# --------------------------------------------------

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


# --------------------------------------------------
# 5. PDF ANALYSIS ROUTE
# --------------------------------------------------

@app.route("/analyze", methods=["POST"])
def analyze():

    if "file" not in request.files:
        return jsonify({
            "success": False,
            "error": "No file was uploaded."
        }), 400

    pdf_file = request.files["file"]

    if not pdf_file.filename:
        return jsonify({
            "success": False,
            "error": "No file was selected."
        }), 400

    try:

        # Read uploaded PDF
        pdf_bytes = pdf_file.read()

        if not pdf_bytes:
            return jsonify({
                "success": False,
                "error": "The uploaded file is empty."
            }), 400

        # Validate PDF signature
        if not pdf_bytes.startswith(b"%PDF-"):
            return jsonify({
                "success": False,
                "error": "The uploaded file is not a valid PDF."
            }), 400

        # Extract text using PyMuPDF
        try:

            with fitz.open(
                stream=pdf_bytes,
                filetype="pdf"
            ) as document:

                extracted_text = "\n".join(
                    page.get_text("text")
                    for page in document
                ).strip()

        except Exception:
            return jsonify({
                "success": False,
                "error": "The PDF is corrupted or cannot be read."
            }), 400

        # Reject scanned or image-only PDFs
        if not extracted_text:
            return jsonify({
                "success": False,
                "error": (
                    "No selectable text was found. "
                    "The PDF may be scanned or image-based."
                )
            }), 400

        # Extract agreement attributes
        agreement = extract_agreement_fields(extracted_text)

        # Apply predefined completeness rules
        findings = evaluate_rules(agreement)

        # Return results to frontend
        return jsonify({
            "success": True,
            "agreement": agreement,
            "findings": findings,
            "extracted_text": extracted_text
        }), 200

    except Exception:

        app.logger.exception(
            "Unexpected error during PDF analysis"
        )

        return jsonify({
            "success": False,
            "error": (
                "An unexpected error occurred "
                "while processing the PDF."
            )
        }), 500


# --------------------------------------------------
# 6. FILE SIZE ERROR HANDLER
# --------------------------------------------------

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({
        "success": False,
        "error": "The uploaded file exceeds the 10 MB limit."
    }), 413


# --------------------------------------------------
# 7. RUN FLASK APPLICATION
# --------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
