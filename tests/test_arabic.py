"""Arabic pregroup pre-formalizer: deterministic NL -> Lean for the math fragment."""

from __future__ import annotations

import json

import pytest
from conftest import FakeRunner, ScriptedModel

from falconverifier import arabic
from falconverifier.agent import VerifyAndTeachAgent
from falconverifier.schemas import Verdict
from falconverifier.student import parse_answer


def test_script_detection_and_digits():
    assert arabic.is_arabic("ما هو ناتج ١٧ × ٢٣؟")
    assert not arabic.is_arabic("What is 17 * 23?")
    assert arabic.normalize_digits("٣٬٥٠٠٫٢٥٪") == "3500.25%"


@pytest.mark.parametrize(
    "text, prop",
    [
        ("١٧ × ٢٠ = ٣٤٠", "(17:ℚ) * 20 = (340:ℚ)"),
        ("17 ضرب 20 يساوي 340", "(17:ℚ) * 20 = (340:ℚ)"),
        ("مجموع ٣٤٠ و ٥١ هو ٣٩١", "(340:ℚ) + 51 = (391:ℚ)"),
        ("ناتج ضرب 17 في 23 هو 391.", "(17:ℚ) * 23 = (391:ℚ)"),
        ("٥٠٪ من ١٥٠ يساوي ٧٥", "(50:ℚ) / 100 * 150 = (75:ℚ)"),
        ("نصف 40 هو 20", "(40:ℚ) / 2 = (20:ℚ)"),
        ("ثلث 90 هو 30", "(90:ℚ) / 3 = (30:ℚ)"),
        ("مربع 7 هو 49", "(7:ℚ) ^ 2 = (49:ℚ)"),
        ("12 يقبل القسمة على 3", "(3:ℤ) ∣ (12:ℤ)"),
        ("١٣ لا يقبل القسمة على ٣", "¬ ((3:ℤ) ∣ (13:ℤ))"),
        ("٧ أكبر من ٥", "(7:ℚ) > (5:ℚ)"),
        ("١٠٠ ناقص ٣٥ يساوي ٦٥", "(100:ℚ) - 35 = (65:ℚ)"),
        ("(3 + 4) × 2 = 14", "((3:ℚ) + 4) * 2 = (14:ℚ)"),
        ("ضعف مجموع 3 و 4 هو 14", "2 * ((3:ℚ) + 4) = (14:ℚ)"),
        ("٢٠٠ ناقص ٢٠٪ من ٢٠٠ يساوي ١٦٠", "(200:ℚ) - 20 / 100 * 200 = (160:ℚ)"),
        ("إذن 340 + 51 = 391", "(340:ℚ) + 51 = (391:ℚ)"),
    ],
)
def test_declarative_fragment(text, prop):
    hit = arabic.formalize_step(text)
    assert hit is not None, text
    assert hit[0] == prop
    assert hit[1].endswith("→ s")


def test_prefix_head_scopes_over_whole_phrase():
    """«ناتج ١٧ × ٢٣» — the head's nˡ must link to the operator output, not the first literal.

    Greedy left-to-right contraction gets this wrong; the planar-matching search does not."""
    p = arabic.parse("ما هو ناتج ١٧ × ٢٣؟")
    assert p is not None and p.result_type == "q"
    assert p.lean_prop == "(17:ℚ) * 23"
    assert arabic.formalize_problem("ما هو ناتج ١٧ × ٢٣؟", "٣٩١")[0] == "(17:ℚ) * 23 = 391"
    assert arabic.formalize_problem("كم يساوي ٥٠٪ من ١٥٠؟", "الجواب 75")[0] == (
        "(50:ℚ) / 100 * 150 = 75"
    )


def test_outside_fragment_falls_back():
    assert arabic.formalize_step("أحمد كتب الدرس") is None
    assert arabic.formalize_step("كل المربعات مستطيلات") is None
    assert arabic.formalize_step("١٧ × ٢٠ = ٣٤٠ = 5") is None  # two heads: no single-s reduction
    assert arabic.formalize_problem("إذا كان لدى أحمد ٣ صناديق ...", "31") is None


def test_arabic_answer_parsing():
    steps, final = parse_answer(
        "الخطوة ١: 17 × 20 = 340\nالخطوة 2: 17 × 3 = 51\nالخطوة 3: 340 + 51 = 391\n"
        "الجواب النهائي: ٣٩١."
    )
    assert [s.index for s in steps] == [1, 2, 3]
    assert steps[0].text == "17 × 20 = 340"
    assert final == "391"


AR_PROBLEM = "ما هو ناتج ١٧ × ٢٣؟"
AR_WRONG = (
    "الخطوة 1: 17 × 20 = 340\nالخطوة 2: 17 × 3 = 51\nالخطوة 3: 340 + 51 = 381\nالجواب النهائي: 381"
)
AR_RIGHT = (
    "الخطوة 1: 17 × 20 = 340\nالخطوة 2: 17 × 3 = 51\nالخطوة 3: 340 + 51 = 391\nالجواب النهائي: 391"
)
TABLE = {
    "(17:ℕ) * 20 = 340": Verdict.VERIFIED,
    "(17:ℕ) * 3 = 51": Verdict.VERIFIED,
    "(340:ℕ) + 51 = 381": Verdict.REFUTED,
    "(340:ℕ) + 51 = 391": Verdict.VERIFIED,
    "(17:ℕ) * 23 = 381": Verdict.REFUTED,
    "(17:ℕ) * 23 = 391": Verdict.VERIFIED,
}


def test_arabic_loop_is_fully_deterministic(settings):
    """Whole conversation inside the fragment: zero formalizer-LLM calls, Arabic feedback."""
    student = ScriptedModel([AR_WRONG, AR_RIGHT])
    formalizer = ScriptedModel([])  # any call would raise IndexError
    agent = VerifyAndTeachAgent(
        settings, student_model=student, formalizer_model=formalizer, runner=FakeRunner(TABLE)
    )
    trace = agent.run(AR_PROBLEM, expected_answer="391")
    assert trace.status == "verified" and trace.final_answer == "391"
    r1 = trace.rounds[0]
    assert r1.formalization.raw == "pregroup"
    assert all(fs.note.startswith("pregroup:") for fs in r1.formalization.steps)
    assert r1.report.steps[2].verdict == Verdict.REFUTED
    assert r1.feedback and "الخطوة 3" in r1.feedback and "خاطئة" in r1.feedback
    # the student was addressed in Arabic on the revision turn
    assert "Lean 4" in student.calls[1][-1]["content"] and "صحّح" in student.calls[1][-1]["content"]


def test_arabic_mixed_fragment_uses_llm_only_for_the_rest(settings):
    student = ScriptedModel(
        ["الخطوة 1: 17 × 23 = 391\nالخطوة 2: إذن عدد التفاحات هو 391\nالجواب النهائي: 391"]
    )
    llm = json.dumps(
        {
            "problem_prop": "(17:ℕ) * 23 = 391",
            "steps": [
                {"index": 1, "kind": "arith", "lean_prop": "(1:ℕ) = 2"},  # overridden by grammar
                {"index": 2, "kind": "skip", "lean_prop": None},
            ],
        }
    )
    formalizer = ScriptedModel([llm])
    agent = VerifyAndTeachAgent(
        settings, student_model=student, formalizer_model=formalizer, runner=FakeRunner(TABLE)
    )
    trace = agent.run("كم تفاحة في ١٧ صندوقاً في كل منها ٢٣ تفاحة؟", max_rounds=1)
    form = trace.rounds[0].formalization
    assert form.steps[0].lean_prop == "(17:ℚ) * 23 = (391:ℚ)"
    assert form.steps[0].note.startswith("pregroup:")
    assert form.steps[1].kind == "skip"
    assert trace.status == "verified"


def test_agreement_features_reject_what_bare_types_accept():
    """Python twin of Lean's coarse_accepts_bad_agreement / indexed_rejects_bad_agreement."""
    assert arabic.formalize_step("العدد ١٢ يساوي ١٢")[0] == "(12:ℚ) = (12:ℚ)"  # masc/masc
    assert arabic.formalize_step("النتيجة ١٢ تساوي ١٢")[0] == "(12:ℚ) = (12:ℚ)"  # fem/fem
    assert arabic.formalize_step("العدد ١٢ تساوي ١٢") is None  # masc noun, fem verb
    assert arabic.formalize_step("النتيجة ١٢ يساوي ١٢") is None  # fem noun, masc verb
    # bare numerals carry no gender feature, so either verb form is accepted
    assert arabic.formalize_step("١٢ تساوي ١٢") is not None


def test_arabic_yes_no_grading_is_not_vacuous():
    from falconverifier.bench import answers_match

    assert answers_match("نعم", "نعم")
    assert answers_match("لا", "لا")
    assert not answers_match("نعم", "لا")
    assert not answers_match("لا", "نعم")
    assert answers_match("لا، غير صحيح", "لا")
    assert not answers_match("غير صحيح", "نعم")
    assert answers_match("٣٩١", "391")
    assert not answers_match("شيء آخر", "لا")


def test_long_decimal_equality_is_read_as_approximate():
    from fractions import Fraction

    from falconverifier.arabic import _fmt, formalize_step

    prop, _ = formalize_step("387 ÷ 19 = 20.368421052631578")
    assert "20.368421052631578" in prop and "< (1 / 10 ^ 14 : ℚ)" in prop and "∧" in prop
    prop, _ = formalize_step("٣٨٧ ÷ ١٩ = ٢٠٫٥")
    assert prop == "(387:ℚ) / 19 = (20.5:ℚ)"
    assert _fmt(Fraction("20.368421052631578")) == "20.368421052631578"
    assert _fmt(Fraction(1, 3)) == "(1 / 3)"


SYLLOGISM = "كل المربعات مستطيلات، وكل المستطيلات أشكال رباعية. هل يلزم أن كل المربعات أشكال رباعية؟ أجب بنعم أو لا."
UNDISTRIBUTED = (
    "كل الأطباء متعلمون، وبعض المتعلمين فقراء. هل يلزم أن بعض الأطباء فقراء؟ أجب بنعم أو لا."
)
AFFIRM_CONSEQUENT = "إذا أمطرت فإن الأرض تبتل. الأرض مبتلة. هل يلزم أنها أمطرت؟ أجب بنعم أو لا."
DISJ_SYLLOGISM = (
    "إما أن يكون المفتاح في الحقيبة أو في السيارة. المفتاح ليس في الحقيبة. "
    "هل يلزم أنه في السيارة؟ أجب بنعم أو لا."
)
ORDER = "عمر أطول من يوسف، وعمر أطول من خالد. هل يلزم أن يوسف أطول من خالد؟ أجب بنعم أو لا."
NAMED = "كل الطلاب في الصف يتكلمون العربية، وسلطان طالب في الصف. هل يلزم أن سلطان يتكلم العربية؟ أجب بنعم أو لا."


def test_arabic_logic_fragment_syllogisms_and_certificates():
    from falconverifier.arabic_logic import formalize_logic_problem

    prop, cert = formalize_logic_problem(SYLLOGISM)
    assert prop == (
        "∀ (A B C : Fin 3 → Bool), (∀ x, A x = true → B x = true) → "
        "(∀ x, B x = true → C x = true) → (∀ x, A x = true → C x = true)"
    )
    assert "B := مستطيلات ≡ المستطيلات" in cert  # the morphological identification is explicit

    prop, _ = formalize_logic_problem(UNDISTRIBUTED)
    assert "(∃ x, B x = true ∧ C x = true) → (∃ x, A x = true ∧ C x = true)" in prop

    prop, cert = formalize_logic_problem(NAMED)
    assert prop == (
        "∀ (A B : Fin 3 → Bool) (c0 : Fin 3), (∀ x, A x = true → B x = true) → "
        "A c0 = true → B c0 = true"
    )
    assert "A := الطلاب في الصف ≡ طالب في الصف" in cert and "c0 := سلطان" not in cert


def test_arabic_logic_fragment_propositional_and_order():
    from falconverifier.arabic_logic import formalize_logic_problem

    prop, _ = formalize_logic_problem(AFFIRM_CONSEQUENT)
    assert prop == "∀ (P Q : Bool), (P = true → Q = true) → Q = true → P = true"
    prop, _ = formalize_logic_problem(DISJ_SYLLOGISM)
    assert prop == "∀ (P Q : Bool), (P = true ∨ Q = true) → P = false → Q = true"
    prop, _ = formalize_logic_problem(ORDER)
    assert prop == "∀ (v0 v1 v2 : Fin 4), v0 > v1 → v0 > v2 → v1 > v2"


def test_arabic_logic_fragment_refuses_gaps():
    from falconverifier.arabic_logic import formalize_logic_problem

    # conclusion predicate («عدد أولي») is not identified with any premise: no verdict
    assert (
        formalize_logic_problem(
            "كل الأعداد الأولية الأكبر من ٢ فردية، و٩ فردي. هل يلزم أن ٩ عدد أولي؟ أجب بنعم أو لا."
        )
        is None
    )
    # arithmetic content inside "propositions" is not a propositional variable
    assert (
        formalize_logic_problem(
            "إذا كان العدد زوجياً فإنه يقبل القسمة على ٢. العدد ١٨ زوجي. "
            "هل يلزم أن ١٨ يقبل القسمة على ٢؟ أجب بنعم أو لا."
        )
        is None
    )
    assert formalize_logic_problem("ما هو ناتج ١٧ × ٢٣؟") is None


def test_logic_fragment_polarity_is_aligned_with_the_answer():
    from falconverifier.arabic_logic import formalize_logic_problem
    from falconverifier.formalizer import align_polarity

    prop, _ = formalize_logic_problem(UNDISTRIBUTED)
    assert align_polarity(prop, "نعم") == prop
    assert align_polarity(prop, "لا") == f"¬ ({prop})"
