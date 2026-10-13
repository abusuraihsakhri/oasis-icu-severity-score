const test = require("node:test");
const assert = require("node:assert/strict");
const {calculateOasis, scoreCSV, FIELDS} = require("./oasis.js");

function normal(extra = {}) {
  return {
    age: 40, pre_icu_los_hours: 8, gcs_min: 15,
    heart_rate_min: 70, heart_rate_max: 88, map_min: 80, map_max: 90,
    respiratory_rate_min: 16, respiratory_rate_max: 20,
    temperature_min: 36.4, temperature_max: 36.8, urine_output_ml: 3000,
    mechanically_ventilated: false, elective_surgery: true, ...extra
  };
}
test("reference normal-case points", () => {
  const res = calculateOasis(normal());
  assert.equal(res.score, 3);
  assert.equal(res.component_scores.age, 3);
});
test("published extreme case: 75 points", () => {
  const res = calculateOasis(normal({
    age: 80, pre_icu_los_hours: 0, gcs_min: 3,
    heart_rate_min: 20, heart_rate_max: 140,
    map_min: 10, map_max: 160,
    respiratory_rate_min: 2, respiratory_rate_max: 50,
    temperature_min: 32, temperature_max: 41,
    urine_output_ml: 100, mechanically_ventilated: true,
    elective_surgery: false
  }));
  assert.equal(res.score, 75);
});
test("vital extreme precedence", () => {
  const pts = calculateOasis(normal({heart_rate_min: 20, heart_rate_max: 130,
    respiratory_rate_min: 2, respiratory_rate_max: 50})).component_scores;
  assert.equal(pts.heart_rate, 6);
  assert.equal(pts.respiratory_rate, 10);
});
test("boundaries and missing data", () => {
  assert.equal(calculateOasis(normal({pre_icu_los_hours: 10.19/60})).component_scores.pre_icu_los, 5);
  assert.equal(calculateOasis(normal({pre_icu_los_hours: 10.2/60})).component_scores.pre_icu_los, 3);
  assert.throws(() => calculateOasis(normal({age: undefined})));
  assert.throws(() => calculateOasis(normal({temperature_min: 40, temperature_max: 37})));
  assert.throws(() => calculateOasis(normal({map_min: NaN})));
  assert.throws(() => calculateOasis(normal({mechanically_ventilated: "maybe"})));
});
test("CSV rows and quoted identifier", () => {
  const head = ["record_id", ...FIELDS];
  const values = normal();
  const csv = head.join(",") + "\r\n" +
    ['"case, one"', ...FIELDS.map(key => values[key])].join(",") + "\r\n";
  const rows = scoreCSV(csv);
  assert.equal(rows.length, 1);
  assert.equal(rows[0].record_id, "case, one");
  assert.equal(rows[0].score, 3);
  assert.throws(() => scoreCSV("v1,v2\n1,2\n"));
});
