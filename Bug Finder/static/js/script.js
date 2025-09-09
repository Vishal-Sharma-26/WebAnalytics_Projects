let currentAnalysis = null;
let dragTimer = null;

// Initialize the application
document.addEventListener("DOMContentLoaded", function () {
  loadStats();
  loadHistory();
  setupFileUpload();
});

// Setup file upload functionality
function setupFileUpload() {
  const uploadArea = document.getElementById("uploadArea");
  const fileInput = document.getElementById("fileInput");

  if (!uploadArea || !fileInput){
    console.error("Upload area or file input not found in DOM.");
    return;
  }

  // Click to select file
  uploadArea.addEventListener("click", () => {
    fileInput.click();
  });

  // File input change
  fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  });

  // Drag and drop
  uploadArea.addEventListener("dragover", (e) => {
    e.preventDefault();
    uploadArea.classList.add("dragover");
    clearTimeout(dragTimer);
  });

  uploadArea.addEventListener("dragleave", (e) => {
    e.preventDefault();
    dragTimer = setTimeout(() => {
      uploadArea.classList.remove("dragover");
    }, 100);
  });

  uploadArea.addEventListener("drop", (e) => {
    e.preventDefault();
    uploadArea.classList.remove("dragover");
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFile(files[0]);
    }
  });
}

// Handle uploaded file
function handleFile(file) {
  const allowedTypes = [
    "py",
    "js",
    "java",
    "cpp",
    "c",
    "cs",
    "php",
    "rb",
    "go",
    "ts",
    "jsx",
    "tsx",
    "html",
    "css",
    "sql",
  ];
  const extension = file.name.split(".").pop().toLowerCase();

  if (!allowedTypes.includes(extension)) {
    showError("File type not supported. Please upload a supported code file.");
    return;
  }

  if (file.size > 16 * 1024 * 1024) {
    // 16MB limit
    showError("File too large. Please upload a file smaller than 16MB.");
    return;
  }

  // Update UI to show selected file
  const uploadArea = document.getElementById("uploadArea");
  uploadArea.innerHTML = `
                <div class="upload-icon">✅</div>
                <h3>File Selected: ${file.name}</h3>
                <p>Size: ${formatFileSize(file.size)}</p>
            `;
}

// Switch between tabs
function switchTab(tab) {
  // Update tab buttons
  document
    .querySelectorAll(".tab")
    .forEach((t) => t.classList.remove("active"));
  event.target.classList.add("active");

  // Update tab content
  document
    .querySelectorAll(".tab-content")
    .forEach((c) => c.classList.remove("active"));
  document.getElementById(tab + "Tab").classList.add("active");
}

// Analyze code
async function analyzeCode() {
  const analyzeBtn = document.getElementById("analyzeBtn");
  const originalText = analyzeBtn.innerHTML;

  try {
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<div class="spinner"></div> Analyzing...';

    let formData = new FormData();
    let isFileUpload = false;

    // Check which tab is active
    if (document.getElementById("fileTab").classList.contains("active")) {
      // File upload
      const fileInput = document.getElementById("fileInput");
      if (!fileInput.files[0]) {
        throw new Error("Please select a file to analyze");
      }
      formData.append("file", fileInput.files[0]);
      isFileUpload = true;
    } else {
      // Code input
      const code = document.getElementById("codeInput").value.trim();
      const filename = document.getElementById("filenameInput").value.trim();

      if (!code) {
        throw new Error("Please enter some code to analyze");
      }
      if (!filename) {
        throw new Error("Please enter a filename with extension");
      }
    }

    let response;
    if (isFileUpload) {
      response = await fetch("/api/analyze", {
        method: "POST",
        body: formData,
      });
    } else {
      response = await fetch("/api/analyze", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          code: document.getElementById("codeInput").value,
          filename: document.getElementById("filenameInput").value,
        }),
      });
    }

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || "Analysis failed");
    }

    const result = await response.json();
    displayResults(result);
    loadStats(); // Refresh stats
    loadHistory(); // Refresh history
  } catch (error) {
    showError(error.message);
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.innerHTML = originalText;
  }
}

// Display analysis results
function displayResults(analysis) {
  currentAnalysis = analysis;
  const resultsSection = document.getElementById("resultsSection");

  // Show results section
  resultsSection.classList.add("show");

  // Update filename
  document.getElementById(
    "analysisFilename"
  ).textContent = `File: ${analysis.filename}`;

  // Update severity counts
  document.getElementById("criticalCount").textContent =
    analysis.severity_count.Critical || 0;
  document.getElementById("highCount").textContent =
    analysis.severity_count.High || 0;
  document.getElementById("mediumCount").textContent =
    analysis.severity_count.Medium || 0;
  document.getElementById("lowCount").textContent =
    analysis.severity_count.Low || 0;

  // Display issues
  const issuesList = document.getElementById("issuesList");

  if (analysis.issues.length === 0) {
    issuesList.innerHTML = `
                    <div style="text-align: center; padding: 40px; color: #28a745;">
                        <h3>🎉 Great News!</h3>
                        <p>No issues found in your code. Keep up the good work!</p>
                    </div>
                `;
  } else {
    const issuesHtml = analysis.issues
      .map(
        (issue) => `
                    <div class="issue-item">
                        <div class="issue-header">
                            <span class="issue-type">${escapeHtml(
                              issue.type
                            )}</span>
                            <span class="issue-line">Line ${issue.line}</span>
                            <span class="severity-badge severity-${issue.severity.toLowerCase()}">${
          issue.severity
        }</span>
                        </div>
                        <div class="issue-message">${escapeHtml(
                          issue.message
                        )}</div>
                        <div class="issue-suggestion">💡 ${escapeHtml(
                          issue.suggestion
                        )}</div>
                    </div>
                `
      )
      .join("");

    issuesList.innerHTML = issuesHtml;
  }

  // Scroll to results
  resultsSection.scrollIntoView({ behavior: "smooth" });
}

// Load statistics
async function loadStats() {
  try {
    const response = await fetch("/api/stats");
    const stats = await response.json();

    document.getElementById("totalAnalyses").textContent =
      stats.total_analyses || 0;

    // Calculate totals from severity distribution
    let critical = 0,
      medium = 0,
      low = 0;
    stats.severity_distribution?.forEach((item) => {
      switch (item._id) {
        case "Critical":
        case "High":
          critical += item.count;
          break;
        case "Medium":
          medium += item.count;
          break;
        case "Low":
          low += item.count;
          break;
      }
    });

    document.getElementById("criticalIssues").textContent = critical;
    document.getElementById("mediumIssues").textContent = medium;
    document.getElementById("lowIssues").textContent = low;
  } catch (error) {
    console.error("Failed to load stats:", error);
  }
}

// Load analysis history
async function loadHistory() {
  const container = document.getElementById("historyContainer");

  try {
    const response = await fetch("/api/analyses");
    const analyses = await response.json();

    if (analyses.length === 0) {
      container.innerHTML =
        '<div class="loading">No analyses found. Upload some code to get started!</div>';
      return;
    }

    const historyHtml = analyses
      .map(
        (analysis) => `
                    <div class="history-item">
                        <div class="history-header">
                            <span class="history-filename">${escapeHtml(
                              analysis.filename
                            )}</span>
                            <span class="history-date">${formatDate(
                              analysis.created_date
                            )}</span>
                        </div>
                        <div class="history-stats">
                            <span class="history-stat">📊 ${
                              analysis.total_issues
                            } issues</span>
                            <span class="history-stat">🔴 ${
                              analysis.severity_count.Critical
                            } critical</span>
                            <span class="history-stat">🟡 ${
                              analysis.severity_count.Medium
                            } medium</span>
                            <span class="history-stat">🟢 ${
                              analysis.severity_count.Low
                            } low</span>
                        </div>
                        <div style="margin-top: 10px;">
                            <button class="btn btn-secondary" onclick="viewAnalysis('${
                              analysis._id
                            }')">View Details</button>
                            <button class="btn btn-secondary" onclick="deleteAnalysis('${
                              analysis._id
                            }')">Delete</button>
                        </div>
                    </div>
                `
      )
      .join("");

    container.innerHTML = `<div class="history-grid">${historyHtml}</div>`;
  } catch (error) {
    container.innerHTML =
      '<div class="error">Failed to load analysis history.</div>';
  }
}

// View specific analysis
async function viewAnalysis(analysisId) {
  try {
    const response = await fetch(`/api/analyses/${analysisId}`);
    const analysis = await response.json();
    displayResults(analysis);
  } catch (error) {
    showError("Failed to load analysis details");
  }
}

// Delete analysis
async function deleteAnalysis(analysisId) {
  if (!confirm("Are you sure you want to delete this analysis?")) {
    return;
  }

  try {
    const response = await fetch(`/api/analyses/${analysisId}`, {
      method: "DELETE",
    });

    if (response.ok) {
      showSuccess("Analysis deleted successfully");
      loadHistory();
      loadStats();
    } else {
      throw new Error("Failed to delete analysis");
    }
  } catch (error) {
    showError("Failed to delete analysis");
  }
}

// Download analysis report
function downloadReport() {
  if (!currentAnalysis) {
    showError("No analysis data to download");
    return;
  }

  const report = generateReport(currentAnalysis);
  const blob = new Blob([report], { type: "text/plain" });
  const url = URL.createObjectURL(blob);

  const a = document.createElement("a");
  a.href = url;
  a.download = `bug-report-${currentAnalysis.filename}.txt`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Generate text report
function generateReport(analysis) {
  let report = `BUG FINDER - CODE ANALYSIS REPORT\n`;
  report += `${"=".repeat(40)}\n\n`;
  report += `File: ${analysis.filename}\n`;
  report += `Analysis Date: ${new Date(
    analysis.created_date
  ).toLocaleString()}\n`;
  report += `Total Issues Found: ${analysis.total_issues}\n\n`;

  report += `SEVERITY SUMMARY:\n`;
  report += `- Critical: ${analysis.severity_count.Critical || 0}\n`;
  report += `- High: ${analysis.severity_count.High || 0}\n`;
  report += `- Medium: ${analysis.severity_count.Medium || 0}\n`;
  report += `- Low: ${analysis.severity_count.Low || 0}\n\n`;

  if (analysis.issues.length > 0) {
    report += `DETAILED ISSUES:\n`;
    report += `${"=".repeat(20)}\n\n`;

    analysis.issues.forEach((issue, index) => {
      report += `${index + 1}. ${issue.type} (Line ${issue.line}) - ${
        issue.severity
      }\n`;
      report += `   Message: ${issue.message}\n`;
      report += `   Suggestion: ${issue.suggestion}\n\n`;
    });
  } else {
    report += `🎉 GREAT NEWS! No issues found in your code.\n`;
  }

  return report;
}

// Utility functions
function formatFileSize(bytes) {
  if (bytes === 0) return "0 Bytes";
  const k = 1024;
  const sizes = ["Bytes", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
}

function formatDate(dateString) {
  return (
    new Date(dateString).toLocaleDateString() +
    " " +
    new Date(dateString).toLocaleTimeString()
  );
}

function escapeHtml(text) {
  const div = document.createElement("div");
  div.textContent = text;
  return div.innerHTML;
}

function showError(message) {
  // Remove existing notifications
  const existing = document.querySelectorAll(".error, .success");
  existing.forEach((el) => el.remove());

  const errorDiv = document.createElement("div");
  errorDiv.className = "error";
  errorDiv.textContent = message;

  document
    .querySelector(".container")
    .insertBefore(errorDiv, document.querySelector(".upload-section"));

  // Auto remove after 5 seconds
  setTimeout(() => {
    if (errorDiv.parentNode) {
      errorDiv.parentNode.removeChild(errorDiv);
    }
  }, 5000);
}

function showSuccess(message) {
  // Remove existing notifications
  const existing = document.querySelectorAll(".error, .success");
  existing.forEach((el) => el.remove());

  const successDiv = document.createElement("div");
  successDiv.className = "success";
  successDiv.textContent = message;

  document
    .querySelector(".container")
    .insertBefore(successDiv, document.querySelector(".upload-section"));

  // Auto remove after 3 seconds
  setTimeout(() => {
    if (successDiv.parentNode) {
      successDiv.parentNode.removeChild(successDiv);
    }
  }, 3000);
}
