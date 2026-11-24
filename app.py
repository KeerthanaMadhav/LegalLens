
from flask import Flask, render_template, request, jsonify
import fitz
from clause_extractor import analyze_text

app = Flask(__name__)

# Maximum PDF upload size: 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024


# 1. Homepage
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")


# 2. PDF Analysis
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

        except Exception as e:
            print(f"PDF extraction error: {e}")
            return jsonify({
                "success": False,
                "error": "Could not read the PDF file."
            }), 400

        if not extracted_text:
            return jsonify({
                "success": False,
                "error": "No readable text was found in the PDF."
            }), 400

        # Analyze extracted agreement text
        results = analyze_text(extracted_text)

        return jsonify({
   		"success": True,
	   	"agreement": results["agreement"],
    		"findings": results["findings"],
    		"extracted_text": extracted_text
}), 200

    except Exception as e:
        print(f"Analysis error: {e}")
        return jsonify({
            "success": False,
            "error": "An unexpected error occurred during analysis."
        }), 500


# 3. Handle oversized uploads
@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "success": False,
        "error": "File too large. Maximum allowed size is 10 MB."
    }), 413


# 4. Start Flask server
if __name__ == "__main__":
    app.run(debug=True)
