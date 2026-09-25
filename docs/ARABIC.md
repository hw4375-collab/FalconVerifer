# Arabic: pregroup grammar → typed meaning → Lean 4

FalconVerifier's Arabic track answers three questions with code and theorems rather than
slogans:

1. **Does the verify-and-teach loop work on Arabic math/logic conversations with Falcon?**
   Yes — `bench/problems_ar.jsonl` (86 items, Eastern + Western digits) is run with the same
   pipeline; numbers are in `docs/BENCHMARK.md` (`falcon7b_arabic`).
2. **Can we make the NL → Lean translation itself *provably* faithful for a fragment of
   Arabic?** Yes — `falconverifier/arabic.py` is a *pregroup grammar* parser that emits a Lean
   `Prop` together with a derivation certificate, with no LLM in the loop.
3. **Where does the type-logical approach lose meaning on Arabic, and what do we do about
   it?** Arabic morphology carries agreement (gender/number/person) that a coarse pregroup
   type erases; `lean/FalconVerifier/Arabic/Semantics.lean` proves both the loss
   (`coarse_accepts_bad_agreement`) and the remedy (`indexed_rejects_bad_agreement`).

## 1. Pregroup grammars in one page

A **pregroup** (Lambek 1999) is a partially ordered monoid where every element `x` has a
left adjoint `xˡ` and a right adjoint `xʳ`:

```
xˡ · x ≤ 1 ≤ x · xˡ          x · xʳ ≤ 1 ≤ xʳ · x
```

Words are assigned *types* built from a few basic types (`n` noun phrase, `s` sentence,
`π` subject, `o` object …) by multiplication and adjoints. A string of words is a
grammatical sentence of type `s` iff the product of the word types *reduces* to `s` using
only the contraction rules `xˡ x → 1` and `x xʳ → 1`. Crucially the reduction is a
**proof object**: a planar (non-crossing) linking of adjoint pairs. That proof is what we
store in every trace as `note: "pregroup: n nʳ s nˡ n → s"`.

Pregroups are the syntactic half of **DisCoCat** (Coecke, Sadrzadeh & Clark 2010): the same
reduction diagram, read in a different category (vector spaces, relations, or — here —
Lean propositions), *is* the semantics. The grammar therefore fixes the shape of the
meaning; the lexicon fills in the content.

The Lean kernel in `lean/FalconVerifier/Arabic/Pregroup.lean` implements exactly this:
`Ty Atom` (types), `Deriv X Y : Type` (explicit derivation certificates, constructors
`leftContract`, `rightContract`, `mono`, `assoc…`), and `Derivable X Y := Nonempty (Deriv X Y)`.

## 2. Arabic word order: VSO ≡ SVO, proved

Modern Standard Arabic allows both verb-initial (VSO, the unmarked order) and
subject-initial (SVO) clauses. Following Bargelli & Lambek (2003), the *verb* carries the
word order in its type:

```lean
-- lean/FalconVerifier/Arabic/ArabicTypes.lean
def kataba    : Ty ArabicAtom := s₀ * oˡ * πˡ     -- VSO: كتب أحمد الدرس
def katabaSVO : Ty ArabicAtom := πʳ * s₀ * oˡ     -- SVO: أحمد كتب الدرس

theorem vso_valid : Derivable (kataba * ahmad * alDarsa) s₀
theorem svo_valid : Derivable (ahmad * katabaSVO * alDarsa) s₀
```

Both are theorems (the derivations are written out constructor by constructor). On the
semantic side `Semantics.lean` interprets a transitive clause as a relation applied to
subject and object, and proves the two orders *denote the same proposition*:

```lean
theorem vso_svo_same_meaning (verb : Entity → Entity → Prop) (subj obj : Entity) :
    meaningVSO verb subj obj ↔ meaningSVO verb subj obj := Iff.rfl
```

For the verifier this means: whichever order Falcon (or the user) writes a mathematical
claim in — «يساوي ١٧ × ٢٣ ٣٩١» or «١٧ × ٢٣ يساوي ٣٩١» — the Lean proposition is the same,
and the *derivation* is the audit trail that says why.

## 3. The morphology gap — where pregroups lose faithfulness

Arabic is *morphologically rich*: a finite verb inflects for person, gender and number of
its subject (and, with clitics, its object), so a verb form already "contains" information
about its arguments. Bargelli & Lambek index Arabic verb types by exactly these features
(persons × genders × numbers × tense/mood/voice).

With a **coarse** type — one atom `π` for every subject — the pregroup accepts
agreement-violating strings: the feminine verb form «كتبتْ» with the masculine subject
«أحمد» reduces to `s₀` just as well as the correct «كتب أحمد». This is a *faithfulness
loss*: syntax says "sentence", but the morphology says "these two words do not talk about
the same referent". In Lean:

```lean
-- coarse lexicon: katabat has the same type as kataba
theorem coarse_accepts_bad_agreement : Derivable (katabatCoarse * ahmad * alDarsa) s₀
```

The remedy is to **index the atoms by features** (`πm`, `πf` …). Then the offending string
is *not* derivable — and we prove it not by failing to find a derivation, but with an
invariant that every pregroup derivation preserves:

```lean
theorem weight_preserved (w : Atom → ℤ) (d : X ⊢ Y) : weight w X = weight w Y
theorem indexed_rejects_bad_agreement : ¬ Derivable (katabatF * ahmadF * alDarsaF) fs₀
```

(`weight` counts each atom with sign, adjoints negated; contractions cancel, so the total
is a derivation invariant. A gender-weight of the mismatched string is 1 while `fs₀` has
weight 0.) The same file shows the **pro-drop** case «كتبوا الدرس» — the subject is
*inside* the verb, typed `s₀ * oˡ`, and is derivable with no separate subject word.

`falconverifier/arabic.py` mirrors this: every lexical entry carries a `feat` dictionary
(gender/number/person) *next to* its pregroup type, so the parser can reject or flag
agreement clashes that the bare type string would accept.

## 4. Why Arabic needs formal verification *more* (carefully stated)

None of this says Arabic is "less logical". It says the **NL → formal** step is riskier, so
an independent oracle matters more:

- **Two orders, one meaning.** VSO/SVO (and topicalised OVS) mean that surface position is
  not a reliable cue for argument roles; a translator that pattern-matches on position will
  mis-assign subject and object more often than in fixed-order English.
- **Information lives in morphology, not in words.** Agreement, pro-drop subjects and
  cliticised objects mean the "who did what to whom" of a claim can be carried by affixes.
  Tokenisers and small LLMs are known to be weaker at exactly this.
- **Digits and separators.** Eastern Arabic digits `٠-٩`, the decimal separator `٫`, the
  thousands separator `٬` and the percent sign `٪` co-exist with ASCII in real text; a
  wrong normalisation silently changes the number (`٣٫٥` vs `3,5`).
- **Ambiguity under-specified by the script.** Short vowels and case endings are normally
  unwritten, so e.g. nominative vs accusative — which disambiguates subject from object in
  SVO/VSO — is invisible on the page. Grammar + morphology have to be reconstructed.
- **Model capacity.** Arabic is under-represented in pre-training data, and Falcon-7B is a
  small model; in our runs the *baseline* Arabic error rate is higher than the English one
  on matched templates, so there is more for Lean to catch (see `docs/BENCHMARK.md`).

A **deterministic, certificate-producing** translator for the arithmetic/logic fragment
removes the LLM from the most fragile step, and Lean removes trust from the reasoning step.
That is the argument.

## 5. What is deterministic today (the fragment)

`falconverifier.arabic.formalize_step` handles (with Eastern or Western digits):

| Arabic | pregroup types | Lean |
|---|---|---|
| «١٧ × ٢٣ = ٣٩١», «17 ضرب 23 يساوي 391» | `n · nʳ n nˡ · n · nʳ s nˡ · n → s` | `(17:ℚ) * 23 = (391:ℚ)` |
| «مجموع ٣٤٠ و ٥١ هو ٣٩١» | `n nˡ · n · nʳ n nˡ · n · nʳ s nˡ · n → s` | `(340:ℚ) + 51 = (391:ℚ)` |
| «٥٠٪ من ١٥٠ يساوي ٧٥» | `n · nʳ n nˡ · n · nʳ s nˡ · n → s` | `(50:ℚ) / 100 * 150 = (75:ℚ)` |
| «نصف 40 هو 20», «مربع 7 هو 49», «ضعف مجموع 3 و 4 هو 14» | prefix heads `n nˡ` | `(40:ℚ) / 2 = (20:ℚ)` … |
| «12 يقبل القسمة على 3», «١٣ لا يقبل القسمة على ٣» | `n · nʳ s nˡ · n → s` | `(3:ℤ) ∣ (12:ℤ)`, `¬ ((3:ℤ) ∣ (13:ℤ))` |
| «٧ أكبر من ٥», «≠», «<» | comparison heads | `(7:ℚ) > (5:ℚ)` |
| «ما هو ناتج ١٧ × ٢٣؟», «كم يساوي ٥٠٪ من ١٥٠؟» | question head `q nˡ` | with the FINAL ANSWER: `(17:ℚ) * 23 = 391` |

The reducer is the O(n³) planar-matching search (memoised), not a greedy stack: on
«ناتج ١٧ × ٢٣» the head's `nˡ` must skip the first literal and link to the operator's output
`n`, which greedy left-to-right contraction gets wrong. All emitted props are checked
against the real Lean kernel in `tests/test_lean_integration.py::test_pregroup_props_are_decidable_by_fv_auto`.

Everything outside the fragment (word problems, syllogisms, «كل … بعض …») falls back to the
LLM formalizer, whose prompt is Arabic-aware; the pipeline then applies the usual guards
(ℚ-lift, literal grounding, faithfulness audit). Grammar-translated steps skip the LLM audit
entirely — their derivation *is* the faithfulness certificate.

### 5a. Logic questions: what the LLM formalizer got wrong, and what is now mechanical

The Arabic logic slice (syllogisms, propositional patterns, orderings; answer «نعم»/«لا») was
the weak spot: on the first Falcon-3B run Lean caught 0 of 8 wrong answers. Reading the
traces showed three *systematic* failure modes of the LLM formalizer, each now handled
without an LLM in the loop:

1. **Polarity.** The formalizer encoded the *valid* inference (`premises → conclusion`) no
   matter whether Falcon answered «نعم» or «لا، لا يلزم». A wrong «لا» was then "verified".
   `student.yes_no_polarity` reads the answer (Arabic and English, «غير صحيح»/«ليس صحيحاً»
   folded to «خطأ»; contradictory answers → no polarity) and `formalizer.align_polarity`
   makes the checked proposition assert *the student's answer*: the inference for Yes, its
   negation `¬ (…)` for No. Lean then proves the negation of a wrong «لا» by producing the
   valid derivation, and the negation of a wrong «نعم» by a counterexample.
2. **Degenerate encodings.** A frequent artefact was an inference whose conclusion is one of
   its own premises («٦ يقسم n → ٣ يقسم n → ٦ يقسم n»), trivially true and unrelated to the
   question. `formalizer.degenerate_inference` detects this shape syntactically (top-level
   `→`/`∧` split) and the agent refuses to draw either a refutation *or* an assurance from it.
3. **Over-strict auditing.** The generic faithfulness audit rejected correct abstractions
   for being "more general than the question" (named people as `Fin 3`, propositions as
   `P Q : Prop`). Yes/no finals now go through `Formalizer.audit_yes_no`, which is told that
   polarity is already handled and only asks whether premises/conclusion/quantifiers
   correspond — validity is Lean's job.

On the Lean side `fv_auto` gained a bounded counterexample search
(`push Not; refine ⟨k, ?_⟩; omega | norm_num | decide` over small witnesses), so negated
universals such as `¬ (∀ n : ℕ, 3 ∣ n → 6 ∣ n)` get a kernel verdict instead of `unknown`.

Result on the same 24 Arabic logic items with Falcon-3B, before the deterministic fragment
below: 62.5% → 79.2%, 3/9 wrong answers refuted by Lean, 0 regressions. With the fragment
(§5b): 62.5% → 87.5%, 7/9 wrong answers caught, syllogisms 8/8, 0 false alarms; with the
countermodel feedback (§5b, "teaching with the witness"): 70.8% → 91.7%, 7/7 wrong answers caught, 5 fixed
on revision (the two Falcon still refused to correct are recorded as caught-not-fixed), 0 false alarms, 0 regressions (baselines move a few points between runs
because the 3B student samples)
(`docs/BENCHMARK.md`). Still honest limits on the LLM path: the formalizer
sometimes emits invalid identifiers or mixes `Bool` and `Prop`, inclusive «أو» and parity
questions are often mistranslated, and 3B frequently omits the «الجواب النهائي» line
(now itself a teachable defect). The remedy that does *not* depend on prompt engineering is
to grow the deterministic pregroup fragment to quantifiers («كل … بعض … لا …») — done next.

### 5b. The deterministic logic fragment (`falconverifier.arabic_logic`)

Yes/no questions built from these clause shapes are now translated without any LLM:

| Arabic clause | reading | Lean (over a finite Boolean model) |
|---|---|---|
| «كل الـA B», «جميع A B» | `∀x. A x → B x` | `∀ x, A x = true → B x = true` |
| «بعض الـA B» | `∃x. A x ∧ B x` | `∃ x, A x = true ∧ B x = true` |
| «لا أحد من الـA B», «لا A B» | `∀x. A x → ¬B x` | `∀ x, A x = true → B x = false` |
| «سلطان A» / «سلطان ليس A» | individual constant | `A c0 = true` / `A c0 = false` |
| «إذا P فإن Q», «إذا P فـQ» | implication | `P = true → Q = true` |
| «إما P أو Q» / «P أو Q» | disjunction | `P = true ∨ Q = true` |
| «عمر أطول من يوسف», «س أكبر من ص» | strict order | `v0 > v1` on `Fin (k+1)` |
| «هل يلزم أن …؟», «هل يمكن أن نستنتج أن …؟» | question head | premises `→` conclusion |

Every unary predicate becomes a free `Fin 3 → Bool`, so the whole statement is closed
(`∀ (A B C : Fin 3 → Bool), …`) and *decidable*: Lean's kernel either proves the inference
or proves its negation by exhibiting a countermodel — no `unknown`. The integration test
`test_arabic_logic_fragment_is_decided_both_ways` checks all 16 covered items of the Arabic set
in both polarities (16 s for 32 claims): every answer key is confirmed, every negation refuted.

Why `Fin 3` is enough here: with `n` predicate letters a countermodel to a syllogistic
inference needs at most one witness per existential premise plus one for the conclusion; the
patterns in the fragment need ≤ 3. (For the strict-order sub-fragment `Fin (k+1)` where `k`
is the number of names.) This is a *sound* bound for these shapes, not a general
finite-model theorem, so the fragment refuses anything it cannot classify.

What the grammar must decide — and where Arabic morphology bites — is *lemma identification*:
«مستطيلات» (indefinite plural) in one premise and «المستطيلات» (definite plural) in the next
are the same predicate; «الطلاب في الصف» vs «طالب في الصف» (broken plural vs singular) too.
The parser keys predicates on a coarse consonantal skeleton (article and sound-plural/
feminine suffixes ‑ات/‑ون/‑ين/‑ة stripped, long vowels ا/و/ي deleted, one derivational
prefix م/ت/ي dropped — so مبتلة and تبتل, طالب and الطلاب coincide), and — crucially — refuses to translate when the conclusion contains a
predicate that appears in no premise (e.g. «عدد أولي» after premises about «فردي»): a
sound encoding would then be trivially refutable and would blame Falcon for the grammar's
gap. Each identification is written into the certificate shown in the UI
(`B := مستطيلات ≡ المستطيلات`), so the faithfulness of the translation is auditable by a
human reader, not just asserted. Anything with arithmetic inside an atom («١٨ زوجي»,
«يقبل القسمة على ٢») is *not* treated as a propositional letter and stays with the arithmetic
fragment / LLM path.

**Teaching with the witness.** Because the encoding is a finite model, the same parser can
*exhibit* the countermodel Lean's `decide` found (`arabic_logic.countermodel`): when Falcon
answers «نعم» to an invalid inference, the feedback it receives is not "Lean says no" but a
concrete Arabic situation —

> مثال مضاد (عالم من العناصر x0، x1، x2): «الأطباء» = {x0}، «متعلمون» = {x0، x1}، «أثرياء» = {x1}.
> في هذا الوضع كل المقدمات صحيحة ولكن «بعض الأطباء أثرياء» خاطئة.

— chosen among all witnesses to keep every class inhabited (an empty class of doctors is a
valid but unconvincing refutation). Conversely a wrong «لا» to a valid inference is told
that the closed statement is a theorem and asked to re-derive the chain. The feedback thus
names the polarity Lean established; the student still has to produce the corrected
reasoning, which is what the revised-answer rounds record.

### 5c. The counting fragment: symmetric relations and the handshake lemma (`falconverifier.arabic_graph`)

The unary fragment above cannot say anything about a *relation between two people*. Running the
classic puzzle

> خمسة طلاب يجلسون في الفصل، ويقول كل واحد منهم إن ثلاثة من الأربعة الباقين أصدقاؤه. هل يلزم أن أحدهم يكذب؟

through the LLM formalizer exposed exactly the failure this project is about: the 34B model
flattened *friendship* into a per-student `Bool` (`students : Fin 5 → Bool`) — losing that the
relation is binary and mutual — and Lean dutifully refuted the wrong proposition, producing a
false alarm against a Falcon answer that was actually right. A second attempt kept the relation
binary but dropped symmetry, and `decide` over `Fin 5 → Fin 5 → Bool` (2^25 relations) timed out.

The counting fragment recognises the regular-graph family — «n people, each is a friend of /
shook hands with / knows exactly k of the others», followed by «هل يلزم أن أحدهم يكذب؟» or
«هل يمكن ذلك؟» — and emits, with a certificate that records where symmetry came from
(`symmetry stated («متبادلة»)` vs `symmetry assumed from lexeme «أصدقاؤه»`):

```lean
∀ f : Fin 5 → Fin 5 → Bool, ¬ FalconVerifier.Regular f 3   -- «someone must be lying»
∃ f : Fin 6 → Fin 6 → Bool,   FalconVerifier.Regular f 3   -- «is it possible?»
```

`Regular f k` (lean/FalconVerifier/Graph.lean) says `f` is symmetric, irreflexive and every vertex
has exactly `k` neighbours. Lean settles these claims with *lemmas*, never by enumeration:

| situation | Lean | proof |
|---|---|---|
| `n·k` odd | `no_regular_of_odd` | handshake lemma via Mathlib `SimpleGraph.sum_degrees_eq_twice_card_edges` |
| `k ≥ n` | `no_regular_of_ge` | degree ≤ n−1 (`Finset.card_le_card` on the neighbour set) |
| `n·k` even, `k < n` | `circulant n k` | explicit witness, `Regular (circulant n k) k := by decide` |

`lean_runner` routes any claim mentioning `FalconVerifier.Regular` to a dedicated tactic
cascade (`fv_graph`) without a generic `decide`; the six claims of the integration test settle
in ≈4 s. All 40 admissible `(n, k)` pairs with `2 ≤ n ≤ 12`, `k ≤ 9` are checked as circulant
witnesses. The teaching feedback (`arabic_graph.explanation`) gives the parity argument in
Arabic (`5 × 3 = 15` is odd but every friendship is counted twice) or describes the circulant
construction («رتّب الأشخاص في دائرة …»).

**Round-trip faithfulness for the LLM path.** Outside the fragments the formalizer is still an
LLM, so the same structure loss can recur. `Formalizer.audit_roundtrip` now asks the LLM only to
*extract a signature* of the question (does it involve a binary relation between individuals? is
it symmetric? which counts does the claim structurally depend on?), reads the same signature off
the Lean proposition mechanically (`prop_signature`: a `Fin n → Fin n → Bool` binder or an order
over ℤ is binary; `Regular`/`f x y = f y x` marks symmetry; literals are the counts) and compares
them deterministically (`compare_signatures`). Only *structure loss* is rejected — relation
flattened to unary, symmetry dropped, a structural count absent — and a rejection downgrades the
verdict to `unknown` instead of blaming Falcon. Legitimate abstraction (syllogisms as unary
predicates, orderings as integers, facts as propositional letters) passes; a first design that
asked the LLM to back-translate the Lean into Arabic and judge equivalence rejected all of these
and was discarded.

## 6. Research directions (not needed for the demo)

- **Feature-indexed types as dependent types.** Bargelli–Lambek's indexed atoms are a
  product of finite feature sets; in Lean these are naturally `Fin`-indexed families, and
  the "agreement invariant" becomes a typing rule rather than a post-hoc weight. Extending
  the Python lexicon to full verb paradigms is mechanical but large.
- **Beyond pregroups.** Pregroups are *rigid* (no copying/deleting of resources), which is
  why pro-drop and clitic doubling need lexical tricks. Lambek calculus with structural
  modalities, or the categorial "type-logical grammar" of Moortgat, handle these more
  faithfully; DisCoCat's categorical semantics (compact closed / rigid monoidal categories)
  lifts to any of them.
- **Higher categories.** Word order alternations that preserve meaning are 2-cells between
  derivations; a bicategorical semantics would let us *prove* VSO ≡ SVO once, as a natural
  isomorphism, instead of per-lexicon. This is the "∞-categorical encoding" direction —
  open research, deliberately out of scope here.

## References

- J. Lambek, *Type grammar revisited*, LACL 1997 / *Pregroups: a new algebraic approach to
  sentence structure*, 1999.
- D. Bargelli and J. Lambek, *An algebraic approach to Arabic sentence structure*,
  Linguistic Analysis 31 (2001) 301–315; extended in *An algebraic approach to the
  syntax of Arabic*, McGill preprint (2003). https://www.math.mcgill.ca/barr/lambek/pdffiles/arabic.pdf
- B. Coecke, M. Sadrzadeh, S. Clark, *Mathematical foundations for a compositional
  distributional model of meaning*, Linguistic Analysis 36 (2010). (DisCoCat)
- M. Moortgat, *Categorial type logics*, Handbook of Logic and Language (1997).
- Recent work on pregroup parsing of Arabic verb phrases and on Arabic math-word-problem
  benchmarks was consulted for the fragment design; see the slide deck for pointers.
