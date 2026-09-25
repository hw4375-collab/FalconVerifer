---
name: NYU Falcon
description: A research figure that argues one claim — the Lean kernel catches and corrects Falcon's Arabic reasoning.
colors:
  paper: "#fafaf8"
  panel: "#f1f2ef"
  ink: "#16181b"
  ink-2: "#4f555c"
  ink-3: "#686e75"
  rule: "#dfe1dd"
  rule-strong: "#c9ccc7"
  verified: "#0b7a4b"
  verified-bright: "#12935c"
  verified-wash: "#e3f1e8"
  refuted: "#c8381f"
  refuted-bright: "#e0442a"
  refuted-wash: "#fae7e2"
  unknown: "#9a5b00"
  unknown-bright: "#c27a0e"
  unknown-wash: "#f6ecd9"
  skip: "#8c9198"
typography:
  display:
    fontFamily: "Schibsted Grotesk Variable, Readex Pro Variable, system-ui, sans-serif"
    fontSize: "clamp(44px, 5.4vw, 78px)"
    fontWeight: 600
    lineHeight: 1.02
    letterSpacing: "-0.038em"
  headline:
    fontFamily: "Schibsted Grotesk Variable, Readex Pro Variable, system-ui, sans-serif"
    fontSize: "clamp(34px, 4.6vw, 60px)"
    fontWeight: 600
    lineHeight: 1.04
    letterSpacing: "-0.032em"
  title:
    fontFamily: "Schibsted Grotesk Variable, Readex Pro Variable, system-ui, sans-serif"
    fontSize: "clamp(24px, 2.4vw, 32px)"
    fontWeight: 600
    letterSpacing: "-0.025em"
  lede:
    fontFamily: "Schibsted Grotesk Variable, Readex Pro Variable, system-ui, sans-serif"
    fontSize: "clamp(17px, 1.5vw, 20px)"
    fontWeight: 400
    lineHeight: 1.5
  body:
    fontFamily: "Schibsted Grotesk Variable, Readex Pro Variable, system-ui, sans-serif"
    fontSize: "15px"
    fontWeight: 400
    lineHeight: 1.6
  arabic:
    fontFamily: "Readex Pro Variable, Schibsted Grotesk Variable, system-ui, sans-serif"
    fontSize: "17px"
    fontWeight: 400
    lineHeight: 1.7
  label:
    fontFamily: "Schibsted Grotesk Variable, Readex Pro Variable, system-ui, sans-serif"
    fontSize: "13px"
    fontWeight: 500
  code:
    fontFamily: "FV Mono, ui-monospace, Menlo, monospace"
    fontSize: "15px"
    fontWeight: 400
rounded:
  mark: "4px"
  panel: "12px"
  card: "20px"
  control: "9999px"
spacing:
  gutter: "20px"
  gutter-md: "32px"
  container: "1320px"
  section: "clamp(96px, 14vh, 168px)"
components:
  button-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
    padding: "12px 24px"
  button-quiet:
    textColor: "{colors.ink}"
    rounded: "{rounded.control}"
    padding: "12px 24px"
  chip-filter:
    textColor: "{colors.ink-2}"
    rounded: "{rounded.control}"
    padding: "6px 14px"
  chip-filter-selected:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.control}"
  verdict-proved:
    backgroundColor: "{colors.verified-wash}"
    textColor: "{colors.verified}"
    rounded: "{rounded.control}"
  verdict-refuted:
    backgroundColor: "{colors.refuted-wash}"
    textColor: "{colors.refuted}"
    rounded: "{rounded.control}"
  verdict-undecided:
    backgroundColor: "{colors.unknown-wash}"
    textColor: "{colors.unknown}"
    rounded: "{rounded.control}"
  figure-panel:
    backgroundColor: "{colors.panel}"
    rounded: "{rounded.panel}"
    padding: "32px"
  answer-card:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.card}"
    padding: "24px"
---

# Design System: NYU Falcon

## Overview

**Creative North Star: "The Research Figure"**

The site is one explorable figure from a paper, not a product landing page. Every screen argues a single
claim: Falcon writes fluent Arabic, the Lean 4 kernel checks each step, and a refutation goes back to
Falcon as a correction. Diagrams, arrows and real traces carry the argument. Prose is limited to a
headline, one sentence and a caption.

The surface is light paper, because the site is presented on a projector. Grey ink sets the hierarchy.
Color is data: green means proved, vermilion means refuted, amber means undecided, and nothing else on
the page is colored. Arabic is primary content. It is set right to left in Readex Pro with its own
rhythm, never as a translation afterthought. English appears as a quiet gloss beside it, and the whole
interface flips to right to left when the reader switches language.

**Key Characteristics:**
- Paper and ink, with color reserved for kernel verdicts.
- Figures in 12px panels. Controls are pills. Text never sits in decorative boxes.
- One motion vocabulary: enter from 8–10px with a light blur, and draw lines along their path.
- Real data only. Every number and example is exported from `bench/results/`.

## Colors

The palette is neutral paper and ink, plus three verdict hues validated for color-vision deficiency.

### Verdicts
- **Proved Green** (#0b7a4b; bright #12935c; wash #e3f1e8): a claim the kernel proved, an answer
  fixed by the loop, and the "after the loop" series in charts.
- **Refuted Vermilion** (#c8381f; bright #e0442a; wash #fae7e2): a claim the kernel refuted, a wrong
  answer, and the correction sent back to Falcon.
- **Undecided Amber** (#9a5b00; bright #c27a0e; wash #f6ecd9): unknown or ill-formed verdicts, false
  alarms, and broken answers.
- **Skip Grey** (#8c9198): a step with no checkable claim. In the coverage chart it marks "undecided",
  while "not checkable" (no claim, or an unchecked world-knowledge premise) is Rule strong.

The text shades (`verified`, `refuted`, `unknown`) are for words. The bright shades are for marks: dots,
bars and chart segments. Washes sit behind a highlighted row. Proved green against refuted vermilion
passes the CVD check at ΔE 8.5. Amber against vermilion does not, so amber never sits next to
vermilion without a label.

### Neutral
- **Paper** (#fafaf8): the page.
- **Panel** (#f1f2ef): figure panels, the demo sidebar, and hover fills.
- **Ink** (#16181b): headlines, primary text, the primary button and the kernel node.
- **Ink 2** (#4f555c): body copy and secondary labels.
- **Ink 3** (#686e75): captions, glosses, axis labels and ids. It is 4.9:1 on paper and 4.6:1 on
  panel, and must stay at or above 4.5:1.
- **Rule** (#dfe1dd) and **Rule strong** (#c9ccc7): dividers, card edges and inactive diagram strokes.

### Named Rules
**The Color Is Data Rule.** Green, vermilion and amber appear only where the kernel returned that
verdict, or a chart encodes it. There are no brand accents, gradients or decorative color. The
ChaosButterfly mark keeps its own navy (#0f1f3a) because it is an image, not an interface color.

**The Label Beside Color Rule.** Every colored verdict ships with an icon and a word (✓ proved,
✕ refuted). Chart series ship with a legend. Color never carries meaning alone.

## Typography

**Display and body:** Schibsted Grotesk (variable)
**Arabic:** Readex Pro (variable). The `:lang(ar)` and `[dir=rtl]` selectors switch to it.
**Code:** FV Mono, a JuliaMono subset kept for its ℕ ℚ ∀ ∃ ¬ → glyphs in Lean propositions.

**Character:** a tight, newsy grotesk for claims, paired with a round, open Arabic face. Lean code
always reads as code.

### Hierarchy
- **Display** (600, clamp(44px, 5.4vw, 78px), 1.02, −0.038em): the hero statement only.
- **Headline** (600, clamp(34px, 4.6vw, 60px), 1.04, −0.032em): one per story section, written as a
  claim ("Same Falcon. Thirty points better.").
- **Title** (600, clamp(24px, 2.4vw, 32px), −0.025em): results sections and Loop captions.
- **Lede** (400, clamp(17px, 1.5vw, 20px), 1.5, max 46ch): the one sentence under a headline.
- **Arabic body** (400, 17px, 1.6–1.8): questions, claims and corrections.
- **Label** (500, 13–14px): chips, legends and table heads.

### Named Rules
**The Math Stays Left-to-Right Rule.** Western-digit equations inside Arabic text are isolated with
`isolateMath()`. Each run is a left-to-right `<bdi>` inline block, so "59 × 41 = 2419" is never reordered
or split across lines. Lean propositions always render `dir="ltr"`.

**The Tabular Numbers Rule.** Every changing or compared number uses the `.num` utility
(tabular figures).

## Layout

The container is 1320px wide, with 20px gutters (32px from `md`). Story sections breathe at
clamp(96px, 14vh, 168px) of vertical padding.

The hero is split: headline and actions on the left 5 of 12 columns, the live figure on the right 7.
The Loop section pins its figure (`sticky`) beside five captions of 72vh each, and scroll progress picks
the active step. Below `lg` it becomes a static sequence, with each step getting its own frame. Results
read top to bottom: run picker, headline, outcome flow, two charts side by side, then the problem
table. The demo is an app shell: a 272px sidebar (a drawer below `lg`) and a thread centered at a
readable width.

Figures draw from their rendered width through `useWidth()`. SVG text stays at true pixel size on
phones instead of shrinking with the viewBox.

## Elevation & Depth

The system is flat and tonal. Depth comes from paper, panel and rules, not shadows.

### Shadow Vocabulary
- **Float** (`0 1px 2px rgb(22 24 27 / 0.05), 0 6px 14px -6px rgb(22 24 27 / 0.14)`): floating
  layers only, meaning tooltips and the model popover.

### Named Rules
**The Edge Or Lift Rule.** An in-flow element gets a defined 1px edge. A floating layer gets an edge and
the float shadow. Never put a wide diffuse shadow on a card, input or button.

## Shapes

Radii come from a small, fixed set:
- 4px on chart marks
- 12px on figure panels
- 20px on demo answer cards
- a full pill on every interactive control (buttons, chips, verdict badges, nav items)

Diagram strokes are 2px with round caps. Arrowheads are open chevrons, not filled triangles.

Tables are open: an ink top rule and hairline row dividers, with no enclosing box. Cards never nest.

## Components

### Buttons
- **Shape:** pill (9999px).
- **Primary:** ink fill, paper text, 12px × 24px, 16px medium. Hover deepens to #2a2d31.
- **Quiet:** text only, same size. Used for the secondary action beside a primary.
- **Press:** every pressable element uses `.press`, which scales to 0.97 on `:active` over 160ms.
- **Focus:** 2px ink outline via `:focus-visible`.

### Chips
- **Filter chips** (results table): a pill with a rule edge, ink-2 text and a count. Selected is ink
  fill with paper text. A color dot mirrors the dot chart's encoding.
- **Pipeline chips** (demo): "Falcon, round N" → "Lean 4 ✓/✕" → "correction", joined by carets that
  flip in RTL.

### Verdict Badge
A pill with a wash background, verdict-colored text and a Phosphor icon: proved ✓, refuted ✕,
undecided −, ill-formed ?, no claim. An unchecked premise (a world-knowledge step Lean cannot judge) is
the one exception: no wash and no verdict color, just a dashed rule-strong outline, ink-2 text and a
globe icon, because the kernel decided nothing. Labels come from `VERDICT_LABEL` in both languages.

### Figure Panels
Panel fill with a 12px radius and 20–32px padding, and no border or shadow. Every story diagram and the
grammar derivation sits in one.

### Answer Cards (demo)
Paper fill with a 20px radius and a 1px edge. The baseline card uses the rule edge. The verified card
uses `ink/30` to stand forward, with no shadow. The final answer is set large and colored by verdict,
and the reasoning and the proof sit behind disclosures.

### Composer
A pill-ended field with a rule-strong edge that turns ink on focus. Enter sends and Shift+Enter adds a
new line. It moves from the empty state's center to the thread's foot through a shared `layoutId`.

### Navigation
A sticky 64px bar on paper at 95%. Its bottom rule appears after 8px of scroll. The active item is a
panel pill that slides between links (`layoutId`, spring 0.45s). The wordmark is the ChaosButterfly mark
followed by "NYU Falcon"; below `sm` it collapses to the mark alone. The language toggle names the other
language in its own script.

### Footer and Assets
The ChaosButterfly mark (`public/brand/chaosbutterfly-mark.png`, 480 × 335) is the product mark and the
site's only raster. The team supplied it on 25 September 2026 as a PNG on white. The white was removed by
computing each pixel's alpha from its darkness against the mark's own navy (#0f1f3a), and every pixel takes
that navy, so the edges carry no white fringe. `public/favicon.png` is the same mark on a paper-coloured
rounded square. The ⊢ symbol is authored SVG and stands for the Lean kernel only (diagram nodes and the
demo's Lean avatar). FV Mono is a subset of JuliaMono, shipped with its OFL license
(`public/fonts/FV-MONO-OFL.txt`).

### Signature: Dot Band
One dot per benchmark question: ink for right, bright vermilion for wrong, bright green for fixed.
A missed error is an open vermilion ring, and a false alarm is amber. Dots stagger in on first view, and
only the changed dots recolor when the story reaches the outcome. Hovering or focusing a dot shows the
question, Falcon's answer, the answer after Lean, and the correct answer.

## Motion

- **Easing:** `--ease-out-strong` (0.23, 1, 0.32, 1) for entrances, `--ease-in-out-strong` for lines
  drawn along a path, and `--ease-drawer` for the demo drawer.
- **Entrances:** opacity with an 8–10px offset and a 3–4px blur, clearing to `filter: none` when the
  entrance settles. They run once, on first view.
- **Emphasis:** inactive Loop captions dim to ink-3 and the active one returns to ink. Opacity is
  never the dimming mechanism for text that has to be read. Cancelled pregroup types fade to 30% on
  purpose: the cups show the reduction, and the caption below restates it at full contrast.
- **Reduced motion:** `MotionConfig reducedMotion="user"`, plus a global CSS override that brings every
  transition to 0.01ms. Sequences render in their final state.

## Do's and Don'ts

### Do:
- **Do** show the Lean proposition next to every verdict.
- **Do** set Arabic content with `lang="ar" dir="rtl"`, and isolate equations with `isolateMath()`.
- **Do** use logical properties (`ms`, `pe`, `start`, `end`, `insetInlineStart`) so the layout mirrors
  in Arabic.
- **Do** label replayed traces as "recorded run", and live ones as "live".
- **Do** export any new number from `bench/results/` through `web/scripts/export_data.py`. Never type
  numbers in by hand.

### Don't:
- **Don't** add purple or blue gradients, glassmorphism, glow, or any color that is not a verdict.
- **Don't** add paragraphs of explanation. If a section needs more words, it needs a better diagram.
- **Don't** nest cards, or put a wide soft shadow on in-flow elements.
- **Don't** mirror media icons (play) in RTL. Do mirror flow arrows and carets.
- **Don't** claim fine-tuning results. The preference pairs exist, but training has not been run.
