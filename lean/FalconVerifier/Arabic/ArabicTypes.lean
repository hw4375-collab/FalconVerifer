import FalconVerifier.Arabic.Pregroup

namespace FalconVerifier.ArabicTypes
open FalconVerifier.Pregroup



/- Basic types of Arabic phrase:
π : external subject
o : external object
s : declarative sentence
-/

inductive ArabicAtom where
  | π
  | o
  | s₀



-- π ∈ A ↦ ι (π) ∈ Ty (A)

def π : Ty ArabicAtom := Ty.atom ArabicAtom.π
def o : Ty ArabicAtom := Ty.atom ArabicAtom.o
def s₀ : Ty ArabicAtom := Ty.atom ArabicAtom.s₀


/-
كَتَبَ أَحْمَدُ الدَّرْسَ
lesson ← Ahmad ← wrote

Transliteration (left-to-right):
kataba / Aḥmadu / al-darsa

Gloss:
wrote / Ahmad / the lesson

Word order:
V / S / O

English:
"Ahmad wrote the lesson."
-/

def kataba : Ty ArabicAtom := s₀ * oˡ * πˡ
def ahmad : Ty ArabicAtom := π
def alDarsa : Ty ArabicAtom := o




def vsoSentence : Ty ArabicAtom :=
  kataba * ahmad * alDarsa

/-

def vsoDerivation : vsoSentence ⊢ s₀ := by
  have d₁ :
    (s₀ * oˡ * π ˡ) * π ⊢ (s₀ * oˡ) * (π ˡ * π) := by
      exact Deriv.assocLR

  have d₂ :
    (s₀ * oˡ) * (πˡ * π) ⊢ (s₀ * oˡ) := by
      exact contractInsideRight  (s₀ * oˡ) π

  have d₃ :
    (s₀ * oˡ) * o ⊢ s₀ * (oˡ * o) := by
      exact Deriv.assocLR

  have d₄ :
    s₀ * (oˡ * o) ⊢ s₀ := by
      exact contractInsideRight s₀ o

  have d₁' :
    (s₀ * oˡ * π ˡ) * π * o ⊢ (s₀ * oˡ) * (π ˡ * π) * o := by
      exact Deriv.mono d₁ (Deriv.refl o)

  have d₂' :
    (s₀ * oˡ) * (π ˡ * π) * o ⊢ (s₀ * oˡ) * o := by
      exact Deriv.mono d₂ (Deriv.refl o)

  have d₁₂ :
    (s₀ * oˡ * πˡ) * π * o ⊢ (s₀ * oˡ) * o := by
      exact Deriv.trans d₁' d₂'

  have d₁₃ :
    (s₀ * oˡ * πˡ) * π * o ⊢ s₀ * (oˡ * o) := by
      exact Deriv.trans d₁₂ d₃

  exact Deriv.trans d₁₃ d₄

-/

def vsoDerivation : vsoSentence ⊢ s₀ := by
  have d₁ :
      (s₀ * oˡ * πˡ) * π * o
        ⊢
      (s₀ * oˡ) * (πˡ * π) * o := by
    exact Deriv.mono Deriv.assocLR (Deriv.refl o)

  have d₂ :
      (s₀ * oˡ) * (πˡ * π) * o
        ⊢
      (s₀ * oˡ) * o := by
    exact Deriv.mono
      (contractInsideRight (s₀ * oˡ) π)
      (Deriv.refl o)

  have d₃ :
      (s₀ * oˡ) * o ⊢ s₀ := by
    exact Deriv.trans
      Deriv.assocLR
      (contractInsideRight s₀ o)

  exact Deriv.trans d₁ (Deriv.trans d₂ d₃)


theorem vso_valid :
    Derivable vsoSentence s₀ := by
  exact ⟨vsoDerivation⟩



/-
أَحْمَدُ كَتَبَ الدَّرْسَ

lesson ← wrote ← Ahmad

Transliteration (left-to-right):

Aḥmadu / kataba / al-darsa

Gloss:

Ahmad / wrote / the lesson

Word order:

S / V / O

English:

"Ahmad wrote the lesson."
-/

def contractInsideLeft {Atom : Type} (A X : Ty Atom) :
    (X * Xʳ) * A ⊢ A := by

      have d₁ : (X * Xʳ) * A ⊢ 𝟙 * A :=
        Deriv.mono (Deriv.rightContract) (Deriv.refl A)

      exact Deriv.trans d₁ Deriv.leftUnitContract



def katabaSVO : Ty ArabicAtom :=
  πʳ * s₀ * oˡ

def svoSentence : Ty ArabicAtom :=
  ahmad * katabaSVO * alDarsa

def svoDerivation : svoSentence ⊢ s₀ := by

  have d₁ : (πʳ * s₀ * oˡ) * o ⊢ (πʳ * s₀) * (oˡ * o) := by
    exact Deriv.assocLR

  have d₂ : (πʳ * s₀) * (oˡ * o) ⊢ πʳ * s₀ := by
    exact contractInsideRight (πʳ * s₀) o

  have d₁₂ : (πʳ * s₀ * oˡ) * o ⊢ πʳ * s₀ := by
    exact Deriv.trans d₁ d₂

  have d₃ : π * ((πʳ * s₀ * oˡ) * o)  ⊢ π * (πʳ * s₀) := by
    exact Deriv.mono (Deriv.refl π) d₁₂

  have d₄ : π * (πʳ * s₀ * oˡ) * o ⊢ π * ((πʳ * s₀ * oˡ) * o) := by
    exact Deriv.assocLR

  have d₃₄ : π * (πʳ * s₀ * oˡ) * o ⊢ π * (πʳ * s₀) := by
    exact Deriv.trans d₄ d₃

  have d₅ : π * (πʳ * s₀) ⊢ (π * πʳ) * s₀ := by
    exact Deriv.assocRL

  have d₆ : (π * πʳ) * s₀ ⊢ s₀ := by
    exact contractInsideLeft s₀ π

  have d₅₆ :  π * (πʳ * s₀) ⊢ s₀ := by
    exact Deriv.trans d₅ d₆

  have d₇ : π * (πʳ * s₀ * oˡ) * o ⊢ s₀ := by
    exact Deriv.trans d₃₄ d₅₆

  exact d₇



theorem svo_valid :
    Derivable svoSentence s₀ := by
  exact ⟨svoDerivation⟩


end FalconVerifier.ArabicTypes
