// Deterministic spans and cues from the shared pattern catalogue — the
// JavaScript half of brief_bar/patterns/__init__.py. Same contract, held to
// it by the dual-engine harness (python -m experiments.pattern_harness):
//
//   1. Every contact pattern runs over the ORIGINAL text. Group 1, when
//      present, is the span and ends where the match ends.
//   2. A phone candidate outside its digit limits is dropped. An exclusion
//      (amount, range, date, tax id, IBAN...) drops it only when it covers
//      the whole candidate and carries no other digits; patterns with
//      never_excluded_from_digits are never dropped by one (fail closed).
//   3. Overlaps resolve by priority, then the longer span, then the earlier
//      start, then the pattern id. Spans come back in document order.
//   4. Keyword cues are lowercase substrings of the lowercased text.
//
// Offsets are native string indexes (UTF-16 code units). Vendored unchanged
// by consumers; no dependencies, no network, no LLM.

export function compileCatalogue(catalogue) {
  const rx = (e) => new RegExp(e.source, (e.flags || '') + 'g')
  return {
    version: catalogue.version,
    contacts: catalogue.contacts.map((e) => ({ ...e, re: rx(e) })),
    exclusions: catalogue.exclusions.map((e) => ({ ...e, re: rx(e) })),
    keywords: catalogue.keywords,
  }
}

function* matches(re, text) {
  re.lastIndex = 0
  let m
  while ((m = re.exec(text))) {
    if (m[0].length === 0) {
      re.lastIndex++
      continue
    }
    const end = m.index + m[0].length
    const start = m[1] !== undefined ? end - m[1].length : m.index
    yield [start, end]
  }
}

const digits = (s) => (s.match(/[0-9]/g) || []).length

export function exclusionSpans(compiled, text) {
  const out = []
  for (const e of compiled.exclusions)
    for (const [s, end] of matches(e.re, text)) out.push([s, end, e.id])
  return out
}

function isExcluded(e, s, end, text, excluded) {
  const n = digits(text.slice(s, end))
  if (e.never_excluded_from_digits !== undefined && n >= e.never_excluded_from_digits) return false
  return excluded.some(([xs, xe]) => xs <= s && end <= xe && digits(text.slice(xs, xe)) === n)
}

export function contactSpans(compiled, text) {
  const t = text || ''
  const excluded = exclusionSpans(compiled, t)
  const cands = []
  for (const e of compiled.contacts) {
    for (const [s, end] of matches(e.re, t)) {
      if (e.min_digits !== undefined) {
        const n = digits(t.slice(s, end))
        if (n < e.min_digits || n > e.max_digits) continue
      }
      if (e.kind === 'phone' && isExcluded(e, s, end, t, excluded)) continue
      cands.push({ e, s, end })
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
