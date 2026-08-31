"""llm-only: the anonymised rule judges identity, not specificity.

The rule is a hard gate, so a false positive there blocks a publishable
brief outright. Two failure modes seen in the wild, both on non-English
briefs, both fixed by the criteria written in `rules/anonymised.yaml@2`:

  1. naming the compliance regime (GDPR/AVG/DSGVO, WCAG, HACCP) was read as
     naming a brand — while `data-compliance` was rewarding the same words;
  2. describing the business concretely (sector, size, volumes) was read as
     "company details", though every other rule asks for exactly that.

MockJudge cannot exercise a prompt change, so this suite is live like the
multilingual one. Run with `make test-llm-multilingual` or plain pytest with
PB_ANTHROPIC_API_KEY set.
"""

import os

import pytest

from brief_bar import Status, llm, load_bundled

pytestmark = pytest.mark.skipif(
    not os.environ.get("PB_ANTHROPIC_API_KEY"),
    reason="llm-only: judging identity needs a real judge",
)

RULES, CFG = load_bundled()

# Danish, deliberately concrete about the operation, and it names GDPR and
# WCAG because the ruleset asks it to. Nothing here identifies the writer.
SPECIFIC_BUT_BLIND = """
# Sporing af returemballage i distribution af kølevarer

Vi distribuerer kølevarer og kører knap 40 daglige ruter fra to lagre ud til
omkring tusind butikker og storkøkkener. Rullecontainere og europaller kommer
kun delvist retur, og sidste år købte vi 4.000 nye, fordi vi ikke kan gøre rede
for, hvor de står. Chaufføren noterer udvekslet emballage i hånden.

Omfang: registrering på terminalen ved levering, kvittering fra modtageren, og
en selvbetjeningsoversigt per kunde. Uden for omfang: ruteplanlægning og
fakturering. Modtagerens navn og underskrift er personoplysninger og behandles
efter GDPR med en bevaringsfrist på 24 måneder. Selvbetjeningsoversigten skal
opfylde WCAG 2.1 AA. Budget 35.000-55.000 EUR over fire måneder, med to
udviklere og en designer.
"""

# The same shape, but a reader can name the company, the person and the town.
IDENTIFYING = """
# Sporing af returemballage hos Nordkøl A/S

Vi er Nordkøl A/S i Hjørring. Logistikchef Mette Sørensen (mette@nordkoel.dk,
+45 30 11 22 33) ejer processen, og vores kunde Fakta afviser vores tal.

Omfang: registrering på terminalen ved levering. Budget 35.000-55.000 EUR over
fire måneder. Personoplysninger behandles efter GDPR.
"""


def _anonymised(brief: str):
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["PB_ANTHROPIC_API_KEY"])
    model = os.environ.get("PB_MODEL", "deepseek/deepseek-v4-pro")
    prompt = llm.render_judge_prompt(RULES, brief, CFG.budget_floor)
    msg = client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    verdicts = llm.parse_judge(RULES, msg.content[0].text)
    return next(v for v in verdicts if v.rule_id == "anonymised")


def test_specific_and_compliant_brief_is_anonymised():
    v = _anonymised(SPECIFIC_BUT_BLIND)
    assert v.status is Status.PASS, (
        f"a blind brief was blocked: {v.note!r} (quote: {v.quote!r})"
    )


def test_named_company_and_person_still_fails():
    v = _anonymised(IDENTIFYING)
    assert v.status is Status.FAIL, "a brief naming the company and a person passed"
