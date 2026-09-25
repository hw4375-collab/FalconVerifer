import type { Text } from '../i18n'
import type { Arm } from '../lib/types'

export const ARM_SET: Record<string, Text> = {
  falcon3b_arabic: { en: 'Arabic benchmark', ar: 'المعيار العربي' },
  falcon3b_arabic_scale: { en: 'Arabic, generated at scale', ar: 'عربي، مولّد على نطاق واسع' },
  falcon7b_arabic: { en: 'Arabic benchmark', ar: 'المعيار العربي' },
  falcon3b_formalizer: { en: 'English benchmark', ar: 'المعيار الإنجليزي' },
  falcon3b_v2: { en: 'English math, rerun', ar: 'رياضيات إنجليزية، إعادة تشغيل' },
  falcon3b_formalizer_hard: { en: 'English, hard tier', ar: 'إنجليزي، المستوى الصعب' },
  falcon_formalizer: { en: 'English benchmark', ar: 'المعيار الإنجليزي' },
  falcon_formalizer_hard: { en: 'English, hard tier', ar: 'إنجليزي، المستوى الصعب' },
  l20_ar: { en: 'LOGIC-20, Arabic', ar: 'LOGIC-20، بالعربية' },
  daily_ar: { en: 'Everyday Arabic dialogue', ar: 'حوار عربي يومي' },
  l20_en: { en: 'LOGIC-20, English', ar: 'LOGIC-20، بالإنجليزية' },
}

export const SLICES: { key: string; label: Text }[] = [
  { key: 'all', label: { en: 'All questions', ar: 'كل الأسئلة' } },
  { key: 'math', label: { en: 'Math', ar: 'رياضيات' } },
  { key: 'logic', label: { en: 'Logic', ar: 'منطق' } },
  { key: 'eastern-digits', label: { en: 'Eastern Arabic digits', ar: 'أرقام عربية مشرقية' } },
  { key: 'fragment', label: { en: 'Inside the grammar fragment', ar: 'ضمن قواعد الترجمة الحتمية' } },
  { key: 'hard', label: { en: 'Hard', ar: 'صعبة' } },
  { key: 'det:weekday', label: { en: 'Weekdays', ar: 'أيام الأسبوع' } },
  { key: 'det:clock', label: { en: 'Clock times', ar: 'الساعات' } },
  { key: 'det:currency', label: { en: 'Currency', ar: 'العملات' } },
  { key: 'det:unit', label: { en: 'Units', ar: 'الوحدات' } },
  { key: 'det:bill', label: { en: 'Bills', ar: 'الفواتير' } },
]

export const armSet = (a: Arm, t: (x: Text) => string) => t(ARM_SET[a.key] ?? { en: a.key, ar: a.key })
