"""Find key dates, amounts and notice periods in plain lease text with regular expressions."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], start=1)}
DATE_RE = re.compile(
    r"(?P<named>(?P<mon>[A-Za-z]{3,9})\.? (?P<d1>\d{1,2}),? (?P<y1>\d{4}))"
    r"|(?P<us>(?P<m2>\d{1,2})/(?P<d2>\d{1,2})/(?P<y2>\d{4}))"
    r"|(?P<iso>(?P<y3>\d{4})-(?P<m3>\d{2})-(?P<d3>\d{2}))")
MONEY_RE = re.compile(r"\$\s?(\d{1,3}(?:,\d{3})+|\d+)(\.\d{2})?")
DAYS_RE = re.compile(r"\b(\d{1,3}|(?:thirty|sixty|ninety)) \(?(?:\d+\) )?days?\b", re.IGNORECASE)
PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s?(?:%|percent)", re.IGNORECASE)
WORD_DAYS = {"thirty": 30, "sixty": 60, "ninety": 90}

FIELDS = ["commencement_date", "expiration_date", "monthly_rent", "security_deposit",
          "annual_increase_pct", "renewal_notice_days", "termination_notice_days"]


@dataclass
class Found:
    """One extracted value and the sentence it came from."""

    value: str | float | int
    source: str


def parse_date(text: str) -> str | None:
    """Return the first date in text as YYYY-MM-DD, or None. Understands 'March 1, 2026', 3/1/2026 and 2026-03-01."""
    for m in DATE_RE.finditer(text):
        try:
            if m.group("named"):
                month = MONTHS.get(m.group("mon").lower()) or next(
                    (n for k, n in MONTHS.items() if k.startswith(m.group("mon").lower()[:3])), None)
                if month:
                    return date(int(m.group("y1")), month, int(m.group("d1"))).isoformat()
            elif m.group("us"):
                return date(int(m.group("y2")), int(m.group("m2")), int(m.group("d2"))).isoformat()
            else:
                return date(int(m.group("y3")), int(m.group("m3")), int(m.group("d3"))).isoformat()
        except ValueError:
            continue
    return None


def parse_money(text: str) -> float | None:
    """Return the first dollar amount in text, or None."""
    m = MONEY_RE.search(text)
    return float(m.group(1).replace(",", "") + (m.group(2) or "")) if m else None


def parse_days(text: str) -> int | None:
    """Return the first notice period in days ('90 days', 'sixty (60) days'), or None."""
    m = DAYS_RE.search(text)
    if not m:
        return None
    word = m.group(1).lower()
    return WORD_DAYS.get(word) or int(word)


def sentences(text: str) -> list[str]:
    """Split text into sentences on full stops and line breaks, keeping dollar amounts and dates intact."""
    flat = re.sub(r"\s+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[a-z\)])\.\s+(?=[A-Z])|;\s+", flat) if s.strip()]


def extract(text: str) -> dict[str, Found | None]:
    """Extract the fields in FIELDS from lease text. A field that is not found maps to None."""
    out: dict[str, Found | None] = {f: None for f in FIELDS}
    for s in sentences(text):
        low = s.lower()
        if out["commencement_date"] is None and (k := re.search(r"commenc|\bbegins?\b", low)) and (d := parse_date(s[k.end():])):
            out["commencement_date"] = Found(d, s)
        if out["expiration_date"] is None and (k := re.search(r"\bexpir|\bends\b", low)) and (d := parse_date(s[k.end():])):
            out["expiration_date"] = Found(d, s)
        if out["security_deposit"] is None and "security deposit" in low and (a := parse_money(s)) is not None:
            out["security_deposit"] = Found(a, s)
        if out["monthly_rent"] is None and "rent" in low and "deposit" not in low and (a := parse_money(s)) is not None:
            if re.search(r"\b(annual|per year|per annum|yearly)\b", low):
                out["monthly_rent"] = Found(round(a / 12, 2), s)
            elif re.search(r"\b(month|monthly)\b", low):
                out["monthly_rent"] = Found(a, s)
        if out["annual_increase_pct"] is None and re.search(r"increase|escalat", low) and (p := PERCENT_RE.search(s)):
            out["annual_increase_pct"] = Found(float(p.group(1)), s)
        if out["renewal_notice_days"] is None and "renew" in low and "notice" in low and (n := parse_days(s)):
            out["renewal_notice_days"] = Found(n, s)
        if out["termination_notice_days"] is None and "terminat" in low and "notice" in low and "renew" not in low and (n := parse_days(s)):
            out["termination_notice_days"] = Found(n, s)
    return out
