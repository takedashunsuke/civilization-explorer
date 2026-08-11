# -*- coding: utf-8 -*-
"""Generate japanNengo data from Wikipedia markdown dump."""
import json
import re
from pathlib import Path

SRC = Path(
    r"C:\Users\shunsuke\.cursor\projects\c-dev-civ-explorer\agent-tools\f3f37105-f512-40f6-905b-e7f0b677262f.txt"
)
OUT_TS = Path(r"c:\dev\civ-explorer\frontend\app\utils\japanNengo.ts")
OUT_JSON = Path(r"c:\dev\civ-explorer\frontend\scripts\_eras_parsed.json")

text = SRC.read_text(encoding="utf-8")

# Remove Northern Court block (keep Southern + reunified eras)
northern_start = text.find("#### 北朝")
reunify_start = text.find("#### 南北朝合一後")
if northern_start != -1 and reunify_start != -1 and reunify_start > northern_start:
    text = text[:northern_start] + text[reunify_start:]

# Stop before unrelated sections
for marker in ("## 中央政府以外の元号", "## 符号位置", "## 脚注"):
    idx = text.find(marker)
    if idx != -1:
        text = text[:idx]
        break

row_re = re.compile(
    r"^\|\s*([^|\n]+?)\s*\|\s*([^|\n]+?)\s*\|\s*[^|]*?（\s*(\d{3,4})\s*年",
    re.M,
)

eras: list[tuple[str, str, int]] = []
seen_years: set[int] = set()

for m in row_re.finditer(text):
    ja = m.group(1).strip()
    reading = m.group(2).strip()
    year = int(m.group(3))
    if ja in ("-", "漢字", "") or reading in ("-", "読み"):
        continue
    if not re.fullmatch(r"[\u4e00-\u9fff]{2,4}", ja):
        continue
    # Prefer first occurrence for a start year
    if year in seen_years:
        continue
    seen_years.add(year)
    eras.append((ja, reading, year))

# Meiji+ tables use a different shape: 明治（めいじ） | ...（ 1868年
modern_re = re.compile(
    r"^\|\s*([一-龥]{2,3})（([^）]+)）\s*\|[^|]*?（\s*(\d{4})\s*年",
    re.M,
)
for m in modern_re.finditer(text):
    ja, reading, year = m.group(1), m.group(2), int(m.group(3))
    if year in seen_years:
        # replace if older entry was wrong, keep modern authoritative for these years
        eras = [e for e in eras if e[2] != year]
    seen_years.add(year)
    eras.append((ja, reading, year))

# Ensure reunification era after Southern Court
if not any(e[0] == "明徳" for e in eras):
    eras.append(("明徳", "めいとく", 1392))
    seen_years.add(1392)

eras.sort(key=lambda x: x[2])

# Year-table cleanups
eras = [(ja, rd, y) for ja, rd, y in eras if ja != "正慶"]
eras = [
    ("天平勝宝", "てんぴょうしょうほう", y) if ja == "天平感宝" else (ja, rd, y)
    for ja, rd, y in eras
]
# Re-extend 元弘 through 建武 if 正慶 removed
fixed = []
for ja, rd, y in eras:
    fixed.append((ja, rd, y))
eras = fixed
eras.sort(key=lambda x: x[2])

print(f"count={len(eras)}")
print("first=", eras[:5])
print("last=", eras[-6:])
missing = [n for n in ("明治", "大正", "昭和", "平成", "令和", "天平勝宝") if not any(e[0] == n for e in eras)]
print("missing check=", missing)

# Simple hiragana -> Hepburn (enough for era readings)
HIRAGANA = {
    "あ": "a", "い": "i", "う": "u", "え": "e", "お": "o",
    "か": "ka", "き": "ki", "く": "ku", "け": "ke", "こ": "ko",
    "さ": "sa", "し": "shi", "す": "su", "せ": "se", "そ": "so",
    "た": "ta", "ち": "chi", "つ": "tsu", "て": "te", "と": "to",
    "な": "na", "に": "ni", "ぬ": "nu", "ね": "ne", "の": "no",
    "は": "ha", "ひ": "hi", "ふ": "fu", "へ": "he", "ほ": "ho",
    "ま": "ma", "み": "mi", "む": "mu", "め": "me", "も": "mo",
    "や": "ya", "ゆ": "yu", "よ": "yo",
    "ら": "ra", "り": "ri", "る": "ru", "れ": "re", "ろ": "ro",
    "わ": "wa", "を": "o", "ん": "n",
    "が": "ga", "ぎ": "gi", "ぐ": "gu", "げ": "ge", "ご": "go",
    "ざ": "za", "じ": "ji", "ず": "zu", "ぜ": "ze", "ぞ": "zo",
    "だ": "da", "ぢ": "ji", "づ": "zu", "で": "de", "ど": "do",
    "ば": "ba", "び": "bi", "ぶ": "bu", "べ": "be", "ぼ": "bo",
    "ぱ": "pa", "ぴ": "pi", "ぷ": "pu", "ぺ": "pe", "ぽ": "po",
    "きゃ": "kya", "きゅ": "kyu", "きょ": "kyo",
    "しゃ": "sha", "しゅ": "shu", "しょ": "sho",
    "ちゃ": "cha", "ちゅ": "chu", "ちょ": "cho",
    "にゃ": "nya", "にゅ": "nyu", "にょ": "nyo",
    "ひゃ": "hya", "ひゅ": "hyu", "ひょ": "hyo",
    "みゃ": "mya", "みゅ": "myu", "みょ": "myo",
    "りゃ": "rya", "りゅ": "ryu", "りょ": "ryo",
    "ぎゃ": "gya", "ぎゅ": "gyu", "ぎょ": "gyo",
    "じゃ": "ja", "じゅ": "ju", "じょ": "jo",
    "びゃ": "bya", "びゅ": "byu", "びょ": "byo",
    "ぴゃ": "pya", "ぴゅ": "pyu", "ぴょ": "pyo",
    "っ": "",  # handled specially
}


def to_romaji(hira: str) -> str:
    s = hira
    out = []
    i = 0
    while i < len(s):
        if s[i] == "っ" and i + 1 < len(s):
            # geminate next consonant
            rest = to_romaji(s[i + 1 :])
            if rest:
                out.append(rest[0])
                out.append(rest)
                return "".join(out)
            i += 1
            continue
        if i + 1 < len(s) and s[i : i + 2] in HIRAGANA:
            out.append(HIRAGANA[s[i : i + 2]])
            i += 2
            continue
        ch = s[i]
        out.append(HIRAGANA.get(ch, ch))
        i += 1
    return "".join(out)


def title_romaji(hira: str) -> str:
    r = to_romaji(hira)
    # split on boundaries for multi-mora compounds is hard; capitalize first letter
    if not r:
        return r
    return r[0].upper() + r[1:]


records = []
for ja, reading, start in eras:
    records.append(
        {
            "ja": ja,
            "reading": reading,
            "en": title_romaji(reading),
            "from": start,
        }
    )

# Build PeriodDef ranges: to = next.from, last to = Infinity
lines = [
    "/** Auto-generated Japanese nengō (大化→令和). Do not edit by hand — regenerate via scripts/parse_eras.py */",
    "",
    "export type JapanNengo = {",
    "  /** Inclusive start year (Gregorian / astronomical AD) */",
    "  from: number",
    "  /** Exclusive end year */",
    "  to: number",
    "  ja: string",
    "  reading: string",
    "  en: string",
    "}",
    "",
    "export const JAPAN_NENGO: JapanNengo[] = [",
]

for i, rec in enumerate(records):
    end = records[i + 1]["from"] if i + 1 < len(records) else "Number.POSITIVE_INFINITY"
    lines.append(
        f'  {{ from: {rec["from"]}, to: {end}, ja: "{rec["ja"]}", reading: "{rec["reading"]}", en: "{rec["en"]}" }},'
    )

lines.append("]")
lines.append("")

OUT_TS.write_text("\n".join(lines) + "\n", encoding="utf-8")
OUT_JSON.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote", OUT_TS)
print("wrote", OUT_JSON)
