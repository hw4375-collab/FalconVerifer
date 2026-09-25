import FalconVerifier.Prelude
import FalconVerifier.Arabic.Pregroup
import FalconVerifier.Arabic.ArabicTypes

/-!
# From pregroup syntax to meaning, and what Arabic morphology does to it

`ArabicTypes.lean` shows that the VSO sentence *kataba Aḥmadu al-darsa* and the SVO
sentence *Aḥmadu kataba al-darsa* both reduce to the sentence type `s₀`.  That is a
statement about **syntax**.  Here we add two things FalconVerifer needs:

1. **Semantics (DisCoCat style).**  A pregroup derivation is a *wiring diagram*; reading it
   as a function that plugs the noun meanings into the verb meaning gives the sentence
   meaning.  We show that the two word orders denote the *same* proposition
   `wrote ahmad lesson`, so a verifier may treat them as one claim.

2. **A faithfulness limit.**  Arabic verbs carry person/gender/number of the subject
   (Bargelli–Lambek 2003 index the subject type `π_i` by these features).  If a pregroup
   lexicon uses one coarse subject atom `π`, an agreement-violating sentence
   (*katabat Aḥmadu* — feminine verb, masculine subject) is still derivable: syntax accepted,
   meaning lost.  We prove this, and prove that a feature-indexed lexicon rejects it, via a
   ℤ-valued invariant of pregroup derivations.  This is the formal content behind the claim
   "pregroups alone do not preserve Arabic morphological information; the semantic
   layer must carry it".
-/

namespace FalconVerifier.Semantics
open FalconVerifier.Pregroup FalconVerifier.ArabicTypes

/-! ## 1. Relational semantics: word order is not meaning -/

/-- A tiny universe of individuals. -/
inductive Entity where
  | ahmad
  | lesson
  | fatima
  deriving DecidableEq, Repr

/-- The meaning of the verb *kataba* ("wrote") as a relation. -/
def wrote : Entity → Entity → Prop := fun subj obj => (subj, obj) = (Entity.ahmad, Entity.lesson)

/-- Meaning assembled along the VSO wiring `(s₀ * oˡ * πˡ) * π * o ⊢ s₀`:
the verb consumes the subject wire then the object wire. -/
def meaningVSO (verb : Entity → Entity → Prop) (subj obj : Entity) : Prop := verb subj obj

/-- Meaning assembled along the SVO wiring `π * (πʳ * s₀ * oˡ) * o ⊢ s₀`. -/
def meaningSVO (verb : Entity → Entity → Prop) (subj obj : Entity) : Prop := verb subj obj

/-- **Word-order equivalence.** Both syntactically valid orders (see `vso_valid`,
`svo_valid`) denote the same proposition. A verifier can therefore normalise Arabic
VSO/SVO reasoning steps to one Lean claim without changing what is being checked. -/
theorem vso_svo_same_meaning (verb : Entity → Entity → Prop) (subj obj : Entity) :
    meaningVSO verb subj obj ↔ meaningSVO verb subj obj := Iff.rfl

example : meaningVSO wrote Entity.ahmad Entity.lesson := rfl
example : ¬ meaningSVO wrote Entity.fatima Entity.lesson := by
  simp [meaningSVO, wrote]

/-! ## 2. A ℤ-invariant of derivations -/

/-- Any assignment of integers to atoms extends to types: adjoints negate, product adds.
Every rule of `Deriv` preserves this weight, so it is an invariant of derivability. -/
def weight {Atom : Type} (w : Atom → ℤ) : Ty Atom → ℤ
  | Ty.atom a => w a
  | Ty.one => 0
  | Ty.mul x y => weight w x + weight w y
  | Ty.leftAdj x => - weight w x
  | Ty.rightAdj x => - weight w x

theorem weight_preserved {Atom : Type} (w : Atom → ℤ) {X Y : Ty Atom} (d : X ⊢ Y) :
    weight w X = weight w Y := by
  induction d with
  | refl => rfl
  | trans _ _ ih₁ ih₂ => exact ih₁.trans ih₂
  | mono _ _ ih₁ ih₂ => simp [weight, ih₁, ih₂]
  | leftContract => simp [weight]
  | rightContract => simp [weight]
  | leftExpand => simp [weight]
  | rightExpand => simp [weight]
  | assocLR => simp [weight, add_assoc]
  | assocRL => simp [weight, add_assoc]
  | leftUnitContract => simp [weight]
  | leftUnitExpand => simp [weight]
  | rightUnitContract => simp [weight]
  | rightUnitExpand => simp [weight]

/-- Non-derivability criterion: different weights ⇒ no derivation. -/
theorem not_derivable_of_weight_ne {Atom : Type} (w : Atom → ℤ) {X Y : Ty Atom}
    (h : weight w X ≠ weight w Y) : ¬ Derivable X Y := by
  rintro ⟨d⟩
  exact h (weight_preserved w d)

/-! ## 3. Agreement: coarse types accept what Arabic rejects -/

/-- *katabat* ("she wrote") typed with the coarse subject atom `π` — identical to *kataba*.
The lexicon cannot see gender. -/
def katabatCoarse : Ty ArabicAtom := s₀ * oˡ * πˡ

/-- كَتَبَتْ أَحْمَدُ الدَّرْسَ — feminine verb, masculine subject: **ungrammatical Arabic**,
yet derivable with coarse types. -/
def badAgreementCoarse : Ty ArabicAtom := katabatCoarse * ahmad * alDarsa

theorem coarse_accepts_bad_agreement : Derivable badAgreementCoarse s₀ := by
  unfold badAgreementCoarse katabatCoarse
  exact ⟨vsoDerivation⟩

/-- Feature-indexed atoms in the spirit of Bargelli–Lambek's `π_i`: the subject type carries
gender, so the verb selects it. -/
inductive FeatAtom where
  | πm   -- masculine singular subject
  | πf   -- feminine singular subject
  | o
  | s₀
  deriving DecidableEq

open FeatAtom in
def fπm : Ty FeatAtom := Ty.atom πm
open FeatAtom in
def fπf : Ty FeatAtom := Ty.atom πf
open FeatAtom in
def fo : Ty FeatAtom := Ty.atom o
open FeatAtom in
def fs₀ : Ty FeatAtom := Ty.atom s₀

/-- *kataba* wants a masculine subject; *katabat* wants a feminine one. -/
def katabaF : Ty FeatAtom := fs₀ * foˡ * fπmˡ
def katabatF : Ty FeatAtom := fs₀ * foˡ * fπfˡ
def ahmadF : Ty FeatAtom := fπm
def fatimaF : Ty FeatAtom := fπf
def alDarsaF : Ty FeatAtom := fo

/-- كَتَبَ أَحْمَدُ الدَّرْسَ still parses with indexed types. -/
theorem fine_agreement_derivable : Derivable (katabaF * ahmadF * alDarsaF) fs₀ := by
  refine ⟨?_⟩
  have d₁ : (fs₀ * foˡ * fπmˡ) * fπm * fo ⊢ (fs₀ * foˡ) * (fπmˡ * fπm) * fo :=
    Deriv.mono Deriv.assocLR (Deriv.refl fo)
  have d₂ : (fs₀ * foˡ) * (fπmˡ * fπm) * fo ⊢ (fs₀ * foˡ) * fo :=
    Deriv.mono (contractInsideRight (fs₀ * foˡ) fπm) (Deriv.refl fo)
  have d₃ : (fs₀ * foˡ) * fo ⊢ fs₀ :=
    Deriv.trans Deriv.assocLR (contractInsideRight fs₀ fo)
  exact Deriv.trans d₁ (Deriv.trans d₂ d₃)

/-- كَتَبَتْ فَاطِمَةُ الدَّرْسَ parses too. -/
theorem feminine_agreement_derivable : Derivable (katabatF * fatimaF * alDarsaF) fs₀ := by
  refine ⟨?_⟩
  have d₁ : (fs₀ * foˡ * fπfˡ) * fπf * fo ⊢ (fs₀ * foˡ) * (fπfˡ * fπf) * fo :=
    Deriv.mono Deriv.assocLR (Deriv.refl fo)
  have d₂ : (fs₀ * foˡ) * (fπfˡ * fπf) * fo ⊢ (fs₀ * foˡ) * fo :=
    Deriv.mono (contractInsideRight (fs₀ * foˡ) fπf) (Deriv.refl fo)
  have d₃ : (fs₀ * foˡ) * fo ⊢ fs₀ :=
    Deriv.trans Deriv.assocLR (contractInsideRight fs₀ fo)
  exact Deriv.trans d₁ (Deriv.trans d₂ d₃)

/-- Weight that counts feminine-subject wires. -/
def genderWeight : FeatAtom → ℤ
  | FeatAtom.πf => 1
  | _ => 0

/-- **Faithfulness theorem.** With feature-indexed types the agreement-violating sentence
كَتَبَتْ أَحْمَدُ الدَّرْسَ is *not* derivable: the feminine wire opened by the verb is never
closed by a feminine subject. Contrast `coarse_accepts_bad_agreement`. -/
theorem indexed_rejects_bad_agreement : ¬ Derivable (katabatF * ahmadF * alDarsaF) fs₀ := by
  apply not_derivable_of_weight_ne genderWeight
  decide

/-! ## 4. Pro-drop: the subject lives *inside* the verb

*katabū al-darsa* ("they wrote the lesson") has no external subject word: the verb form
alone contributes `s₀ * oˡ` (Bargelli–Lambek §3: "the subject may be incorporated in the
verb"). Any semantics attached to the pregroup derivation must therefore read the subject
off the *verb's morphology*, not off a wire — precisely the information the coarse lexicon
discards. This is why FalconVerifer's Arabic pre-formalizer keeps a feature record
(person/gender/number) alongside each pregroup type. -/

def katabuu : Ty ArabicAtom := s₀ * oˡ

theorem prodrop_derivable : Derivable (katabuu * alDarsa) s₀ := by
  refine ⟨?_⟩
  exact Deriv.trans Deriv.assocLR (contractInsideRight s₀ o)

end FalconVerifier.Semantics
