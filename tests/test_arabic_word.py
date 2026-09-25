"""Deterministic Arabic quantity narratives (arabic_word) → Lean arithmetic propositions."""

from __future__ import annotations

import pytest

from falconverifier import arabic_word
from falconverifier.arabic import formalize_problem

BOXES = (
    "اشترى سعيد ٩٣ علبة تحتوي كل منها على ٣٧ صندوقاً، ثم أعطى ٣٩١ صندوقاً من مجموعها "
    "لأصدقائه. كم صندوقاً بقي لدى سعيد؟"
)
DISCOUNT = (
    "يبلغ سعر هاتف 800 درهماً. خُفِّض بنسبة 10٪ ثم خُفِّض السعر الجديد بنسبة 20٪ أخرى. "
    "ما هو السعر النهائي بالدرهم؟"
)
FULL_BOXES = "لدينا ٨٧ تفاحة نضعها في صناديق تتسع كل منها ٦ تفاحة. كم صندوقاً ممتلئاً نحصل عليه؟"
AVERAGE = "حصلت ليلى على الدرجات ٨٥، ٩٠، ٧٨ في ٣ اختبارات. ما هو متوسط درجاتها؟"
THINK = "فكّر خالد في عدد، ضربه في ٣ ثم أضاف ٥، فكانت النتيجة ٢٠. ما هو العدد الأصلي؟"


def prop(problem: str, final: str) -> str:
    hit = arabic_word.formalize_word_problem(problem, final)
    assert hit is not None, problem
    return hit[0]


def test_boxes_then_give_multiplies_before_subtracting():
    assert prop(BOXES, "3050") == "((93:ℚ) * 37) - 391 = 3050"
    assert prop(BOXES, "172") == "((93:ℚ) * 37) - 391 = 172"


def test_compound_discount_is_multiplicative_not_additive():
    p = prop(DISCOUNT, "576")
    assert p == "(800:ℚ) * (1 - 10 / 100) * (1 - 20 / 100) = 576"


def test_full_boxes_uses_nat_division():
    assert prop(FULL_BOXES, "14") == "(87:ℕ) / 6 = 14"


def test_average_of_listed_grades_divides_by_count_with_tolerance():
    p = prop(AVERAGE, "84.33")
    assert p.startswith("((85:ℚ) + (90:ℚ) + (78:ℚ)) / 3 - 84.33 <")
    assert "∧" in p and "/ 3" in p and "/ 90" not in p


def test_think_of_a_number_substitutes_the_answer():
    assert prop(THINK, "5") == "(((5:ℚ)) * 3) + 5 = 20"


def test_certificate_lists_fired_clauses():
    _, deriv = arabic_word.formalize_word_problem(BOXES, "3050")
    assert "boxes" in deriv and "give" in deriv and "⇒" in deriv


def test_western_and_eastern_digits_agree():
    western = BOXES.replace("٩٣", "93").replace("٣٧", "37").replace("٣٩١", "391")
    assert prop(western, "3050") == prop(BOXES, "3050")


@pytest.mark.parametrize(
    "text",
    [
        "كل المربعات مستطيلات، وبعض المستطيلات ليست مربعات. هل يلزم أن بعض المربعات ليست مستطيلات؟",
        "اشترى سعيد ٩٣ علبة. كم صندوقاً بقي لدى سعيد؟",  # partial narrative: no contents clause
        "What is 17 * 23?",
        "",
    ],
)
def test_unsupported_or_partial_narratives_return_none(text):
    assert arabic_word.formalize_word_problem(text, "1") is None


def test_no_final_answer_returns_none():
    assert arabic_word.formalize_word_problem(BOXES, None) is None


def test_order_of_operations_with_exponent_stays_in_arithmetic_fragment():
    hit = formalize_problem("احسب قيمة ٣٦ + ٩ × ٨ − ٣² باتباع ترتيب العمليات.", "99")
    assert hit is not None
    assert hit[0] == "(36:ℚ) + 9 * 8 - 3 ^ 2 = 99"
