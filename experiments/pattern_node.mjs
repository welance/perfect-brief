// The JavaScript engine for the pattern harness: runs brief_bar/patterns/
// runtime.mjs over {id: text} read from stdin and prints contact and subject
// spans with offsets in Unicode code points (Python's indexing), so the two
// engines compare 1:1.
//   node experiments/pattern_node.mjs <catalogue.json> < texts.json
import { readFileSync } from 'node:fs'
import {
  compileCatalogue,
  contactSpans,
  keywordHits,
  subjectSpans,
} from '../brief_bar/patterns/runtime.mjs'

const compiled = compileCatalogue(JSON.parse(readFileSync(process.argv[2], 'utf8')))
const texts = JSON.parse(readFileSync(0, 'utf8'))
const cp = (text, i) => [...text.slice(0, i)].length
const out = {}
for (const [id, text] of Object.entries(texts)) {
  const t0 = performance.now()
  const spans = contactSpans(compiled, text).map((s) => [s.kind, cp(text, s.start), cp(text, s.end), s.text])
  const subjects = subjectSpans(compiled, text).map((s) => [
    s.subject,
    cp(text, s.start),
    cp(text, s.end),
    s.text,
  ])
  out[id] = {
    spans,
    subjects,
    data: keywordHits(compiled, text, 'data').length > 0,
    compliance: keywordHits(compiled, text, 'compliance').length > 0,
    ms: performance.now() - t0,
  }
}
process.stdout.write(JSON.stringify(out))
