# Rule coverage of expectations and open decisions

Date: 2026-10-06

Status: Audit of current criteria and proposed evaluation plan. No rule, weight,
gate, prompt or fixture expectation changes are made by this audit.

The [product direction](../decisions/0003-brief-expectations.md) asks whether a
brief enables an informed discussion between client and supplier. The current
rules cover several foundations well, but often accept the presence of an item
without distinguishing its meaning, certainty or negotiability. Some criteria
also penalise legitimate delegation of decisions to a supplier.

## Coverage of the current rules

The observations below concern the criteria in `brief_bar/rules/`. They are not
measured LLM verdicts. Proposed directions require evaluation before adoption.

| Rule | Current contribution | Gap or boundary | Proposed direction |
| --- | --- | --- | --- |
| `clear-title` | Makes the subject findable and scannable. | A title says little about the engagement being requested. | Retain its narrow purpose; do not turn it into a general comprehension test. |
| `problem-defined` | Separates a user problem from a proposed solution. | Naming a problem does not establish whether the proposed solution is mandatory. | Retain the problem test; examine solution status under technical constraints. |
| `users-identified` | Names a user segment and context. | Users are not necessarily the client decision maker or acceptance owner. | Retain the user test; examine responsibilities separately. |
| `success-metrics` | Makes the desired outcome measurable. | A target can be mistaken for a guaranteed result or an established baseline. | Test whether material outcome assumptions are visible; accept a stated plan to establish a baseline. |
| `scope-boundaries` | Accepts an explicit exclusion or clear boundary. | One exclusion need not clarify what is being commissioned, optional or deferred. | Test whether the requested engagement is bounded; priorities are useful when they resolve a real scope question. |
| `deliverables-concrete` | Requires observable acceptance conditions for each deliverable. | Concrete outputs do not establish agreement, feasibility or who accepts them. | Preserve verifiability; calibrate to the engagement, including discovery deliverables. |
| `budget-floor` | Checks a stated amount against Directory policy. | Does not distinguish budget from quote, its coverage or flexibility; disappears entirely in generic context. | Separate the question of economic clarity from the marketplace minimum in a later evidence-backed design. |
| `timeline` | Requires a concrete timeframe, deadline or milestone. | Does not distinguish binding dates, targets and dependencies. | Test the status of the schedule and how unresolved dependencies affect it. |
| `team-shape` | Signals roles, skills, size or duration for matching. | Does not cover client contributions or decisions; may encourage clients to invent staffing needs. | Test capability needs and explicit requests for supplier advice before requiring a team composition. |
| `constraints-tech` | Requires a stack, platform, integration or environment constraint. | Its fail example is explicit technical flexibility; it can reward arbitrary prescription. | First evaluation target: distinguish a real constraint, a preference and a choice deliberately delegated. |
| `assumptions-risks` | Accepts at least one substantive assumption or risk. | A single risk can coexist with many implicit commitments; a resolution path is not required. | Test material unknowns and the decisions they affect without demanding an exhaustive risk register. |
| `data-compliance` | Names a regime when the product handles personal data. | Naming a regime does not establish responsibilities or actual compliance. | Keep claims bounded; test known data use and open responsibility questions. |
| `accessibility-considered` | Names an accessibility expectation for a user-facing product. | Naming a standard alone need not explain the expected acceptance evidence. | Test clarity of the expectation and its verification at the appropriate engagement stage. |
| `anonymised` | Protects blind publication in the Directory. | Publication anonymity cannot demonstrate shared expectations. | Retain the explicit Directory context; do not infer general brief quality from anonymity. |

## Gaps that cross rule boundaries

**Status of statements.** Budgets, dates, technologies and outputs may all be
present while readers cannot tell which are requirements, preferences,
assumptions or questions. Additional detail alone does not close this gap.

**Responsibilities.** Skills needed from a supplier and end-user descriptions
do not identify who supplies access, content, domain decisions or acceptance.
These can be roles rather than personal names, including in blind publication.

**Coherence.** Separate passing statements can imply conflicting expectations.
A question about whether scope fits a fixed budget is useful evidence of an open
decision. Budget divided by a reference rate is only an assumed time allowance;
it cannot prove that the scope is feasible or infeasible.

**Accessible meaning.** The reader should be able to find the requested outcome,
engagement boundaries and open questions without reconstructing them from many
attachments. A word limit or a count of technical terms is not a quality proxy.

No new global penalty or composite score is specified here. Evaluation must
establish whether existing criteria can cover these gaps without double-counting.

## Controlled examples for evaluation

Start with one shared synthetic brief and replace only the relevant passage.
The examples below are evaluation designs, not labelled corpus fixtures and not
transpositions of private client material. They carry no expected numeric score.

| Dimension | Ambiguous or weaker passage | Clearer passage | What the comparison tests |
| --- | --- | --- | --- |
| Budget status | “Budget: €24,000.” | “€24,000 is our ceiling for the initial build. Please assess which requested outcomes fit before we agree the scope.” | Meaning and coverage of the same amount, without an invented quote. |
| Technical choice | “Use PostgreSQL.” | “PostgreSQL is our preference; there is no existing database dependency. Please propose alternatives if they better serve the outcome.” | Whether the same named technology is a requirement or a proposal. |
| Schedule status | “Launch on 1 June.” | “1 June is our preferred launch date; please assess it after confirming the integration access.” | Whether a date is understood as a target with a dependency. |
| Responsibility | “Import the catalogue.” | “We provide the catalogue export and resolve ambiguous product records; the supplier implements the import.” | Division of work without extra product functionality. |
| Open decision | “Integration access may be a risk.” | “Integration access is unconfirmed. Our operations lead will check it with the vendor before we agree delivery dates.” | A material unknown linked to an owner and a decision. |

Protect these legitimate counterexamples:

- A greenfield brief delegates technology selection, stating that there is no
  known existing-stack constraint and asking the supplier to assess options.
- A hard technical constraint has a reason, such as compatibility with an
  installed system; it should not be penalised merely for limiting choices.
- Fixed scope, budget and deadline are stated as conditions for supplier
  assessment. A ranking of features or willingness to cut them is not mandatory.
- A discovery engagement has research deliverables and acceptance conditions;
  its final build scope, architecture and price remain intentionally unresolved.
- A concise, concrete brief uses ordinary language rather than rubric headings.
- Adding repeated detail, a generic risk or a decorative priority list should
  not be sufficient to repair an unresolved expectation.

Changing several dimensions in one “improved” brief cannot identify which
criterion accounts for the difference. A controlled pair demonstrates a narrow
distinction, not general predictive validity or the client's understanding.

## Order of evaluation

1. Begin with `constraints-tech`: compare delegated choice, justified constraint
   and unsupported prescription while keeping the underlying project fixed.
   Record human expectations and reasons before examining judge outputs.
2. Record the baseline with the current criteria and actual LLM judge, including
   model, ruleset version, context, per-rule evidence and uncertainty. Keep mock
   results separate. If no provider is configured, record the missing baseline
   rather than substituting manual estimates for model results.
3. Test a narrowly revised existing criterion against those examples, protected
   counterexamples and the existing corpus. Include Italian and English cases;
   repeat model runs enough to expose inconsistent distinctions before adopting
   a criterion. Decide the evaluation procedure before selecting favourable runs.
4. Use the results to choose the next dimension: economic clarity, scope and
   tradeoffs, assumptions, or responsibilities. A new rule is warranted only if
   existing rules cannot explain a demonstrated gap without distorting their purpose.
5. For an adopted rule change, update criteria, examples, meaningful regressions
   and versioning under the existing governance. Check corresponding wizard
   questions and Directory messaging; downstream implementation remains separate
   work, not an automatic consequence of this audit.

The first experiment succeeds when the judge reliably recognises justified
constraints and deliberate delegation while identifying ambiguity, with evidence
in the text. A higher total score alone is insufficient. Material disagreement
between human reviewers is a reason to refine the criterion before rollout.

## Evidence and implementation boundaries

`tests/test_fixtures.py` uses `MockJudge`, whose keyword heuristics do not read
the YAML criteria as an LLM does. Editing criteria and making that test pass
would not establish that the deployed judge recognises the intended distinction.
Use those tests for regression of the mechanics and labelled mock behaviour;
evaluate semantic criteria with the actual judge and human review.

Private source documents and identifying practitioner accounts stay outside this
repository. Any public example must stand on its own and avoid identifiable
details. An internal anecdote can motivate a hypothesis; it does not by itself
prove a rule or a measured scoring failure.

Related foundations: [Contributing](../../CONTRIBUTING.md),
[Governance](../../GOVERNANCE.md), and the earlier
[critique of validity and consistency](CRITIQUE.md).
