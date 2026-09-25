/-
Pregroup grammar kernel — contributed by the FalconVerifer team (original: LeanArabic.Pregroup).
-/
/-
A minimal syntactic kernel for Pregroup grammar.

This file defines:
  1. the syntax of Pregroup type expressions;
  2. explicit derivation objects between type expressions.

The kernel is generic: no Arabic-specific grammatical assumptions
belong in this file.
-/

namespace FalconVerifier.Pregroup

/- Basic types of Arabic phrase:
π : external subject
o : external object
s : declarative sentence
-/

/- Ty(A)::= A | 1 | Ty(A) × Ty(A) | Ty(A) | Ty(A)
ι : A → Ty(A)
e : 1 → Ty(A)
m : Ty(A) × Ty(A) → Ty(A)
L : Ty(A) → Ty(A)
R : Ty(A) → Ty(A)
-/

inductive Ty (Atom : Type) where
  | atom : Atom → Ty Atom
  | one : Ty Atom
  | mul : Ty Atom → Ty Atom → Ty Atom
  | leftAdj : Ty Atom → Ty Atom
  | rightAdj : Ty Atom → Ty Atom


/- Mathematical notation for type expressions. -/

infixl:70 " * " => Ty.mul
notation "𝟙" => Ty.one
postfix:max "ˡ" => Ty.leftAdj
postfix:max "ʳ" => Ty.rightAdj


/-
Instead of representing `X ≤ Y` merely as a proposition, we use 'Deriv X Y : Type'
whose terms are explicit derivation certificates witnessing that X reduces to Y.
The generating rules encode:
Reflexivity: X ≤ X
Transitivity: X ≤ Y, Y ≤ Z  ⟹  X ≤ Z
Monotonicity: X ≤ Y, U ≤ V  ⟹  XU ≤ YV
Pregroup adjunction: XˡX ≤ 𝟙 ≤ XXˡ ∧ XXʳ ≤ 𝟙 ≤ XʳX
Associativity: (XY)Z = X(YZ)
Unit laws: 𝟙X = X = X𝟙

Since Deriv represents a directed relation, each equality above
is represented by derivations in both directions.
-/

inductive Deriv {Atom : Type} : Ty Atom → Ty Atom → Type where

  | refl (X : Ty Atom) :
      Deriv X X

  | trans {X Y Z : Ty Atom} :
      Deriv X Y →
      Deriv Y Z →
      Deriv X Z

  | mono {X Y U V : Ty Atom} :
      Deriv X Y →
      Deriv U V →
      Deriv (X * U) (Y * V)

  | leftContract {X : Ty Atom} :
      Deriv (Xˡ * X) 𝟙

  | rightContract {X : Ty Atom} :
      Deriv (X * Xʳ) 𝟙

  | leftExpand {X : Ty Atom} :
      Deriv 𝟙 (X * Xˡ)

  | rightExpand {X : Ty Atom} :
      Deriv 𝟙 (Xʳ * X)

  | assocLR {X Y Z : Ty Atom} :
      Deriv ((X * Y) * Z) (X * (Y * Z))

  | assocRL {X Y Z : Ty Atom} :
      Deriv (X * (Y * Z)) ((X * Y) * Z)

  | leftUnitContract {X : Ty Atom} :
      Deriv (𝟙 * X) X

  | leftUnitExpand {X : Ty Atom} :
      Deriv X (𝟙 * X)

  | rightUnitContract {X : Ty Atom} :
      Deriv (X * 𝟙) X

  | rightUnitExpand {X : Ty Atom} :
      Deriv X (X * 𝟙)


/- `X ⪯ Y` means that there is an explicit derivation from `X` to `Y`. -/

infix:50 " ⊢  " => Deriv




def Derivable {Atom : Type} (X Y : Ty Atom) : Prop :=
  Nonempty (Deriv X Y)


---- Test Proof

def contractInsideRight {Atom : Type} (A X : Ty Atom) :
    A * (Xˡ * X) ⊢  A := by

      have d₁ : A * (Xˡ * X) ⊢ A * 𝟙 :=
        Deriv.mono (Deriv.refl A) (Deriv.leftContract)

      exact Deriv.trans d₁ Deriv.rightUnitContract




theorem contractInsideRight_derivable
    {Atom : Type} (A X : Ty Atom) :
    Derivable (A * (Xˡ * X)) A := by
  exact ⟨contractInsideRight A X⟩







----








end FalconVerifier.Pregroup
