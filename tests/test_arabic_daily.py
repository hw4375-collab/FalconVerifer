"""Everyday-Arabic deterministic fragment (weekdays, clock, conversion, bills)."""

from falconverifier.arabic_daily import analyze, formalize_daily


def test_weekday_after_and_before():
    assert (
        formalize_daily("اليوم الثلاثاء. ما اليوم بعد ١٠ أيام؟", "الجمعة")[0]
        == "((2:ℕ) + 10) % 7 = 5"
    )
    assert (
        formalize_daily("اليوم الخميس. ما اليوم قبل ٣ أيام؟", "الاثنين")[0]
        == "((4:ℕ) + 7 - 3) % 7 = 1"
    )
    assert (
        formalize_daily("اليوم السبت. ما اليوم بعد أسبوعين؟", "الأحد")[0] == "((6:ℕ) + 14) % 7 = 0"
    )


def test_weekday_answer_must_name_a_day():
    assert formalize_daily("اليوم الثلاثاء. ما اليوم بعد ١٠ أيام؟", "5") is None


def test_clock_duration_with_words_and_pm():
    prop, cert = formalize_daily(
        "بدأ الاجتماع في الساعة ٩:٣٠ واستمر ساعتين و٤٥ دقيقة. في أي ساعة انتهى؟", "١٢:١٥"
    )
    assert prop == "((9:ℕ) * 60 + 30 + 165) = 12 * 60 + 15"
    assert "lasts 165 min" in cert
    prop, _ = formalize_daily(
        "بدأ الفيلم في الساعة ٨:٠٠ مساء واستمر ساعتين ونصف. متى انتهى؟", "22:30"
    )
    assert prop == "((20:ℕ) * 60 + 0 + 150) = 22 * 60 + 30"


def test_currency_both_directions_and_units():
    assert (
        formalize_daily("١ دولار = ٣٫٦٧ درهم. كم دولاراً يساوي ٧٣٤ درهماً؟", "200")[0]
        == "(734:ℚ) / 3.67 = 200"
    )
    prop, _ = formalize_daily("١ دولار = ٣٫٦٧ درهم. كم درهماً يساوي ٢٥٠ دولاراً؟", "917.5")
    assert prop.startswith("(250:ℚ) * 3.67 - 917.5 <")
    assert formalize_daily("كم متراً في ٣٫٥ كيلومتر؟", "3500")[0] == "(3.5:ℚ) * 1000 = 3500"
    assert formalize_daily("كم دقيقة في ٤ ساعات؟", "240")[0] == "(4:ℚ) * 60 = 240"


def test_bill_tax_service_split_tip_discount():
    d = analyze(
        "الفاتورة ٢٤٠ درهماً، تضاف ضريبة ٥٪ ورسوم خدمة ١٠٪، وتقاسمها ٣ أشخاص بالتساوي. كم يدفع كل واحد؟"
    )
    assert d.expr == "(240:ℚ) * (1 + 5 / 100) * (1 + 10 / 100) / 3"
    assert d.fired == ["bill", "+5%", "+10%", "split 3"]
    prop, _ = formalize_daily("الحساب ١٥٠ درهماً، مع خصم ٢٠٪ وأضاف بقشيشاً ١٠ دراهم. كم دفع؟", "130")
    assert prop == "((150:ℚ) * (1 - 20 / 100) + 10) = 130"


def test_fail_closed():
    # per-person question without a split clause; unrelated narrative; no answer
    assert analyze("الفاتورة ٢٤٠ درهماً، تضاف ضريبة ٥٪. كم يدفع كل واحد؟") is None
    assert analyze("اشترى سعيد ٩٣ علبة. كم بقي؟") is None
    assert formalize_daily("كم دقيقة في ٤ ساعات؟", None) is None


def test_answer_expression_uses_right_hand_side():
    q = "العميل: ١ دولار = ٣٫٧٥ ريال. كم ريالاً يساوي ١٥٠ دولاراً؟"
    good = formalize_daily(q, "150 دولار × 3.75 ريال/دولار = 562.5 ريال")
    plain = formalize_daily(q, "562.5")
    assert good is not None and good[0] == plain[0]
