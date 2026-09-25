"""Arabic counting fragment (symmetric relations / handshake lemma) and the structured
round-trip faithfulness check."""

from __future__ import annotations

import pytest

from falconverifier import arabic_graph
from falconverifier.formalizer import (
    Signature,
    align_polarity,
    compare_signatures,
    prop_signature,
)

FIVE_FRIENDS = (
    "خمسة طلاب يجلسون في الفصل، ويقول كل واحد منهم إن ثلاثة من الأربعة الباقين أصدقاؤه. "
    "هل يلزم أن أحدهم يكذب؟"
)
SIX_FRIENDS = "ستة أشخاص، كل واحد منهم صديق لثلاثة من الآخرين بالضبط والصداقة متبادلة. هل يمكن ذلك؟"
SEVEN_HANDSHAKES = "في حفلة ٧ ضيوف، صافح كل ضيف بالضبط ٣ من الضيوف الآخرين. هل يمكن ذلك؟"
FOUR_ALL = "أربعة طلاب، ويقول كل طالب إن له أربعة أصدقاء بينهم. هل يلزم أن أحدهم يكذب؟"


def test_five_friends_is_a_binary_relation_not_a_per_person_bool():
    hit = arabic_graph.formalize_graph_problem(FIVE_FRIENDS)
    assert hit is not None
    prop, cert = hit
    assert prop == "∀ f : Fin 5 → Fin 5 → Bool, ¬ FalconVerifier.Regular f 3"
    assert "n := خمسة (5)" in cert and "k := ثلاثة (3)" in cert
    assert "symmetry assumed from lexeme «اصدقاؤه»" in cert
    # «لا» must become the negation, so a wrong «لا» is refuted rather than verified
    assert align_polarity(prop, "لا") == f"¬ ({prop})"
    assert align_polarity(prop, "نعم") == prop


@pytest.mark.parametrize(
    ("text", "n", "k", "question", "truth"),
    [
        (FIVE_FRIENDS, 5, 3, "impossible", True),
        (SIX_FRIENDS, 6, 3, "possible", True),
        (SEVEN_HANDSHAKES, 7, 3, "possible", False),
        (FOUR_ALL, 4, 4, "impossible", True),
    ],
)
def test_parity_and_degree_bound_decide_the_answer_key(text, n, k, question, truth):
    puz = arabic_graph.analyze(text)
    assert puz is not None
    assert (puz.n, puz.k, puz.question, puz.truth) == (n, k, question, truth)


def test_explicit_symmetry_is_recorded_in_the_certificate():
    puz = arabic_graph.analyze(SIX_FRIENDS)
    assert puz is not None and puz.explicit_symmetry
    assert "symmetry stated" in puz.certificate()
    assert puz.prop() == "∃ f : Fin 6 → Fin 6 → Bool, FalconVerifier.Regular f 3"


@pytest.mark.parametrize(
    "text",
    [
        # no symmetric relation lexeme
        "خمسة طلاب، كل واحد منهم يكره ثلاثة من الآخرين. هل يلزم أن أحدهم يكذب؟",
        # complete graph («with all the others»), not «k of the others»
        "خمسة أصدقاء تصافحوا مع كل من الآخرين. هل يمكن ذلك؟",
        # not a yes/no question of the recognised kind
        "خمسة طلاب، كل واحد منهم صديق لثلاثة من الآخرين. كم عدد علاقات الصداقة؟",
        # a plain syllogism must stay with the logic fragment
        "كل الأطباء متعلمون، وبعض الأطباء أثرياء. هل يلزم أن بعض المتعلمين أثرياء؟",
    ],
)
def test_fragment_refuses_what_it_does_not_understand(text):
    assert arabic_graph.formalize_graph_problem(text) is None


def test_explanations_teach_parity_or_give_a_witness():
    # wrong «لا» on the 5-friends puzzle: handshake parity argument
    e = arabic_graph.explanation(FIVE_FRIENDS, answered_yes=False)
    assert e is not None and "5 × 3 = 15" in e and "no_regular_of_odd" in e
    # right answer: nothing to teach
    assert arabic_graph.explanation(FIVE_FRIENDS, answered_yes=True) is None
    # wrong «لا» on the possible 6/3 case: explicit circulant construction
    e = arabic_graph.explanation(SIX_FRIENDS, answered_yes=False)
    assert e is not None and "circulant 6 3" in e and "دائرة" in e
    # wrong «نعم» on 7 guests × 3 handshakes
    e = arabic_graph.explanation(SEVEN_HANDSHAKES, answered_yes=True)
    assert e is not None and "7 × 3 = 21" in e
    # k ≥ n: the degree bound, not parity
    e = arabic_graph.explanation(FOUR_ALL, answered_yes=False)
    assert e is not None and "على الأكثر" in e


def test_formalizer_prefers_the_graph_fragment_without_any_llm_call():
    from conftest import ScriptedModel

    from falconverifier.formalizer import Formalizer
    from falconverifier.schemas import ReasoningStep

    model = ScriptedModel([])
    form, _ = Formalizer(model).formalize(
        FIVE_FRIENDS, [ReasoningStep(index=1, text="٥ × ٣ = ١٥")], "نعم"
    )
    assert model.calls == []
    assert form.problem_prop == "∀ f : Fin 5 → Fin 5 → Bool, ¬ FalconVerifier.Regular f 3"
    assert form.problem_note.startswith("pregroup:")
    assert form.steps[0].lean_prop is not None and "15" in form.steps[0].lean_prop


# --- structured round-trip -----------------------------------------------------------

BAD_FLATTENED = (
    "∀ (students : Fin 5 → Bool), (∀ x, students x → (∃ y, y ≠ x ∧ students y ∧ "
    "(∃ z, z ≠ x ∧ z ≠ y ∧ students z))) → (∃ x, ¬ students x)"
)
GOOD_GRAPH = "∀ f : Fin 5 → Fin 5 → Bool, ¬ FalconVerifier.Regular f 3"
HANDROLLED_NO_SYMMETRY = (
    "∀ f : Fin 5 → Fin 5 → Bool, (∀ x, ∑ y, (if f x y then 1 else 0) = 3) → False"
)
SYLLOGISM = "∀ (A B C : Fin 3 → Bool), (∀ x, A x → B x) → (∃ x, A x ∧ C x) → ∃ x, B x ∧ C x"
ORDERING = "∀ (a b c : ℤ), a > b → b > c → a > c"

FRIENDS_Q = Signature(binary=True, symmetric=True, counts=frozenset({5, 3, 4}))
SYLLOGISM_Q = Signature(binary=False, symmetric=False, counts=frozenset())
ORDER_Q = Signature(binary=True, symmetric=False, counts=frozenset())


def test_prop_signature_reads_arity_symmetry_and_counts_mechanically():
    assert prop_signature(BAD_FLATTENED) == Signature(False, False, frozenset({5}))
    assert prop_signature(GOOD_GRAPH) == Signature(True, True, frozenset({5, 3}))
    assert prop_signature(HANDROLLED_NO_SYMMETRY).binary
    assert not prop_signature(HANDROLLED_NO_SYMMETRY).symmetric
    assert prop_signature(SYLLOGISM) == Signature(False, False, frozenset({3}))
    assert prop_signature(ORDERING) == Signature(True, False, frozenset())
    assert prop_signature("∀ f : Fin 6 → Fin 6 → Bool, (∀ x y, f x y = f y x) → True").symmetric


def test_round_trip_rejects_structure_loss_and_accepts_faithful_abstraction():
    ok, why = compare_signatures(FRIENDS_Q, prop_signature(BAD_FLATTENED))
    assert not ok and "relation between individuals" in why
    ok, why = compare_signatures(FRIENDS_Q, prop_signature(HANDROLLED_NO_SYMMETRY))
    assert not ok and "symmetry" in why
    ok, why = compare_signatures(
        FRIENDS_Q, prop_signature("∀ f : Fin 5 → Fin 5 → Bool, ¬ FalconVerifier.Regular f 2")
    )
    assert not ok and "[3]" in why
    assert compare_signatures(FRIENDS_Q, prop_signature(GOOD_GRAPH))[0]
    assert compare_signatures(SYLLOGISM_Q, prop_signature(SYLLOGISM))[0]
    assert compare_signatures(ORDER_Q, prop_signature(ORDERING))[0]
    # a syllogism question never complains about a Fin 3 domain or missing counts
    assert compare_signatures(SYLLOGISM_Q, prop_signature(BAD_FLATTENED))[0]
