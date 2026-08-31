# Multilingual fixtures — the judge's language guarantee

The same brief (fixture `0003-accepted`), faithfully translated into the
seven other site languages. `en.yaml` is the reference.

**The claim these fixtures prove:** the judge grades meaning, not language.
A brief in any of the site's languages must reach the **same gate decision**
and a **score within ±10 points** of the English reference — judged live,
by the real LLM judge, both runs at temperature 0.

- These do **not** run in offline CI (`make test`): they need a real judge
  and a key. Run them with `make test-llm-multilingual`
  (`PB_ANTHROPIC_API_KEY` required; `PB_MODEL` optional).
- Re-run this suite whenever the ruleset or the judge prompt changes — it
  is the standing proof, not a one-off check.
- The offline MockJudge is English-only by design; the console says so
  in every non-English locale instead of showing false fails.
- Translations are machine-drafted. A native speaker improving one only
  makes the guarantee stronger — plain PRs welcome, one file per language.
