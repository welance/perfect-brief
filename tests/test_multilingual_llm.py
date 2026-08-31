"""llm-only: the judge's language guarantee.

The same brief (fixture 0003-accepted) translated into the seven other site
languages must reach the SAME gate decision and a score within TOLERANCE of
the English reference — judged live by the real LLM judge, temperature 0.

Not part of offline CI (`make test`): needs PB_ANTHROPIC_API_KEY. Run with
`make test-llm-multilingual`. See brief_bar/fixtures/multilingual/README.md.
"""

import glob
import os

import pytest
import yaml

from brief_bar import aggregate, llm, load_bundled, loader

pytestmark = pytest.mark.skipif(
    not os.environ.get("PB_ANTHROPIC_API_KEY"),
    reason="llm-only: the multilingual guarantee needs a real judge",
)

TOLERANCE = 10  # declared: same gate, score within 10 points of English

RULES, CFG = load_bundled()
ML_DIR = os.path.join(loader.fixtures_dir(), "multilingual")
LANGS = sorted(
    os.path.splitext(os.path.basename(p))[0]
    for p in glob.glob(os.path.join(ML_DIR, "*.yaml"))
    if not p.endswith("en.yaml")
)


def _load(lang: str) -> str:
    with open(os.path.join(ML_DIR, f"{lang}.yaml")) as fh:
        return yaml.safe_load(fh)["input"]


def _judge_live(brief: str):
    """One batched judge call, exactly like the service: temperature 0."""
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
    return aggregate(verdicts, RULES, CFG)


@pytest.fixture(scope="module")
def english_reference():
    return _judge_live(_load("en"))


@pytest.mark.parametrize("lang", LANGS)
def test_same_brief_same_decision(lang, english_reference):
    ref = english_reference
    got = _judge_live(_load(lang))
    assert got.decision == ref.decision, (
        f"{lang}: decision {got.decision!r} != en {ref.decision!r}"
    )
    assert got.gate_passed == ref.gate_passed, (
        f"{lang}: gate {got.gate_passed} != en {ref.gate_passed}"
    )
    assert abs(got.score - ref.score) <= TOLERANCE, (
        f"{lang}: score {got.score} vs en {ref.score} — beyond ±{TOLERANCE}"
    )
