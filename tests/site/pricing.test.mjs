// Engine tests for site/pricing.js — the shared pricing model.
// Dev-only (`make test-site`, needs node); offline CI stays `make test`.
// The pinned numbers below were computed by hand in the plan
// (docs/superpowers/plans/2026-07-31-perfect-method-price-team.md, Task 1).
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
const require = createRequire(import.meta.url);
const P = require("../../site/pricing.js");

test("levels sample the share line", () => {
  for (const lv of P.LEVELS)
    assert.equal(Number(P.share(lv.cover).toFixed(2)), lv.share);
});

test("agreed rounds toward the person", () => {
  assert.equal(P.agreed({ self: 1, evalr: 0.5 }), 1);     // 0.75 → 1
  assert.equal(P.agreed({ self: 0.5, evalr: 0 }), 0.5);   // 0.25 → 0.5
  assert.equal(P.agreed({ self: 1, evalr: 1 }), 1);
});

test("coverage thresholds pick the level", () => {
  assert.equal(P.levelFor(0.875).id, "autonomous");
  assert.equal(P.levelFor(0.874).id, "with-review");
  assert.equal(P.levelFor(0.625).id, "with-review");
  assert.equal(P.levelFor(0.624).id, "with-support");
});

test("CoL floor binds", () => {
  assert.equal(P.applyCol(100, 0.28, 0.4), 40);
  assert.equal(P.applyCol(100, 0.82, 0.4), 82);
});

test("no-deal minimum client rate", () => {
  assert.equal(P.minClientRate(59.5, 0.3), 85); // worked example, concept §9
});

// The team equation — pinned numbers, computed by hand in the plan.
const rows = [
  { weight: 0.30, levelIndex: 0, coef: 1.00, floor: 0, ownRate: 55 },
  { weight: 0.45, levelIndex: 1, coef: 0.82, floor: 0, ownRate: 40 },
  { weight: 0.25, levelIndex: 2, coef: 0.32, floor: 0, ownRate: 12 },
];

test("computeTeam decomposes R into four bands", () => {
  const r = P.computeTeam(100, rows);
  assert.equal(r.ok, true);
  assert.equal(Number(r.payouts.toFixed(2)), 37.5);
  assert.equal(Number(r.headroom.toFixed(2)), 9.64);
  assert.equal(Number(r.geoBand.toFixed(2)), 13.36);
  assert.equal(Number(r.welanceMargin.toFixed(2)), 39.5);
  assert.equal(Number(r.marginTarget.toFixed(3)), 0.395);
  const total = r.payouts + r.headroom + r.geoBand + r.welanceMargin;
  assert.ok(Math.abs(total - 100) < 1e-9);
  assert.equal(Number(r.minViableR.toFixed(2)), 81.3);
});

test("computeTeam flags the failing row, never compresses", () => {
  const r = P.computeTeam(70, rows); // fullstack ceiling 70*0.6*0.82=34.44 < 40
  assert.equal(r.ok, false);
  assert.equal(r.rows[1].ok, false);
});

test("formula registry is the count", () => {
  assert.equal(P.FORMULAS.length, 8);
  assert.deepEqual(P.FORMULAS.map((f) => f.n), [1, 2, 3, 4, 5, 6, 7, 8]);
  for (const f of P.FORMULAS)
    for (const k of ["id", "name", "formula", "plain", "source"])
      assert.ok(f[k], `${f.id ?? "?"} missing ${k}`);
});

/* ---------- edge cases: the equation must never lie ---------- */

test("weights normalise: 30/45/25 and 0.30/0.45/0.25 are the same team", () => {
  const a = P.computeTeam(100, rows);
  const b = P.computeTeam(100, rows.map(r => ({ ...r, weight: r.weight * 100 })));
  for (const k of ["payouts", "headroom", "geoBand", "welanceMargin", "minViableR"])
    assert.ok(Math.abs(a[k] - b[k]) < 1e-9, k);
});

test("a single row still sums exactly", () => {
  const r = P.computeTeam(80, [{ weight: 1, levelIndex: 1, coef: 0.82, floor: 0, ownRate: 30 }]);
  const total = r.payouts + r.headroom + r.geoBand + r.welanceMargin;
  assert.ok(Math.abs(total - 80) < 1e-9);
});

test("empty team: zeros, no crash", () => {
  const r = P.computeTeam(100, []);
  assert.equal(r.ok, true);
  assert.equal(r.payouts + r.headroom + r.geoBand + r.welanceMargin, 0);
  assert.equal(r.minViableR, 0);
});

test("coefficient above 1 (Switzerland): identity holds, geo band goes negative", () => {
  const r = P.computeTeam(100, [{ weight: 1, levelIndex: 0, coef: 1.35, floor: 0, ownRate: 70 }]);
  const total = r.payouts + r.headroom + r.geoBand + r.welanceMargin;
  assert.ok(Math.abs(total - 100) < 1e-9);
  assert.ok(r.geoBand < 0); // ceiling above role-only: the band flips sign, it never hides
});

test("floor binds inside the team equation too", () => {
  const low = P.computeTeam(100, [{ weight: 1, levelIndex: 2, coef: 0.32, floor: 0.5, ownRate: 12 }]);
  assert.equal(Number(low.rows[0].ceiling.toFixed(2)), 25); // 100 × 0.5 × max(0.32, 0.5)
  const full = P.computeTeam(100, [{ weight: 1, levelIndex: 2, coef: 0.32, floor: 1, ownRate: 12 }]);
  assert.equal(Number(full.geoBand.toFixed(10)), 0); // floor 1 = geography off
});

test("no-deal boundary: own rate exactly at the ceiling is a deal", () => {
  const r = P.computeTeam(100, [{ weight: 1, levelIndex: 0, coef: 1, floor: 0, ownRate: 70 }]);
  assert.equal(r.ok, true);
  assert.equal(Number(r.headroom.toFixed(10)), 0);
});

test("zero-weight rows carry nothing", () => {
  const r = P.computeTeam(100, [
    { weight: 0, levelIndex: 0, coef: 1, floor: 0, ownRate: 999 },
    { weight: 1, levelIndex: 0, coef: 1, floor: 0, ownRate: 70 },
  ]);
  assert.equal(Number(r.payouts.toFixed(2)), 70);
});

test("formula ids are unique", () => {
  const ids = P.FORMULAS.map(f => f.id);
  assert.equal(new Set(ids).size, ids.length);
});
