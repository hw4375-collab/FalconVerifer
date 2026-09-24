from __future__ import annotations

import re

from .arabic import is_arabic, normalize_digits
from .llm import ChatModel
from .schemas import ReasoningStep, StudentAnswer

SYSTEM_PROMPT = """You are a careful math and logic tutor solving problems for a student.

Rules:
1. Reason step by step. Number every step on its own line as `Step 1:`, `Step 2:`, ...
2. Each step must state ONE concrete, checkable claim (an arithmetic equality, an algebraic
   fact, or a logical inference) — e.g. `Step 2: 17 × 20 = 340`.
3. Finish with exactly one line of the form `FINAL ANSWER: <answer>` where <answer> is a
   number, a short expression, or `Yes`/`No` for yes/no questions. Do not write anything
   after that line."""

REVISION_PROMPT = """Your previous solution was checked by a formal proof assistant (Lean 4).
Here is the verification feedback:

{feedback}

Fix ONLY what is wrong. Re-solve the problem from scratch following the same format
(numbered `Step k:` lines, one claim each, then `FINAL ANSWER: <answer>`)."""

SYSTEM_PROMPT_AR = """أنت معلّم رياضيات ومنطق دقيق تحل المسائل لطالب. أجب باللغة العربية فقط.

القواعد:
1. فكّر خطوة بخطوة. رقّم كل خطوة في سطر مستقل بالصيغة `الخطوة 1:`، `الخطوة 2:`، ...
2. كل خطوة تذكر ادعاءًا واحداً محدداً قابلاً للفحص (مساواة حسابية، حقيقة جبرية، أو استنتاج
   منطقي) — مثل `الخطوة 2: 17 × 20 = 340`. استخدم الأرقام الغربية (0-9) والرموز + − × ÷ =.
3. اختم بسطر واحد فقط بالصيغة `الجواب النهائي: <الجواب>` حيث <الجواب> رقم أو تعبير قصير، أو
   `نعم`/`لا` لأسئلة نعم/لا. لا تكتب شيئاً بعد ذلك السطر."""

REVISION_PROMPT_AR = """تم فحص حلك السابق بمساعد برهان صوري (Lean 4). هذه نتيجة التحقق:

{feedback}

صحّح الخطأ فقط. أعد حل المسألة من البداية بنفس الصيغة (أسطر `الخطوة k:` مرقمة، ادعاء واحد في كل
سطر، ثم `الجواب النهائي: <الجواب>`)."""

STEP_RE = re.compile(
    r"^\s*(?:\*\*)?(?:Step|الخطوة|خطوة)\s*([\d٠-٩]+)\s*[:.)\-：]\s*(?:\*\*)?\s*(.*)$", re.I
)
FINAL_RE = re.compile(
    r"(?:FINAL\s*ANSWER|الجواب النهائي|الإجابة النهائية|الاجابة النهائية)\s*(?:\*\*)?\s*(?:[:：]|(?:is|=|هو|هي))"
    r"\s*\**\s*(.+?)\s*\**\s*$",
    re.I | re.M,
)


def _clean_final(raw: str) -> str | None:
    val = normalize_digits(raw).strip().strip("*` .ـ").rstrip(".؛،")
    return val or None


def parse_answer(text: str) -> tuple[list[ReasoningStep], str | None]:
    steps: list[ReasoningStep] = []
    current: list[str] | None = None
    current_idx = 0
    final: str | None = None
    for line in text.splitlines():
        fm = FINAL_RE.search(line)
        if fm and _clean_final(fm.group(1)):
            final = _clean_final(fm.group(1))
            break
        m = STEP_RE.match(line)
        if m:
            if current is not None:
                steps.append(ReasoningStep(index=current_idx, text=" ".join(current).strip()))
            current_idx = int(normalize_digits(m.group(1)))
            current = [m.group(2).strip()]
        elif current is not None and line.strip():
            current.append(line.strip())
    if current is not None:
        steps.append(ReasoningStep(index=current_idx, text=" ".join(current).strip()))
    if final is None:
        m2 = FINAL_RE.search(text)
        if m2:
            final = _clean_final(m2.group(1))
    # Fallback: treat paragraphs / bullet lines as steps if the model ignored the format.
    if not steps:
        chunks = [c.strip() for c in re.split(r"\n\s*\n|\n(?=\s*[-*\d]+[.)]\s)", text) if c.strip()]
        chunks = [c for c in chunks if not FINAL_RE.search(c)]
        steps = [ReasoningStep(index=i + 1, text=c[:600]) for i, c in enumerate(chunks[:12])]
    return steps, final


class Student:
    """Wraps the model under test (Falcon) as a student who solves and revises."""

    def __init__(self, model: ChatModel, temperature: float = 0.0, max_tokens: int = 1500):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def solve(self, problem: str, history: list[dict[str, str]] | None = None) -> StudentAnswer:
        system = SYSTEM_PROMPT_AR if is_arabic(problem) else SYSTEM_PROMPT
        messages = [{"role": "system", "content": system}]
        messages += history or []
        if not history:
            messages.append({"role": "user", "content": problem})
        resp = self.model.chat(messages, temperature=self.temperature, max_tokens=self.max_tokens)
        steps, final = parse_answer(resp.content)
        return StudentAnswer(
            raw=resp.content,
            reasoning=resp.reasoning,
            steps=steps,
            final_answer=final,
            latency_s=resp.latency_s,
            tokens=resp.completion_tokens,
        )

    @staticmethod
    def revision_message(feedback: str, arabic: bool = False) -> str:
        tmpl = REVISION_PROMPT_AR if arabic else REVISION_PROMPT
        return tmpl.format(feedback=feedback)
