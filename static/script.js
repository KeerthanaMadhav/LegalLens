// LegalLens frontend script.
// Sends the chosen PDF to POST /analyze and shows the real server response.

// ---------- Page elements ----------
const fileInput = document.getElementById("file-input");
const chooseButton = document.getElementById("choose-button");
const dropArea = document.getElementById("drop-area");
const fileInfo = document.getElementById("file-info");
const fileNameText = document.getElementById("file-name");
const fileSizeText = document.getElementById("file-size");
const errorMessage = document.getElementById("error-message");
const analyzeButton = document.getElementById("analyze-button");
const loadingSection = document.getElementById("loading-section");
const resultsSection = document.getElementById("results-section");
const fieldsList = document.getElementById("fields-list");
const findingsList = document.getElementById("findings-list");
const extractedText = document.getElementById("extracted-text");
const printButton = document.getElementById("print-button");

// The fields shown in the results: key in the JSON -> label on screen
const FIELD_LABELS = [
  ["landlord", "Landlord name"],
  ["tenant", "Tenant name"],
  ["property_address", "Property address"],
  ["rent", "Monthly rent"],
  ["security_deposit", "Security deposit"],
  ["duration", "Agreement duration"],
  ["notice_period", "Notice period"]
];

const MAX_FILE_SIZE_MB = 10; // change if your backend allows a different size
let selectedFile = null;
let isAnalyzing = false;

// ---------- Small helpers ----------
function showError(message) {
  errorMessage.textContent = message; // textContent is safe (no HTML injection)
  errorMessage.hidden = false;
}

function clearError() {
  errorMessage.textContent = "";
  errorMessage.hidden = true;
}

function formatFileSize(bytes) {
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(2) + " MB";
}

// Lock or unlock the controls while a request is running
function setBusy(busy) {
  isAnalyzing = busy;
  analyzeButton.disabled = busy;
  fileInput.disabled = busy;
  dropArea.classList.toggle("disabled", busy);
  loadingSection.hidden = !busy;
}

// ---------- File selection and validation ----------
function handleFile(file) {
  clearError();
  selectedFile = null;
  fileInfo.hidden = true;

  if (!file) return;

  const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!isPdf) {
    showError("Unsupported file type. Please select a PDF file.");
    return;
  }
  if (file.size > MAX_FILE_SIZE_MB * 1024 * 1024) {
    showError("This file is too large. Please choose a PDF under " + MAX_FILE_SIZE_MB + " MB.");
    return;
  }

  selectedFile = file;
  fileNameText.textContent = file.name;
  fileSizeText.textContent = formatFileSize(file.size);
  fileInfo.hidden = false;
}

fileInput.addEventListener("change", function () {
  handleFile(fileInput.files[0]);
});

// Let the keyboard open the file picker from the label button
chooseButton.addEventListener("keydown", function (event) {
  if ((event.key === "Enter" || event.key === " ") && !isAnalyzing) {
    event.preventDefault();
    fileInput.click();
  }
});

// Drag and drop
dropArea.addEventListener("dragover", function (event) {
  event.preventDefault();
  dropArea.classList.add("drag-over");
});
dropArea.addEventListener("dragleave", function () {
  dropArea.classList.remove("drag-over");
});
dropArea.addEventListener("drop", function (event) {
  event.preventDefault();
  dropArea.classList.remove("drag-over");
  if (isAnalyzing) return;
  handleFile(event.dataTransfer.files[0]);
});

// ---------- Send the file to the backend ----------
analyzeButton.addEventListener("click", async function () {
  if (isAnalyzing) return;
  clearError();

  if (!selectedFile) {
    showError("No file selected. Please choose a PDF file first.");
    return;
  }

  resultsSection.hidden = true;
  setBusy(true);

  // FormData builds the multipart request. The field name must be "file".
  // Do NOT set the Content-Type header manually; the browser adds it.
  const formData = new FormData();
  formData.append("file", selectedFile);

  try {
    const response = await fetch("/analyze", { method: "POST", body: formData });

    let data = null;
    try {
      data = await response.json();
    } catch (parseError) {
      data = null; // the server did not send JSON
    }

    if (response.status === 413) {
      showError("The file is too large for the server. Please choose a smaller PDF.");
    } else if (data && data.success === false) {
      showError(data.error || "The document could not be analyzed.");
    } else if (response.ok && isValidResponse(data)) {
      showResults(data);
    } else {
      showError("The server returned an unexpected response. Please try again.");
    }
  } catch (networkError) {
    // fetch fails when the server cannot be reached
    showError("Cannot reach the server. Make sure the Flask app is running and try again.");
  } finally {
    setBusy(false);
  }
});

// Check the response has the shape described in the API contract
function isValidResponse(data) {
  return data && data.success === true && data.agreement && typeof data.agreement === "object";
}

// ---------- Show the results ----------
// Only textContent is used, so server text can never run as HTML.
function showResults(data) {
  // D. Fields
  fieldsList.textContent = "";
  FIELD_LABELS.forEach(function (pair) {
    const key = pair[0];
    const label = pair[1];
    const value = data.agreement[key];
    const detected = value !== null && value !== undefined && String(value).trim() !== "";

    const item = document.createElement("li");
    item.className = "field-item " + (detected ? "detected" : "missing");

    const textBox = document.createElement("div");
    const nameEl = document.createElement("div");
    nameEl.className = "field-name";
    nameEl.textContent = label;
    const valueEl = document.createElement("div");
    valueEl.className = "field-value";
    valueEl.textContent = detected ? String(value) : "Not detected";
    textBox.appendChild(nameEl);
    textBox.appendChild(valueEl);

    const badge = document.createElement("span");
    badge.className = "status-badge " + (detected ? "detected" : "missing");
    badge.textContent = detected ? "Detected" : "Missing";

    item.appendChild(textBox);
    item.appendChild(badge);
    fieldsList.appendChild(item);
  });

  // E. Findings
  findingsList.textContent = "";
  const findings = Array.isArray(data.findings) ? data.findings : [];
  if (findings.length === 0) {
    const empty = document.createElement("li");
    empty.className = "empty-message";
    empty.textContent = "The rules did not report any findings.";
    findingsList.appendChild(empty);
  }
  findings.forEach(function (finding) {
    const item = document.createElement("li");
    item.className = "finding-item";

    if (finding.rule_id) {
      const rule = document.createElement("span");
      rule.className = "finding-rule";
      rule.textContent = "Rule " + finding.rule_id;
      item.appendChild(rule);
    }

    const message = document.createElement("p");
    message.className = "finding-message";
    message.textContent = finding.message || "Finding reported.";
    item.appendChild(message);

    if (finding.explanation) {
      const explanation = document.createElement("p");
      explanation.className = "finding-explanation";
      explanation.textContent = finding.explanation;
      item.appendChild(explanation);
    }
    findingsList.appendChild(item);
  });

  // F. Extracted text
  extractedText.textContent = data.extracted_text || "No text was returned by the server.";

  resultsSection.hidden = false;
  resultsSection.scrollIntoView({ behavior: "smooth" });
}

// ---------- Print ----------
printButton.addEventListener("click", function () {
  window.print();
});
