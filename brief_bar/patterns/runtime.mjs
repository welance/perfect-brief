// Deterministic spans and cues from the shared pattern catalogue — the
// JavaScript half of brief_bar/patterns/__init__.py. Same contract, held to
// it by the dual-engine harness (python -m experiments.pattern_harness):
//
//   1. Every contact pattern runs over the ORIGINAL text. Group 1, when
//      present, is the span and ends where the match ends.
//   2. A phone candidate is valid when its digit count is within limits and
//      no exclusion hides it. An exclusion hides it only when it covers the
//      whole candidate and carries no other digits. never_excluded_from_digits
//      patterns are never hidden; hidden_only_by_structural ones yield only
//      to structural exclusions (dates, tax ids, IBANs). An invalid candidate
//      BACKS OFF to its longest prefix, cut where a digit run ends, that the
//      pattern still matches exactly and that is valid (fail closed).
//   3. Overlaps resolve by priority, then the longer span, then the earlier
//      start, then the pattern id. Spans come back in document order.
//   4. Keyword cues are lowercase substrings of the lowercased text.
//   5. Subject spans say WHERE the text already states a subject (a
//      budget-labelled amount or range, a timeline-labelled duration). Group 1
//      is the value, without its label. Presence only: no floor, no verdict.
//      Overlaps resolve by the longer span, then the earlier start, then the
//      pattern id. Spans come back in document order.
//
// Offsets are native string indexes (UTF-16 code units). Vendored unchanged
// by consumers; no dependencies, no network, no LLM.

export function compileCatalogue(catalogue) {
  const rx = (e, f) => new RegExp(e.source, (e.flags || '') + f)
  return {
    version: catalogue.version,
    contacts: catalogue.contacts.map((e) => ({ ...e, re: rx(e, 'g'), sticky: rx(e, 'y') })),
    exclusions: catalogue.exclusions.map((e) => ({ ...e, re: rx(e, 'g') })),
    keywords: catalogue.keywords,
    subjects: (catalogue.subjects || []).map((e) => ({ ...e, re: rx(e, 'g') })),
  }
}

// [start, end] of group 1 (a suffix of the match) or of the whole match
const spanOf = (m) => {
  const end = m.index + m[0].length
  return [m[1] !== undefined ? end - m[1].length : m.index, end]
}

function* matches(re, text) {
  re.lastIndex = 0
  let m
  while ((m = re.exec(text))) {
    if (m[0].length === 0) {
      re.lastIndex++
      continue
    }
    yield m
  }
}

const digits = (s) => (s.match(/[0-9]/g) || []).length
const isDigit = (ch) => ch >= '0' && ch <= '9'

export function exclusionSpans(compiled, text) {
  const out = []
  for (const e of compiled.exclusions)
    for (const m of matches(e.re, text)) out.push([...spanOf(m), !!e.structural])
  return out
}

function isHidden(e, s, end, text, excluded) {
  const n = digits(text.slice(s, end))
  if (e.never_excluded_from_digits !== undefined && n >= e.never_excluded_from_digits) return false
  return excluded.some(
    ([xs, xe, structural]) =>
      xs <= s &&
      end <= xe &&
      digits(text.slice(xs, xe)) === n &&
      (structural || !e.hidden_only_by_structural)
  )
}

function isValid(e, s, end, text, excluded) {
  if (e.min_digits !== undefined) {
    const n = digits(text.slice(s, end))
    if (n < e.min_digits || n > e.max_digits) return false
  }
  return !(e.kind === 'phone' && isHidden(e, s, end, text, excluded))
}

// the longest valid prefix of a match, cut where a digit run ends
function backOff(e, m, text, excluded) {
  const [s, end] = spanOf(m)
  if (isValid(e, s, end, text, excluded)) return [s, end]
  if (e.min_digits === undefined) return null
  for (let k = end - 1; k > s; k--) {
    if (!isDigit(text[k - 1]) || isDigit(text[k])) continue
    e.sticky.lastIndex = m.index
    const mm = e.sticky.exec(text.slice(0, k))
    if (!mm) continue
    const [ms, me] = spanOf(mm)
    if (ms === s && me === k && isValid(e, s, k, text, excluded)) return [s, k]
  }
  return null
}

export function contactSpans(compiled, text) {
  const t = text || ''
  const excluded = exclusionSpans(compiled, t)
  const cands = []
  for (const e of compiled.contacts) {
    for (const m of matches(e.re, t)) {
      const kept = backOff(e, m, t, excluded)
      if (kept) cands.push({ e, s: kept[0], end: kept[1] })
    }
  }
  const cmpId = (a, b) => (a < b ? -1 : a > b ? 1 : 0)
  cands.sort(
    (a, b) =>
      b.e.priority - a.e.priority ||
      b.end - b.s - (a.end - a.s) ||
      a.s - b.s ||
      cmpId(a.e.id, b.e.id)
  )
  const kept = []
  for (const c of cands)
    if (!kept.some((k) => c.s < k.end && c.end > k.s)) kept.push(c)
  kept.sort((a, b) => a.s - b.s)
  return kept.map(({ e, s, end }) => ({
    kind: e.kind,
    start: s,
    end,
    text: t.slice(s, end),
    pattern: e.id,
  }))
}

export function keywordHits(compiled, text, group) {
  const t = (text || '').toLowerCase()
  return compiled.keywords[group].filter((k) => t.includes(k))
}

export function subjectSpans(compiled, text) {
  const t = text || ''
  const cands = []
  for (const e of compiled.subjects || [])
    for (const m of matches(e.re, t)) {
      const [s, end] = spanOf(m)
      cands.push({ e, s, end })
    }
  const cmpId = (a, b) => (a < b ? -1 : a > b ? 1 : 0)
  cands.sort((a, b) => b.end - b.s - (a.end - a.s) || a.s - b.s || cmpId(a.e.id, b.e.id))
  const kept = []
  for (const c of cands)
    if (!kept.some((k) => c.s < k.end && c.end > k.s)) kept.push(c)
  kept.sort((a, b) => a.s - b.s)
  return kept.map(({ e, s, end }) => ({
    subject: e.subject,
    start: s,
    end,
    text: t.slice(s, end),
    pattern: e.id,
  }))
}
