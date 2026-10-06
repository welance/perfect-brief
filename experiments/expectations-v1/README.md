# Expectations rules experiment

Status: local experiment, 2026-10-06. The bundled service still uses fourteen
rules. This overlay applies the three candidate criteria agreed for testing;
it is not a released policy change.

## Changes under test

- `scope-boundaries` version 3 distinguishes the current engagement from options,
  future phases and decisions still to agree. Breadth alone does not cause failure.
- `assumptions-risks` version 3 connects decisive assumptions stated in the text
  to their verification and the commitments that depend on them.
- `scope-resource-alignment` version 1 distinguishes binding, indicative and
  unresolved scope, budget and dates, including assessment before commitment.
  It does not estimate implementation cost or enforce a marketplace price floor.

The YAML files in [rules](rules/) contain the exact criteria and examples.
The existing batched judge prompt reads their criteria; weights remain invisible
to the model. References are empty for this experimental overlay: these are
product hypotheses, not independently sourced normative claims ready to merge.

## Weighting fixed before evaluation

The existing rules total 100 points. The two revised criteria retain their
original weights for the first calculation. For a second calculation, the new
rule receives 10 points and all fourteen existing weights are multiplied by 0.9.
Thus the candidate totals 100 without selectively weakening a competing rule.
This is a test allocation, not an empirically validated weighting decision.

No gate or threshold changes. Directory anonymity and budget policy retain their
context tags and deactivate together in generic scoring. There is no additional
score cap: the current deterministic aggregation applies throughout.

## Running and interpreting the comparison

From the repository root, `experiments.expectations_v1.load_variant()` returns
the baseline rules, the fourteen rules with two criteria revised, the weighted
fifteen-rule candidate and the unchanged scoring configuration.

Use `brief_bar.llm.render_judge_prompt(candidate, text, cfg.budget_floor)` with
the same source text, model and sampling settings as the baseline. Submit that
prompt to the configured provider with the usual output ceiling. Neither a
summary nor a selected excerpt is a full-document comparison.

`experiments.expectations_v1.evaluate(raw_json_array, source_text)` validates
all fifteen verdicts and their evidence with the current strict parser, then
returns both calculations in Directory and generic contexts. The experiment
identifier combines a prerelease label, baseline version and a content hash of
the overlay and evaluation code.

Both candidate calculations use the same fifteen-rule model response, removing
the new rule for the calculation with original weights. This isolates the
arithmetic effect of adding and reweighting the rule within that response; it
does not isolate the effect of changing the prompt on the model. Compare all
fourteen shared verdicts to the saved baseline, including unchanged criteria,
and report any drift. One before/after run is not a repeatability study.

Private source text, provider responses and evidence-bearing reports stay outside
this repository. Keep application verdict caching disabled. Provider prompt
caching is a separate mechanism and may still appear in usage metadata.

## Checks before adoption

`tests/test_expectations_experiment.py` checks schema validity, the declared
changes, weight conservation, context behaviour and rejection of incomplete
verdicts. These are mechanics checks, not a semantic validation of the criteria.

Before adopting the overlay, evaluate the criteria's examples and controlled
variants from the [audit](../../docs/critique/expectations-rule-audit.md), including
legitimate fixed constraints, supplier pricing requests and discovery engagements.
Record expected judgements before collecting model results and retain failures.
An eventual release also requires the existing contribution and governance
process, fixture calibration, and updates to the mock, suggestions and consumers.
The overlay is deliberately outside the bundled package to keep these remaining
adoption steps visible.
