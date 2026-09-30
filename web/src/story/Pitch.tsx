import { ArrowRight } from '@phosphor-icons/react'
import { motion, useInView, useReducedMotion } from 'motion/react'
import { useRef, type ReactNode } from 'react'
import { isolateMath } from '../components/ArabicText'
import { Lean } from '../components/Lean'
import { Turnstile } from '../components/Mark'
import { Container, Heading, Lede } from '../components/Section'
import { VerdictBadge } from '../components/Verdict'
import type { Text } from '../i18n'
import { useLang } from '../i18n'
import type { Arm } from '../lib/types'

const EASE = [0.23, 1, 0.32, 1] as const

function useReveal(amount = 0.3) {
  const ref = useRef<HTMLDivElement>(null)
  const inView = useInView(ref, { once: true, amount })
  const reduce = !!useReducedMotion()
  const show = (delay: number) => ({
    initial: reduce ? false : { opacity: 0, y: 10, filter: 'blur(4px)' },
    animate: inView ? { opacity: 1, y: 0, filter: 'blur(0px)', transitionEnd: { filter: 'none' } } : {},
    transition: { duration: 0.6, delay: reduce ? 0 : delay, ease: EASE },
  })
  return { ref, show }
}

function Panel({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`rounded-[var(--radius-panel)] bg-panel p-6 ${className}`}>{children}</div>
}

function Kicker({ children }: { children: ReactNode }) {
  return <div className="text-[13px] font-medium uppercase tracking-[0.14em] text-ink-2">{children}</div>
}

/* ---------------------------------------------------------------- Value */

export function Value({ arm }: { arm: Arm }) {
  const { t } = useLang()
  const { ref, show } = useReveal()
  const s = arm.summary.all
  const pct = (v: number | null) => (v == null ? '—' : `${Math.round(v * 100)}%`)

  const cards: { n: string; title: Text; body: Text }[] = [
    {
      n: pct(s.detection_recall),
      title: { en: 'of wrong answers caught', ar: 'من الإجابات الخاطئة تُكتشف' },
      body: {
        en: 'Before they reach a customer. The kernel refutes the step, not a heuristic.',
        ar: 'قبل أن تصل إلى العميل. النواة تدحض الخطوة، لا استدلال تقريبي.',
      },
    },
    {
      n: pct(s.fix_rate),
      title: { en: 'corrected by Falcon itself', ar: 'يصحّحها فالكون نفسه' },
      body: {
        en: 'One Arabic correction from Lean, one more round. No fine-tuning, no second model.',
        ar: 'تصحيح عربي واحد من Lean، وجولة إضافية. بلا ضبط دقيق، بلا نموذج ثانٍ.',
      },
    },
    {
      n: pct(s.false_alarm_rate),
      title: { en: 'false alarms on right answers', ar: 'إنذارات كاذبة على الإجابات الصحيحة' },
      body: {
        en: 'A proof is a proof. Correct answers pass untouched; undecided ones are labelled, never blocked.',
        ar: 'البرهان برهان. الإجابات الصحيحة تمرّ، وغير المحسومة تُعلَّم ولا تُحجب.',
      },
    },
  ]

  return (
    <section className="py-[clamp(96px,14vh,168px)]">
      <Container>
        <Heading className="max-w-[18ch]">{t({ en: 'A wrong answer costs more than a slow one.', ar: 'الجواب الخاطئ أغلى من الجواب البطيء.' })}</Heading>
        <Lede className="mt-5">
          {t({
            en: `Measured on ${s.n} Arabic questions with Falcon-H1-Arabic 3B. Same model, same prompt; only the audit layer added.`,
            ar: `مقاسة على ${s.n} سؤالاً عربياً مع Falcon-H1-Arabic 3B. النموذج نفسه والمحفّز نفسه؛ أُضيفت طبقة التدقيق فقط.`,
          })}
        </Lede>
        <div ref={ref} className="mt-14 grid gap-5 md:grid-cols-3">
          {cards.map((c, i) => (
            <motion.div key={i} {...show(0.12 * i)}>
              <Panel className="h-full">
                <div className={`num text-[clamp(48px,5vw,72px)] font-semibold leading-none tracking-[-0.04em] ${i === 2 ? 'text-ink' : 'text-verified'}`}>
                  {c.n}
                </div>
                <div className="mt-3 text-[18px] font-medium">{t(c.title)}</div>
                <p className="mt-2 text-[15px] leading-[1.6] text-ink-2">{t(c.body)}</p>
              </Panel>
            </motion.div>
          ))}
        </div>
      </Container>
    </section>
  )
}

/* -------------------------------------------------------------- Arabic */

const ARABIC: { kind: Text; ar: string; lean: string; verdict: 'verified' | 'refuted' | 'unverified_premise' }[] = [
  {
    kind: { en: 'Everyday arithmetic', ar: 'حساب يومي' },
    ar: 'الفاتورة 240 ريالاً، مع ضريبة 15% تصبح 276 ريالاً.',
    lean: '(240:ℚ) * (1 + 15/100) = 276',
    verdict: 'verified',
  },
  {
    kind: { en: 'Dates and time', ar: 'التواريخ والوقت' },
    ar: 'اليوم الثلاثاء، فبعد 10 أيام يكون يوم الخميس.',
    lean: '(2 + 10) % 7 = 4',
    verdict: 'refuted',
  },
  {
    kind: { en: 'Logic and quantifiers', ar: 'المنطق والأسوار' },
    ar: 'كل موظف لديه بطاقة، وسعيد موظف، إذن لدى سعيد بطاقة.',
    lean: '(∀ x, E x → C x) → E s → C s',
    verdict: 'verified',
  },
  {
    kind: { en: 'World knowledge', ar: 'معرفة بالعالم' },
    ar: 'مكة في السعودية، لذلك العملة هي الريال.',
    lean: '— premise, not for Lean —',
    verdict: 'unverified_premise',
  },
]

export function ArabicCapability() {
  const { t } = useLang()
  const { ref, show } = useReveal()
  return (
    <section className="border-t border-rule py-[clamp(96px,14vh,168px)]">
      <Container>
        <Heading className="max-w-[18ch]">{t({ en: 'Arabic in, Lean out.', ar: 'عربية تدخل، وLean يخرج.' })}</Heading>
        <Lede className="mt-5">
          {t({
            en: 'A pregroup grammar reads Arabic sentences directly, VSO or SVO, Eastern or Western digits, and writes the Lean proposition itself. When it cannot, it says so instead of guessing.',
            ar: 'قواعد pregroup تقرأ الجملة العربية مباشرة، فعلية أو اسمية، بأرقام مشرقية أو غربية، وتكتب قضية Lean بنفسها. وحين لا تستطيع، تقول ذلك بدل التخمين.',
          })}
        </Lede>
        <div ref={ref} className="mt-14 grid gap-4 md:grid-cols-2">
          {ARABIC.map((c, i) => (
            <motion.div key={i} {...show(0.1 * i)}>
              <Panel className="flex h-full flex-col gap-3">
                <Kicker>{t(c.kind)}</Kicker>
                <p lang="ar" dir="rtl" className="font-ar text-[18px] leading-[1.7] text-ink">
                  {isolateMath(c.ar)}
                </p>
                <div className="mt-auto flex flex-wrap items-center justify-between gap-3 border-t border-rule pt-3">
                  {c.verdict === 'unverified_premise' ? (
                    <span className="text-[14px] text-ink-3">{t({ en: 'Not a claim for the kernel', ar: 'ليست ادعاءً للنواة' })}</span>
                  ) : (
                    <Lean className="text-[15px]">{c.lean}</Lean>
                  )}
                  <VerdictBadge verdict={c.verdict} />
                </div>
              </Panel>
            </motion.div>
          ))}
        </div>
      </Container>
    </section>
  )
}

/* -------------------------------------------------------- Architecture */

export function Architecture() {
  const { t } = useLang()
  const { ref, show } = useReveal()
  const nodes: { label: Text; sub: Text; kind: 'app' | 'falcon' | 'kernel' | 'out' }[] = [
    { label: { en: 'Your app', ar: 'تطبيقك' }, sub: { en: 'chat, API, agent', ar: 'محادثة، API، وكيل' }, kind: 'app' },
    { label: { en: 'Falcon', ar: 'فالكون' }, sub: { en: 'unchanged', ar: 'بلا تغيير' }, kind: 'falcon' },
    { label: { en: 'NYU Falcon', ar: 'NYU Falcon' }, sub: { en: 'formalize · prove · correct', ar: 'صياغة · برهان · تصحيح' }, kind: 'kernel' },
    { label: { en: 'Verified answer', ar: 'جواب مُثبَت' }, sub: { en: '+ audit trace', ar: '+ سجل تدقيق' }, kind: 'out' },
  ]
  return (
    <section className="border-t border-rule py-[clamp(96px,14vh,168px)]">
      <Container>
        <Heading className="max-w-[18ch]">{t({ en: 'A layer, not a model.', ar: 'طبقة، لا نموذج.' })}</Heading>
        <Lede className="mt-5">
          {t({
            en: 'Drop it between Falcon and your product. One HTTP call in, one verified answer and its proof trace out.',
            ar: 'ضعه بين فالكون ومنتجك. طلب HTTP واحد يدخل، وجواب مُثبَت مع سجل برهانه يخرج.',
          })}
        </Lede>

        <div ref={ref} className="mt-14">
          <Panel className="p-6 sm:p-10">
            <div className="grid items-center gap-4 lg:grid-cols-[1fr_auto_1fr_auto_1.4fr_auto_1fr]">
              {nodes.map((n, i) => (
                <div key={i} className="contents">
                  {i > 0 && (
                    <motion.div {...show(0.15 * i)} className="flex justify-center text-ink-3">
                      <ArrowRight size={28} className="rotate-90 lg:rotate-0 rtl:lg:rotate-180" aria-hidden />
                    </motion.div>
                  )}
                  <motion.div
                    {...show(0.15 * i)}
                    className={`rounded-xl border p-5 text-center ${
                      n.kind === 'kernel' ? 'border-ink bg-ink text-paper' : 'border-rule-strong bg-paper text-ink'
                    }`}
                  >
                    <div className="flex items-center justify-center gap-2 text-[18px] font-semibold tracking-[-0.02em]">
                      {n.kind === 'kernel' && <Turnstile className="size-[16px]" />}
                      {t(n.label)}
                    </div>
                    <div className={`mt-1 text-[14px] ${n.kind === 'kernel' ? 'text-paper/70' : 'text-ink-3'}`}>{t(n.sub)}</div>
                  </motion.div>
                </div>
              ))}
            </div>
            <motion.div {...show(0.7)} className="mt-6 flex items-center justify-center gap-2 text-[14px] text-refuted">
              <span className="h-px w-10 border-t-2 border-dashed border-refuted-bright" />
              {t({ en: 'refuted step → Arabic correction → Falcon retries', ar: 'خطوة مدحوضة ← تصحيح عربي ← فالكون يعيد المحاولة' })}
              <span className="h-px w-10 border-t-2 border-dashed border-refuted-bright" />
            </motion.div>
          </Panel>

          <ul className="mt-8 grid gap-x-10 gap-y-3 text-[16px] text-ink-2 sm:grid-cols-3">
            <Fact>{t({ en: 'Zero fine-tuning. Falcon weights untouched.', ar: 'بلا ضبط دقيق. أوزان فالكون كما هي.' })}</Fact>
            <Fact>{t({ en: 'One Lean kernel process per deployment.', ar: 'عملية نواة Lean واحدة لكل نشر.' })}</Fact>
            <Fact>{t({ en: 'Every verdict ships with its proposition and proof.', ar: 'كل حكم يأتي مع قضيته وبرهانه.' })}</Fact>
          </ul>
        </div>
      </Container>
    </section>
  )
}

function Fact({ children }: { children: ReactNode }) {
  return (
    <li className="flex items-start gap-3">
      <span className="mt-[9px] size-2 shrink-0 rounded-full bg-ink" />
      <span>{children}</span>
    </li>
  )
}

/* ------------------------------------------------------------ Use cases */

const CASES: { sector: Text; title: Text; ar: string; en: string }[] = [
  {
    sector: { en: 'Banking & fintech', ar: 'البنوك والتقنية المالية' },
    title: { en: 'Fees, instalments, exchange rates', ar: 'الرسوم والأقساط وأسعار الصرف' },
    ar: 'قسط 12 شهراً على 4800 درهم برسوم 2% هو 408 دراهم.',
    en: 'A 12-month instalment on 4800 AED with a 2% fee is 408 AED.',
  },
  {
    sector: { en: 'Government services', ar: 'الخدمات الحكومية' },
    title: { en: 'Deadlines, eligibility, dates', ar: 'المواعيد والأهلية والتواريخ' },
    ar: 'التجديد خلال 30 يوماً من 15 رمضان ينتهي في 15 شوال.',
    en: 'Renewal within 30 days of 15 Ramadan ends on 15 Shawwal.',
  },
  {
    sector: { en: 'Customer support', ar: 'خدمة العملاء' },
    title: { en: 'Refunds, quotas, plan changes', ar: 'الاسترداد والحصص وتغيير الباقات' },
    ar: 'استهلكت 18 من 20 جيجابايت، فبقي لك 2 جيجابايت.',
    en: 'You used 18 of 20 GB, so 2 GB remain.',
  },
  {
    sector: { en: 'Education', ar: 'التعليم' },
    title: { en: 'Step-checked Arabic tutoring', ar: 'تدريس عربي مُدقَّق خطوة بخطوة' },
    ar: 'مجموع زوايا المثلث 180، فالزاوية الثالثة 180 − 70 − 55 = 55.',
    en: 'A triangle’s angles sum to 180, so the third is 180 − 70 − 55 = 55.',
  },
]

export function UseCases() {
  const { t, isAr } = useLang()
  const { ref, show } = useReveal()
  return (
    <section className="border-t border-rule py-[clamp(96px,14vh,168px)]">
      <Container>
        <Heading className="max-w-[18ch]">{t({ en: 'Where Arabic answers carry money and deadlines.', ar: 'حيث تحمل الإجابات العربية مالاً ومواعيد.' })}</Heading>
        <Lede className="mt-5">
          {t({
            en: 'The same kernel checks the arithmetic, dates and logic that sit inside everyday enterprise conversations.',
            ar: 'النواة ذاتها تفحص الحساب والتواريخ والمنطق داخل المحادثات المؤسسية اليومية.',
          })}
        </Lede>
        <div ref={ref} className="mt-14 grid gap-4 sm:grid-cols-2">
          {CASES.map((c, i) => (
            <motion.div key={i} {...show(0.1 * i)}>
              <div className="flex h-full flex-col gap-3 rounded-[var(--radius-panel)] border border-rule p-6">
                <Kicker>{t(c.sector)}</Kicker>
                <div className="text-[20px] font-semibold tracking-[-0.02em]">{t(c.title)}</div>
                <p lang="ar" dir="rtl" className="mt-auto font-ar text-[17px] leading-[1.7] text-ink-2">
                  {isolateMath(c.ar)}
                </p>
                {!isAr && <p className="text-[13px] leading-snug text-ink-3">{c.en}</p>}
              </div>
            </motion.div>
          ))}
        </div>
      </Container>
    </section>
  )
}

/* ------------------------------------------------------- Under the hood */

const HOOD: { k: Text; v: Text; code?: string }[] = [
  { k: { en: 'Verdict authority', ar: 'مرجع الحكم' }, v: { en: 'Lean 4 kernel + Mathlib. LLM output is never evidence.', ar: 'نواة Lean 4 مع Mathlib. مخرجات النموذج ليست دليلاً أبداً.' } },
  { k: { en: 'Formalization', ar: 'الصياغة' }, v: { en: 'Deterministic Arabic pregroup fragments first; Falcon-34B formalizer only when they decline.', ar: 'قطع pregroup عربية حتمية أولاً؛ صائغ Falcon-34B فقط حين تمتنع.' } },
  { k: { en: 'Proof search', ar: 'البحث عن البرهان' }, v: { en: 'Tactic cascade over each claim and its negation.', ar: 'سلسلة تكتيكات على كل ادعاء ونفيه.' }, code: 'fv_auto := decide | norm_num | omega | linarith' },
  { k: { en: 'Faithfulness', ar: 'الأمانة' }, v: { en: 'LLM translations are back-translated and structurally audited; a mismatch downgrades to undecided.', ar: 'ترجمات النموذج تُعاد ترجمتها وتُدقَّق بنيوياً؛ الاختلاف يخفّض الحكم إلى غير محسوم.' } },
  { k: { en: 'Facts vs. inference', ar: 'الحقائق والاستدلال' }, v: { en: 'World-knowledge premises are marked, never refuted.', ar: 'مقدّمات المعرفة بالعالم تُعلَّم ولا تُدحض.' } },
  { k: { en: 'Memory', ar: 'الذاكرة' }, v: { en: 'Kernel verdicts and checked translations are cached by proposition and toolchain hash. Falcon answers never are.', ar: 'أحكام النواة والترجمات المفحوصة تُخزَّن حسب القضية وبصمة الأدوات. إجابات فالكون لا تُخزَّن.' } },
  { k: { en: 'Deployment', ar: 'النشر' }, v: { en: 'FastAPI + one Lean process, single Docker image, SSE stream or JSON.', ar: 'FastAPI وعملية Lean واحدة، صورة Docker واحدة، بث SSE أو JSON.' }, code: 'POST /api/solve  { problem, rounds }' },
]

export function UnderHood() {
  const { t } = useLang()
  const { ref, show } = useReveal(0.2)
  return (
    <section className="border-t border-rule py-[clamp(96px,14vh,168px)]">
      <Container>
        <Heading className="max-w-[16ch]">{t({ en: 'Under the hood.', ar: 'تحت الغطاء.' })}</Heading>
        <div ref={ref} className="mt-12 border-t border-ink">
          {HOOD.map((h, i) => (
            <motion.div
              key={i}
              {...show(0.06 * i)}
              className="grid gap-x-8 gap-y-1 border-b border-rule py-4 md:grid-cols-[200px_1fr]"
            >
              <div className="text-[14px] font-medium text-ink-2">{t(h.k)}</div>
              <div className="text-[16px] leading-[1.55] text-ink">
                {t(h.v)}
                {h.code && (
                  <div className="mt-1.5">
                    <Lean className="text-[14px] text-ink-2">{h.code}</Lean>
                  </div>
                )}
              </div>
            </motion.div>
          ))}
        </div>
      </Container>
    </section>
  )
}
