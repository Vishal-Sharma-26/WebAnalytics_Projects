document.addEventListener("DOMContentLoaded", () => {
  const validateBtn = document.getElementById("validateBtn");
  const autoFixBtn = document.getElementById("autoFixBtn");
  const uploadFileBtn = document.getElementById("uploadFileBtn");
  const fileInput = document.getElementById("fileInput");
  const invoiceJson = document.getElementById("invoiceJson");
  const resultArea = document.getElementById("resultArea");
  const messages = document.getElementById("messages");
  const jsonOutput = document.getElementById("jsonOutput");
  const savedList = document.getElementById("savedList");

  function showResult(obj) {
    resultArea.style.display = "block";
    messages.innerHTML = "";
    if (obj.errors && obj.errors.length > 0) {
      messages.innerHTML += `<div class="alert alert-danger"><strong>Errors:</strong><ul>${obj.errors.map(e=>`<li>${e}</li>`).join("")}</ul></div>`;
    }
    if (obj.warnings && obj.warnings.length > 0) {
      messages.innerHTML += `<div class="alert alert-warning"><strong>Warnings:</strong><ul>${obj.warnings.map(e=>`<li>${e}</li>`).join("")}</ul></div>`;
    }
    if (obj.valid) {
      messages.innerHTML += `<div class="alert alert-success">Invoice is valid.</div>`;
    }
    if (obj.fix_suggestions && Object.keys(obj.fix_suggestions).length > 0) {
      messages.innerHTML += `<div class="alert alert-info"><strong>Suggested Fixes:</strong><pre>${JSON.stringify(obj.fix_suggestions, null, 2)}</pre></div>`;
    }
    jsonOutput.textContent = JSON.stringify(obj.computed ? {computed: obj.computed, summary: {valid: obj.valid}} : obj, null, 2);
  }

  validateBtn.addEventListener("click", async () => {
    let text = invoiceJson.value.trim();
    if (!text) return alert("Please paste invoice JSON or upload a file.");
    let parsed;
    try { parsed = JSON.parse(text); } catch(e){ return alert("Invalid JSON: " + e.message); }
    try {
      const res = await axios.post("/api/validate", parsed);
      showResult(res.data);
    } catch(err){
      const data = err.response ? err.response.data : {error: err.message};
      messages.innerHTML = `<div class="alert alert-danger">Request failed: ${JSON.stringify(data)}</div>`;
      resultArea.style.display = "block";
      jsonOutput.textContent = JSON.stringify(data, null, 2);
    }
  });

  autoFixBtn.addEventListener("click", async () => {
    let text = invoiceJson.value.trim();
    if (!text) return alert("Please paste invoice JSON or upload a file.");
    let parsed;
    try { parsed = JSON.parse(text); } catch(e){ return alert("Invalid JSON: " + e.message); }
    try {
      const res = await axios.post("/api/invoices?auto_fix=true", parsed);
      messages.innerHTML = `<div class="alert alert-success">Saved as invoice id ${res.data.invoice_id}</div>`;
      showResult(res.data.validation);
      loadSaved();
    } catch(err){
      const data = err.response ? err.response.data : {error: err.message};
      messages.innerHTML = `<div class="alert alert-danger">Save failed: ${JSON.stringify(data)}</div>`;
      resultArea.style.display = "block";
      jsonOutput.textContent = JSON.stringify(data, null, 2);
    }
  });

  uploadFileBtn.addEventListener("click", () => fileInput.click());
  fileInput.addEventListener("change", (e) => {
    const f = e.target.files[0];
    if (!f) return;
    const reader = new FileReader();
    reader.onload = (ev) => { invoiceJson.value = ev.target.result; };
    reader.readAsText(f);
  });

  async function deleteInvoice(id) {
    if (!confirm("Are you sure you want to delete this invoice?")) return;
    try {
      await axios.delete("/api/invoices/" + id);
      loadSaved();
    } catch (err) { alert("Failed to delete invoice"); }
  }

  function toggleInvoiceContent(id) {
    const elem = document.getElementById("content-" + id);
    if (!elem) return;
    elem.style.display = elem.style.display === "none" ? "block" : "none";
  }

  async function loadSaved() {
    try {
      const res = await axios.get("/api/invoices");
      const invoices = res.data;
      if (invoices.length === 0) { savedList.innerHTML = `<div class="text-muted">No saved invoices yet.</div>`; return; }

      savedList.innerHTML = invoices.map(inv => `
        <div class="card mb-2">
          <div class="card-body">
            <div class="d-flex justify-content-between align-items-center">
              <strong>${inv.invoice_number || "(no number)"}</strong> — ${inv.supplier || ""}
              <div>
                <button class="btn btn-sm btn-info me-1" onclick="toggleInvoiceContent('${inv._id}')">Toggle</button>
                <button class="btn btn-sm btn-danger" onclick="deleteInvoice('${inv._id}')">Delete</button>
              </div>
            </div>
            <small class="text-muted">${inv.date || inv._created_at || ""}</small>
            <div id="content-${inv._id}" style="margin-top:6px;">
              <pre>${JSON.stringify(inv, null, 2)}</pre>
            </div>
          </div>
        </div>`).join("");

    } catch (err) { savedList.innerHTML = `<div class="text-danger">Failed loading invoices</div>`; }
  }

  // Expose toggle/delete to global for buttons
  window.toggleInvoiceContent = toggleInvoiceContent;
  window.deleteInvoice = deleteInvoice;

  loadSaved();
});
