"use strict";
(function () {
  const $ = id => document.getElementById(id);
  const {FIELDS, calculateOasis, scoreCSV} = window.OasisCalculator;
  const form = $("oasis-form");
  const result = $("result");
  const formError = $("form-error");
  let lastResult = null;

  function showError(err) {
    formError.textContent = err.message || String(err);
    formError.classList.remove("hidden");
  }

  function clearError() {
    formError.textContent = "";
    formError.classList.add("hidden");
  }

  function addText(tag, text, className) {
    const el = document.createElement(tag);
    el.textContent = text;
    if (className) el.className = className;
    result.appendChild(el);
    return el;
  }

  function render(data) {
    result.replaceChildren();
    addText("div", "OASIS POINTS", "score-label");
    addText("div", String(data.score), "score");
    const metric = addText("div", "", "metric");
    const lbl = document.createElement("div");
    lbl.className = "score-label";
    lbl.textContent = "Original-cohort estimated in-hospital mortality";
    metric.appendChild(lbl);
    const val = document.createElement("strong");
    val.textContent = data.estimated_in_hospital_mortality_percent.toFixed(2) + "%";
    metric.appendChild(val);
    addText("p", "Research estimate only; cohort validation and calibration are required.", "muted");
    const table = document.createElement("table");
    const thead = document.createElement("thead");
    const heading = document.createElement("tr");
    for (const title of ["Component", "Points"]) {
      const th = document.createElement("th");
      th.scope = "col"; th.textContent = title; heading.appendChild(th);
    }
    thead.appendChild(heading); table.appendChild(thead);
    const tbody = document.createElement("tbody");
    for (const [key, points] of Object.entries(data.component_scores)) {
      const tr = document.createElement("tr");
      for (const value of [key.replace(/_/g, " "), String(points)]) {
        const td = document.createElement("td");
        td.textContent = value; tr.appendChild(td);
      }
      tbody.appendChild(tr);
    }
    table.appendChild(tbody); result.appendChild(table);
  }

  form.addEventListener("submit", event => {
    event.preventDefault();
    clearError();
    try {
      if (!form.reportValidity()) throw new Error("Complete all required fields.");
      const input = Object.fromEntries(FIELDS.map(key => [key, form.elements[key].value]));
      lastResult = calculateOasis(input);
      render(lastResult);
      $("export-json").disabled = false;
    } catch (err) {
      lastResult = null; $("export-json").disabled = true;
      result.textContent = "No score calculated.";
      showError(err);
    }
  });
  form.addEventListener("reset", () => {
    clearError();
    result.textContent = "Enter complete observations and select Calculate OASIS.";
    lastResult = null; $("export-json").disabled = true;
  });

  function download(filename, type, content) {
    const url = URL.createObjectURL(new Blob([content], {type}));
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = filename;
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }

  $("export-json").addEventListener("click", () => {
    if (lastResult) download("oasis-result.json", "application/json",
      JSON.stringify(lastResult, null, 2) + "\n");
  });

  function csvCell(value) {
    const string = String(value ?? "");
    const safe = /^[\s]*[=+\-@\t\r]/.test(string) ? "'" + string : string;
    return '"' + safe.replace(/"/g, '""') + '"';
  }

  $("process-csv").addEventListener("click", async () => {
    const notice = $("csv-message");
    const file = $("csv-input").files[0];
    if (!file) { notice.textContent = "Select a CSV file first."; return; }
    if (file.size > 5 * 1024 * 1024) {
      notice.textContent = "File exceeds 5 MB local processing limit."; return;
    }
    const button = $("process-csv");
    button.disabled = true;
    notice.textContent = "Processing locally…";
    try {
      const rows = scoreCSV(await file.text());
      if (!rows.length) throw new Error("No data rows found.");
      const cols = ["record_id", "score", "estimated_in_hospital_mortality_percent",
        ...Object.keys(rows[0].component_scores).map(k => "points_" + k)];
      const csvRows = [cols.map(csvCell).join(",")];
      for (const record of rows) {
        const flat = {...record, ...Object.fromEntries(
          Object.entries(record.component_scores).map(([key, val]) => ["points_" + key, val]))};
        csvRows.push(cols.map(key => csvCell(flat[key])).join(","));
      }
      download("oasis-scored.csv", "text/csv;charset=utf-8",
        csvRows.join("\r\n") + "\r\n");
      notice.textContent = rows.length + " records scored locally; CSV download started.";
    } catch (err) {
      notice.textContent = err.message || "CSV processing failed.";
    } finally { button.disabled = false; }
  });
})();
