/* welance pricing — the whole model in one readable file.
 *
 * Every constant here has a reason, recorded in
 * docs/pricing/PRICING.md; the section is cited next to each.
 * If you disagree with a number: find it, read its section, open a PR
 * against it. That is the point of this file.
 *
 * No DOM, no dependencies, no build step. price.html and team.html are
 * thin UIs over this object; tests/site/pricing.test.mjs pins the numbers.
 */
(function (root) {
  "use strict";

  // §3 The rule — the three levels are one line, sampled.
  // share(coverage) = 30% + 0.4 × coverage; margin is what remains.
  var LEVELS = [
    { id: "autonomous",   cover: 1.00, share: 0.70 },
    { id: "with-review",  cover: 0.75, share: 0.60 },
    { id: "with-support", cover: 0.50, share: 0.50 }
  ];
  function share(cov) { return 0.30 + 0.40 * cov; }
  function marginOf(levelIndex) { return 1 - LEVELS[levelIndex].share; }

  // §4 Each part of a role is scored full / partial / none — by the person
  // AND by the most role-adjacent senior colleague.
  var STEPS = [1, 0.5, 0];

  // §6 Internal work has no client rate — there is nothing to take a share
  // of. Cap at the top level, scaled down by level (Enrico, 2026-07-31).
  var INTERNAL_MAX = 50;

  // §7 Cost of living — rough ratios against Germany = 1.00.
  // EDITABLE DEFAULTS ONLY: replace from a real source (OECD PPP,
  // World Bank ICP, Numbeo) before anyone's pay depends on them.
  var COUNTRIES = [
    { code: "CH", coef: 1.35, en: "Switzerland", de: "Schweiz", it: "Svizzera", ur: "سوئٹزرلینڈ", pt: "Suíça", es: "Suiza", vi: "Thụy Sĩ", ar: "سويسرا" },
    { code: "DE", coef: 1.00, en: "Germany", de: "Deutschland", it: "Germania", ur: "جرمنی", pt: "Alemanha", es: "Alemania", vi: "Đức", ar: "ألمانيا" },
    { code: "AT", coef: 0.95, en: "Austria", de: "Österreich", it: "Austria", ur: "آسٹریا", pt: "Áustria", es: "Austria", vi: "Áo", ar: "النمسا" },
    { code: "IT", coef: 0.82, en: "Italy", de: "Italien", it: "Italia", ur: "اٹلی", pt: "Itália", es: "Italia", vi: "Ý", ar: "إيطاليا" },
    { code: "ES", coef: 0.75, en: "Spain", de: "Spanien", it: "Spagna", ur: "اسپین", pt: "Espanha", es: "España", vi: "Tây Ban Nha", ar: "إسبانيا" },
    { code: "PT", coef: 0.68, en: "Portugal", de: "Portugal", it: "Portogallo", ur: "پرتگال", pt: "Portugal", es: "Portugal", vi: "Bồ Đào Nha", ar: "البرتغال" },
    { code: "PL", coef: 0.55, en: "Poland", de: "Polen", it: "Polonia", ur: "پولینڈ", pt: "Polônia", es: "Polonia", vi: "Ba Lan", ar: "بولندا" },
    { code: "BR", coef: 0.42, en: "Brazil", de: "Brasilien", it: "Brasile", ur: "برازیل", pt: "Brasil", es: "Brasil", vi: "Brazil", ar: "البرازيل" },
    { code: "AR", coef: 0.38, en: "Argentina", de: "Argentinien", it: "Argentina", ur: "ارجنٹینا", pt: "Argentina", es: "Argentina", vi: "Argentina", ar: "الأرجنتين" },
    { code: "UA", coef: 0.38, en: "Ukraine", de: "Ukraine", it: "Ucraina", ur: "یوکرین", pt: "Ucrânia", es: "Ucrania", vi: "Ukraina", ar: "أوكرانيا" },
    { code: "VN", coef: 0.32, en: "Vietnam", de: "Vietnam", it: "Vietnam", ur: "ویتنام", pt: "Vietnã", es: "Vietnam", vi: "Việt Nam", ar: "فيتنام" },
    { code: "IN", coef: 0.30, en: "India", de: "Indien", it: "India", ur: "بھارت", pt: "Índia", es: "India", vi: "Ấn Độ", ar: "الهند" },
    { code: "PK", coef: 0.28, en: "Pakistan", de: "Pakistan", it: "Pakistan", ur: "پاکستان", pt: "Paquistão", es: "Pakistán", vi: "Pakistan", ar: "باكستان" }
  ];

  // §4 Where the two views differ by one step, coverage rounds toward the
  // person. A two-step gap is not averaged — it is discussed (the UI stops).
  function agreed(c) {
    var m = (c.self + c.evalr) / 2;
    if (m === 0.75) return 1;
    if (m === 0.25) return 0.5;
    return m;
  }

  // §4 Coverage is the weighted mean of the agreed part scores.
  function coverageOf(list) {
    var w = 0, s = 0;
    list.forEach(function (c) {
      var wt = Number(c.weight) > 0 ? Number(c.weight) : 0;
      w += wt; s += wt * agreed(c);
    });
    return w > 0 ? s / w : 0;
  }

  // §3 Midpoint thresholds between the three sampled coverage points.
  function levelFor(cov) {
    return cov >= 0.875 ? LEVELS[0] : cov >= 0.625 ? LEVELS[1] : LEVELS[2];
  }

  // §7 payout_local = payout_role × max(coefficient, floor).
  // The floor is what distinguishes a cost-of-living adjustment from
  // arbitrage; the differential is ALWAYS shown as its own band.
  function applyCol(payout, coef, floor) {
    var c = Number(coef) > 0 ? Number(coef) : 1;
    var f = Number(floor) > 0 ? Number(floor) : 0;
    return payout * Math.max(c, f);
  }

  // §8 No-deal: if the client will not pay payout / (1 − m), the
  // engagement does not happen. Nobody is compressed below their rate.
  function minClientRate(payout, marginTarget) {
    return payout / (1 - marginTarget);
  }

  /* The team equation (spec §5) — one blended client rate R, decomposed
   * into four bands that must sum exactly to R:
   *
   *   payouts        what the people actually asked for
   *   headroom       ceiling minus asked — visible, never silently margin
   *   geo band       the cost-of-living differential — same rule as §7
   *   margin         Σ wᵢ · m(levelᵢ) · R — the named recipe. The field is
   *                  still welanceMargin: renaming the returned key would
   *                  touch both calculators and the engine tests for a
   *                  word no reader ever sees.
   *
   * rows: [{ weight, levelIndex, coef, floor, ownRate }]
   * Weights are normalised over their sum, so 30/45/25 and 0.3/0.45/0.25
   * mean the same team. */
  function computeTeam(R, rows) {
    var totalW = rows.reduce(function (s, r) {
      return s + (Number(r.weight) > 0 ? Number(r.weight) : 0);
    }, 0);

    var out = rows.map(function (r) {
      var w = totalW > 0 ? (Number(r.weight) > 0 ? Number(r.weight) : 0) / totalW : 0;
      var sh = LEVELS[r.levelIndex].share;
      var roleOnlyCeiling = R * sh;                         // before CoL
      var ceiling = applyCol(roleOnlyCeiling, r.coef, r.floor); // local ceiling
      var ownRate = Number(r.ownRate) > 0 ? Number(r.ownRate) : 0;
      var ok = ownRate <= ceiling + 1e-9;                   // §8, per row
      return {
        w: w, share: sh,
        roleOnlyCeiling: roleOnlyCeiling,
        ceiling: ceiling,
        ownRate: ownRate,
        ok: ok,
        headroom: ok ? ceiling - ownRate : 0,
        // the smallest R at which THIS row clears no-deal
        minR: ownRate > 0 ? ownRate / (sh * Math.max(Number(r.coef) > 0 ? Number(r.coef) : 1, Number(r.floor) > 0 ? Number(r.floor) : 0)) : 0
      };
    });

    var payouts = 0, headroom = 0, geoBand = 0, welanceMargin = 0, minViableR = 0, allOk = true;
    out.forEach(function (r) {
      payouts += r.w * r.ownRate;
      headroom += r.w * r.headroom;
      geoBand += r.w * (r.roleOnlyCeiling - r.ceiling);
      welanceMargin += r.w * (R - r.roleOnlyCeiling); // = w · m(level) · R
      if (r.minR > minViableR) minViableR = r.minR;
      if (!r.ok) allOk = false;
    });

    return {
      rows: out,
      payouts: payouts,
      headroom: headroom,
      geoBand: geoBand,
      welanceMargin: welanceMargin,
      marginTarget: R > 0 ? welanceMargin / R : 0, // Σ wᵢ · m(levelᵢ)
      ok: allOk,
      minViableR: minViableR
    };
  }

  /* The N formulas — everything this model computes, in one list.
   * Pages derive the count from FORMULAS.length; never hardcode it.
   * Everything NOT in this list is human capital, and it does not compute. */
  var FORMULAS = [
    { id: "score",    n: 1, name: "The score",         formula: "score = Σ weightᵢ × verdictᵢ  (weights sum to 100)",          plain: "How good a brief is: a weighted average over public, versioned rules.",                                     source: "brief_bar/scoring.yaml", url: "https://github.com/welance/perfect-brief/blob/main/brief_bar/scoring.yaml" },
    { id: "gate",     n: 2, name: "The gate",          formula: "publish ⇔ every hard requirement holds",                       plain: "Whether a brief may publish at all — no average can paper over a hard miss.",                              source: "brief_bar/scoring.yaml", url: "https://github.com/welance/perfect-brief/blob/main/brief_bar/scoring.yaml" },
    { id: "coverage", n: 3, name: "Coverage",          formula: "coverage = Σ wᵢ × agreedᵢ / Σ wᵢ",                             plain: "How much of a role someone covers, part by part, agreed by both views.",                                   source: "PRICING.md §4", url: "https://github.com/welance/perfect-brief/blob/main/docs/pricing/PRICING.md#4-deriving-the-level-decompose-the-role" },
    { id: "share",    n: 4, name: "The share",         formula: "share = 30% + 0.4 × coverage",                                 plain: "The slice of the client rate that goes to the person — it follows from coverage, nothing else.",           source: "PRICING.md §3", url: "https://github.com/welance/perfect-brief/blob/main/docs/pricing/PRICING.md#3-the-rule" },
    { id: "margin",   n: 5, name: "The margin rule",   formula: "(R − payout) / R ≥ m(level)",                                  plain: "What the collective retains, priced as the risk it actually carries at that level.",                       source: "PRICING.md §3", url: "https://github.com/welance/perfect-brief/blob/main/docs/pricing/PRICING.md#3-the-rule" },
    { id: "col",      n: 6, name: "Cost of living",    formula: "payout_local = payout_role × max(coeff, floor)",               plain: "A stated, floored geographic adjustment — always shown as its own band, never hidden in margin.",          source: "PRICING.md §7", url: "https://github.com/welance/perfect-brief/blob/main/docs/pricing/PRICING.md#7-cost-of-living" },
    { id: "nodeal",   n: 7, name: "No-deal",           formula: "client < payout/(1−m) → the engagement does not happen",       plain: "Nobody is squeezed below their own rate to make a margin work.",                                           source: "PRICING.md §8", url: "https://github.com/welance/perfect-brief/blob/main/docs/pricing/PRICING.md#8-the-no-deal-rule" },
    { id: "team",     n: 8, name: "The team equation", formula: "R = payouts + headroom + geo differential + margin",   plain: "One blended client rate, decomposed into four visible bands that must sum exactly.",                       source: "spec §5", url: "https://github.com/welance/perfect-brief/blob/main/site/pricing.js#L101" }
  ];

  var API = {
    LEVELS: LEVELS, STEPS: STEPS, INTERNAL_MAX: INTERNAL_MAX,
    COUNTRIES: COUNTRIES,
    share: share, marginOf: marginOf,
    agreed: agreed, coverageOf: coverageOf, levelFor: levelFor,
    applyCol: applyCol, minClientRate: minClientRate,
    computeTeam: computeTeam,
    FORMULAS: FORMULAS
  };

  if (typeof module !== "undefined" && module.exports) module.exports = API;
  root.WelancePricing = API;
})(typeof self !== "undefined" ? self : globalThis);
