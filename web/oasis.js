/* OASIS first-ICU-day points; matches MIT-LCP MIMIC-IV oasis.sql.
 * No patient identifiers or observations are transmitted or stored.
 */
(function (root) {
  "use strict";

  const FIELDS = [
    "age", "pre_icu_los_hours", "gcs_min", "heart_rate_min", "heart_rate_max",
    "map_min", "map_max", "respiratory_rate_min", "respiratory_rate_max",
    "temperature_min", "temperature_max", "urine_output_ml",
    "mechanically_ventilated", "elective_surgery"
  ];
  const FLAGS = ["mechanically_ventilated", "elective_surgery"];

  function calculateOasis(input) {
    if (!input || typeof input !== "object" || Array.isArray(input)) {
      throw new Error("An observation object is required.");
    }
    const unknown = Object.keys(input).filter(key => !FIELDS.includes(key));
    if (unknown.length) throw new Error("Unknown OASIS field: " + unknown.join(", "));
    const v = {};
    for (const key of FIELDS) {
      const raw = input[key];
      if (raw === undefined || raw === null || String(raw).trim() === "") {
        throw new Error(key + ": value required");
      }
      if (FLAGS.includes(key)) {
        const normalized = String(raw).trim().toLowerCase();
        if (!["true", "false", "1", "0", "yes", "no"].includes(normalized)) {
          throw new Error(key + ": use yes or no");
        }
        v[key] = ["true", "1", "yes"].includes(normalized);
      } else {
        if (typeof raw === "boolean") throw new Error(key + ": invalid number");
        const value = Number(raw);
        if (!Number.isFinite(value) || value < 0) {
          throw new Error(key + ": must be finite and non-negative");
        }
        v[key] = value;
      }
    }
    if (v.age < 18 || v.age > 120) throw new Error("age: expected adult age 18–120");
    if (!Number.isInteger(v.gcs_min) || v.gcs_min < 3 || v.gcs_min > 15) {
      throw new Error("gcs_min: expected integer 3–15");
    }
    for (const key of ["heart_rate", "map", "respiratory_rate", "temperature"]) {
      if (v[key + "_min"] > v[key + "_max"]) {
        throw new Error(key + ": minimum exceeds maximum");
      }
    }
    const preicu = v.pre_icu_los_hours * 60;
    const points = {
      pre_icu_los: preicu < 10.2 ? 5 : preicu < 297 ? 3 : preicu < 1440 ? 0 : preicu < 18708 ? 2 : 1,
      age: v.age < 24 ? 0 : v.age <= 53 ? 3 : v.age <= 77 ? 6 : v.age <= 89 ? 9 : 7,
      gcs: v.gcs_min <= 7 ? 10 : v.gcs_min < 14 ? 4 : v.gcs_min === 14 ? 3 : 0,
      heart_rate: v.heart_rate_max > 125 ? 6 : v.heart_rate_min < 33 ? 4 :
        v.heart_rate_max >= 107 ? 3 : v.heart_rate_max >= 89 ? 1 : 0,
      map: v.map_min < 20.65 ? 4 : v.map_min < 51 ? 3 : v.map_max > 143.44 ? 3 :
        v.map_min < 61.33 ? 2 : 0,
      respiratory_rate: v.respiratory_rate_min < 6 ? 10 : v.respiratory_rate_max > 44 ? 9 :
        v.respiratory_rate_max > 30 ? 6 : v.respiratory_rate_max > 22 ? 1 :
        v.respiratory_rate_min < 13 ? 1 : 0,
      temperature: v.temperature_max > 39.88 ? 6 :
        ((v.temperature_min >= 33.22 && v.temperature_min <= 35.93) ||
         (v.temperature_max >= 33.22 && v.temperature_max <= 35.93)) ? 4 :
        v.temperature_min < 33.22 ? 3 :
        (v.temperature_min > 35.93 && v.temperature_min <= 36.39) ? 2 :
        (v.temperature_max >= 36.89 && v.temperature_max <= 39.88) ? 2 : 0,
      urine_output: v.urine_output_ml < 671.09 ? 10 : v.urine_output_ml > 6896.80 ? 8 :
        v.urine_output_ml < 1427 ? 5 : v.urine_output_ml <= 2544.14 ? 1 : 0,
      mechanical_ventilation: v.mechanically_ventilated ? 9 : 0,
      elective_surgery: v.elective_surgery ? 0 : 6
    };
    const score = Object.values(points).reduce((sum, n) => sum + n, 0);
    const estimated = 100 / (1 + Math.exp(-(-6.1746 + 0.1275 * score)));
    return {
      score, component_scores: points,
      estimated_in_hospital_mortality_percent: Math.round((estimated + Number.EPSILON) * 100) / 100,
      calibration_note: "Original OASIS cohort equation; local validation required."
    };
  }

  // Strict CSV reading (including quoted commas and embedded newlines).
  function parseCSV(text) {
    const rows = [];
    let row = [], value = "", quoted = false, quoteClosed = false;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (quoted) {
        if (ch === '"') {
          if (text[i + 1] === '"') { value += '"'; i++; }
          else { quoted = false; quoteClosed = true; }
        } else value += ch;
      } else if (ch === "," || ch === "\n" || ch === "\r") {
        row.push(value); value = ""; quoteClosed = false;
        if (ch !== ",") {
          rows.push(row); row = [];
          if (ch === "\r" && text[i + 1] === "\n") i++;
        }
      } else if (ch === '"' && value === "" && !quoteClosed) quoted = true;
      else if (quoteClosed || ch === '"') throw new Error("Invalid CSV quoting");
      else value += ch;
    }
    if (quoted) throw new Error("Unclosed CSV quotation");
    if (value !== "" || row.length) { row.push(value); rows.push(row); }
    return rows;
  }

  function scoreCSV(text) {
    const rows = parseCSV(String(text).replace(/^\uFEFF/, ""));
    if (!rows.length) throw new Error("Empty CSV");
    const headers = rows.shift();
    if (new Set(headers).size !== headers.length ||
        headers.some(k => !FIELDS.includes(k) && k !== "record_id") ||
        FIELDS.some(k => !headers.includes(k))) {
      throw new Error("CSV columns must include all OASIS fields and optional record_id.");
    }
    const scored = rows.filter(row => !(row.length === 1 && row[0] === "")).map((row, index) => {
      if (row.length !== headers.length) throw new Error("CSV row " + (index + 2) + ": incorrect column count");
      const input = Object.fromEntries(headers.map((key, j) => [key, row[j]]));
      try { return {record_id: input.record_id || "", ...calculateOasis(
        Object.fromEntries(FIELDS.map(key => [key, input[key]]))
      )}; }
      catch (err) { throw new Error("CSV row " + (index + 2) + ": " + err.message); }
    });
    return scored;
  }

  const api = {FIELDS, calculateOasis, parseCSV, scoreCSV};
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  if (root) root.OasisCalculator = api;
})(typeof window !== "undefined" ? window : null);
