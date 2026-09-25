import Mathlib

/-!
# Finite symmetric relations ("friendship graphs") and the handshake lemma

The Arabic counting fragment (`falconverifier/arabic_graph.py`) translates puzzles of the form
«n people, each claims to be friends with exactly k of the others — must someone be lying?»
into `¬ ∃ f : Fin n → Fin n → Bool, Regular f k`. Deciding that by enumeration is hopeless
(2^(n²) relations), so the automation uses these two lemmas instead:

* `no_regular_of_odd`: if `n * k` is odd no such relation exists (degree sum = 2·|edges|);
* `circulant n k` is an explicit k-regular relation whenever one exists, checked by `decide`.
-/

namespace FalconVerifier

/-- A symmetric, irreflexive Boolean relation on `Fin n`. -/
def IsGraph {n : ℕ} (f : Fin n → Fin n → Bool) : Prop :=
  (∀ x y, f x y = f y x) ∧ ∀ x, f x x = false

/-- Number of `y` related to `x`. -/
def degree {n : ℕ} (f : Fin n → Fin n → Bool) (x : Fin n) : ℕ :=
  (Finset.univ.filter fun y => f x y = true).card

/-- `f` is a graph in which every vertex has exactly `k` neighbours. -/
def Regular {n : ℕ} (f : Fin n → Fin n → Bool) (k : ℕ) : Prop :=
  IsGraph f ∧ ∀ x, degree f x = k

instance {n : ℕ} (f : Fin n → Fin n → Bool) : Decidable (IsGraph f) := by
  unfold IsGraph; infer_instance

instance {n : ℕ} (f : Fin n → Fin n → Bool) (k : ℕ) : Decidable (Regular f k) := by
  unfold Regular; infer_instance

/-- The simple graph underlying a symmetric irreflexive Boolean relation. -/
def toSimpleGraph {n : ℕ} (f : Fin n → Fin n → Bool) (h : IsGraph f) : SimpleGraph (Fin n) where
  Adj x y := f x y = true
  symm := ⟨fun {x y} hxy => by
    show f y x = true
    rw [← h.1 x y]; exact hxy⟩
  loopless := ⟨fun x hx => by
    have hx' : f x x = true := hx
    rw [h.2 x] at hx'
    exact Bool.false_ne_true hx'⟩

instance {n : ℕ} (f : Fin n → Fin n → Bool) (h : IsGraph f) :
    DecidableRel (toSimpleGraph f h).Adj :=
  fun x y => inferInstanceAs (Decidable (f x y = true))

theorem degree_toSimpleGraph {n : ℕ} (f : Fin n → Fin n → Bool) (h : IsGraph f) (x : Fin n) :
    (toSimpleGraph f h).degree x = degree f x := by
  rw [← SimpleGraph.card_neighborFinset_eq_degree, SimpleGraph.neighborFinset_eq_filter]
  rfl

/-- Handshake lemma: no `k`-regular graph on `n` vertices when `n * k` is odd. -/
theorem no_regular_of_odd {n k : ℕ} (hodd : Odd (n * k)) :
    ¬ ∃ f : Fin n → Fin n → Bool, Regular f k := by
  rintro ⟨f, hg, hdeg⟩
  have hsum : ∑ x, (toSimpleGraph f hg).degree x = n * k := by
    simp only [degree_toSimpleGraph, hdeg, Finset.sum_const, Finset.card_univ, Fintype.card_fin,
      smul_eq_mul]
  have heven : Even (n * k) := by
    rw [← hsum, SimpleGraph.sum_degrees_eq_twice_card_edges]
    exact even_two_mul _
  exact (Nat.not_even_iff_odd.mpr hodd) heven

/-- `no_regular_of_odd` in universally quantified form (the shape the Arabic fragment emits
for a «someone must be lying» question). -/
theorem not_regular_of_odd {n k : ℕ} (hodd : Odd (n * k)) :
    ∀ f : Fin n → Fin n → Bool, ¬ Regular f k :=
  fun f hf => no_regular_of_odd hodd ⟨f, hf⟩

/-- A vertex has at most `n - 1` neighbours, so no `k`-regular relation on `n` vertices exists
when `k ≥ n` («each of the 4 is friends with all 5 others»). -/
theorem no_regular_of_ge {n k : ℕ} (h : 0 < n ∧ n ≤ k) :
    ¬ ∃ f : Fin n → Fin n → Bool, Regular f k := by
  rintro ⟨f, hg, hdeg⟩
  have x : Fin n := ⟨0, h.1⟩
  have hd := hdeg x
  unfold degree at hd
  have hsub : (Finset.univ.filter fun y => f x y = true) ⊆ Finset.univ.erase x := by
    intro y hy
    simp only [Finset.mem_filter, Finset.mem_univ, true_and] at hy
    refine Finset.mem_erase.mpr ⟨?_, Finset.mem_univ _⟩
    intro hyx
    rw [hyx, hg.2 x] at hy
    exact Bool.false_ne_true hy
  have := Finset.card_le_card hsub
  rw [Finset.card_erase_of_mem (Finset.mem_univ _), Finset.card_univ, Fintype.card_fin] at this
  omega

theorem not_regular_of_ge {n k : ℕ} (h : 0 < n ∧ n ≤ k) :
    ∀ f : Fin n → Fin n → Bool, ¬ Regular f k :=
  fun f hf => no_regular_of_ge h ⟨f, hf⟩

example : ∀ f : Fin 4 → Fin 4 → Bool, ¬ Regular f 4 := not_regular_of_ge (by decide)

/-- Circulant relation: `x ~ y` iff their cyclic distance is at most `k / 2`, plus the
antipodal vertex when `k` is odd (which requires `n` even). `k`-regular whenever `n * k` is
even and `k < n`; the automation checks the instance with `decide`. -/
def circulant (n k : ℕ) (x y : Fin n) : Bool :=
  let d := (y.val + n - x.val) % n
  x ≠ y && (d ≤ k / 2 || n - d ≤ k / 2 || (k % 2 = 1 && 2 * d = n))

example : Regular (circulant 6 3) 3 := by decide
example : ¬ ∃ f : Fin 5 → Fin 5 → Bool, Regular f 3 := no_regular_of_odd (by decide)
example : ∀ f : Fin 5 → Fin 5 → Bool, ¬ Regular f 3 := not_regular_of_odd (by decide)

end FalconVerifier
