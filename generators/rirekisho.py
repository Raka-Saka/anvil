"""
履歴書 and 職務経歴書 as PDFs, written fresh for each Japanese application.

The fixed facts (name, address, dates, schools, employers, visa) come from data/rirekisho.yaml, never from
Claude. Per job, the pack gives: the wording of each employer line (from his own 履歴書 versions), which
licences to show, the 志望動機, the 本人希望 lines (from hope_facts) and the 職務経歴書 text. Dated today.
Layout: A4, close to the JIS 履歴書 (two pages).
"""

from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent.parent
FACTS_FILE = ROOT / "data" / "rirekisho.yaml"
FONT_FILE = Path("C:/Windows/Fonts/BIZ-UDMinchoM.ttc")
FONT_FALLBACK = Path("C:/Windows/Fonts/msmincho.ttc")


def facts() -> dict:
    from core.store import read_yaml
    return read_yaml(FACTS_FILE) if FACTS_FILE.exists() else {}


def _font() -> str:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    if "JP" not in pdfmetrics.getRegisteredFontNames():
        path = FONT_FILE if FONT_FILE.exists() else FONT_FALLBACK
        pdfmetrics.registerFont(TTFont("JP", str(path), subfontIndex=0))
    return "JP"


def _jdate(d: date) -> str:
    return f"{d.year} 年 {d.month} 月 {d.day} 日現在"


def _age(birth: date, on: date) -> int:
    return on.year - birth.year - ((on.month, on.day) < (birth.month, birth.day))


def _ym(s: str):
    s = str(s or "")
    return (s[:4], str(int(s[5:7])) if len(s) >= 7 else "")


def history_rows(f: dict, descs: dict) -> list:
    """[(year, month, text)] for 学歴・職歴, ending with 以上."""
    rows = [("", "", "学　歴")]
    rows += [(*_ym(e["date"]), e["text"]) for e in f.get("education", [])]
    rows.append(("", "", "職　歴"))
    for c in f.get("career", []):
        desc = descs.get(c["company"]) or c["desc"]
        rows.append((*_ym(c["start"]), f"{c['company']}　入社　{desc}"))
        if c.get("end"):
            rows.append((*_ym(c["end"]), "一身上の都合により退職"))
    rows.append(("", "", "以上"))
    return rows


def render_rirekisho(path: Path, motive: str, hope: list, descs: dict = None, licenses: list = None,
                     on: date = None) -> Path:
    """Write the 履歴書 PDF in the standard layout (JIS / 厚生労働省履歴書様式例, A4 x 2).
    descs: {company: wording}; licenses: texts to show (None = all)."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase.pdfmetrics import stringWidth
    from reportlab.platypus import Paragraph
    from reportlab.pdfgen import canvas

    f = facts()
    on = on or date.today()
    font = _font()
    W, H = A4
    L, R = 15 * mm, W - 15 * mm
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setTitle("履歴書")

    def t(x, y, s, size=10, right=False, centre=False):
        c.setFont(font, size)
        (c.drawRightString if right else c.drawCentredString if centre else c.drawString)(x, y, s)

    def para(txt, x, y_top, width, size=10, leading=None):
        st = ParagraphStyle("p", fontName=font, fontSize=size, leading=leading or size * 1.5, wordWrap="CJK")
        p = Paragraph(str(txt).replace("\n", "<br/>"), st)
        _, h = p.wrap(width, 2000)
        p.drawOn(c, x, y_top - h)
        return h

    def frame(x0, y0, x1, y1, w=1.2):
        c.setLineWidth(w)
        c.rect(x0, y1, x1 - x0, y0 - y1)
        c.setLineWidth(0.5)

    def hline(x0, x1, y, dash=False):
        c.setDash(1, 2) if dash else c.setDash()
        c.line(x0, y, x1, y)
        c.setDash()

    # --- page 1 ----------------------------------------------------------------------------------
    t(L, H - 20 * mm, "履　歴　書", 18)
    t(L + 72 * mm, H - 20 * mm, f"{on.year} 年　{on.month} 月　{on.day} 日現在", 9.5)

    # photo: 縦 40mm × 横 30mm, top right
    pw, ph = 30 * mm, 40 * mm
    px, py = R - pw, H - 15 * mm - ph
    photo = ROOT / str(f.get("photo") or "")
    if f.get("photo") and photo.exists():
        c.drawImage(str(photo), px, py, pw, ph)
    else:
        c.setDash(2, 2)
        c.rect(px, py, pw, ph)
        c.setDash()
        para("写真をはる位置<br/>縦 36〜40mm<br/>横 24〜30mm<br/>本人単身胸から上", px + 2 * mm, py + ph - 4 * mm,
             pw - 4 * mm, 6.5)

    # identity block: ふりがな / 氏名 / 生年月日 + ※性別
    bx1 = px - 4 * mm
    top = H - 24 * mm
    y_kana, y_name, y_birth = top - 7 * mm, top - 7 * mm - 18 * mm, top - 7 * mm - 18 * mm - 10 * mm
    frame(L, top, bx1, y_birth)
    hline(L, bx1, y_kana, dash=True)
    hline(L, bx1, y_name)
    t(L + 2 * mm, top - 5 * mm, "ふりがな", 7.5)
    t(L + 20 * mm, top - 5 * mm, f.get("name_kana", ""), 9)
    t(L + 2 * mm, y_kana - 5 * mm, "氏　名", 8)
    t(L + 20 * mm, y_kana - 12 * mm, f.get("name", ""), 14)
    birth = date.fromisoformat(str(f.get("birth", "1970-01-01")))
    gx = bx1 - 26 * mm
    c.line(gx, y_name, gx, y_birth)
    t(L + 2 * mm, y_name - 6.3 * mm,
      f"{birth.year} 年　{birth.month} 月　{birth.day} 日生　（満 {_age(birth, on)} 歳）", 10)
    t(gx + 2 * mm, y_name - 6.3 * mm, f"※性別　{f.get('gender', '')}", 9.5)

    # address block: ふりがな / 現住所 | 電話 ; ふりがな / 連絡先 | 電話 ; E-mail
    a_top = y_birth - 4 * mm
    tel_x = R - 42 * mm
    rows_a = [a_top, a_top - 6 * mm, a_top - 22 * mm, a_top - 28 * mm, a_top - 42 * mm]
    frame(L, rows_a[0], R, rows_a[-1])
    c.line(tel_x, rows_a[0], tel_x, rows_a[-1])
    hline(L, tel_x, rows_a[1], dash=True)
    hline(L, R, rows_a[2])
    hline(L, tel_x, rows_a[3], dash=True)
    hline(tel_x, R, rows_a[0] - 12 * mm)
    t(L + 2 * mm, rows_a[0] - 4.3 * mm, "ふりがな", 7.5)
    t(L + 20 * mm, rows_a[0] - 4.3 * mm, f.get("address_kana", ""), 8)
    t(L + 2 * mm, rows_a[1] - 4.5 * mm, "現住所", 8)
    t(L + 16 * mm, rows_a[1] - 4.5 * mm, f"〒 {f.get('postcode', '')}", 9.5)
    para(f.get("address", ""), L + 16 * mm, rows_a[1] - 6 * mm, tel_x - L - 18 * mm, 9.5)
    t(tel_x + 2 * mm, rows_a[0] - 4.3 * mm, "電話", 8)
    t(tel_x + 2 * mm, rows_a[0] - 10 * mm, f.get("phone", ""), 10)
    t(tel_x + 2 * mm, rows_a[0] - 16 * mm, "E-mail", 8)
    t(tel_x + 2 * mm, rows_a[0] - 20.5 * mm, f.get("email", ""), 8.5)
    t(L + 2 * mm, rows_a[2] - 4.3 * mm, "ふりがな", 7.5)
    t(L + 2 * mm, rows_a[3] - 4.5 * mm, "連絡先", 8)
    t(L + 16 * mm, rows_a[3] - 4.5 * mm, "〒　　　　　（現住所以外に連絡を希望する場合のみ記入）", 7.5)
    t(tel_x + 2 * mm, rows_a[2] - 4.3 * mm, "電話", 8)

    # 学歴・職歴 table
    yx, mx, tx = L, L + 17 * mm, L + 27 * mm
    rh = 8 * mm

    def table(rows, y_top, n_rows, head):
        """A ruled table of n_rows lines (heading + rows), filled from rows; returns rows left over."""
        y_bottom = y_top - rh * (n_rows + 1)
        frame(L, y_top, R, y_bottom)
        c.line(mx, y_top, mx, y_bottom)
        c.line(tx, y_top, tx, y_bottom)
        t((yx + mx) / 2, y_top - 5.5 * mm, "年", 9, centre=True)
        t((mx + tx) / 2, y_top - 5.5 * mm, "月", 9, centre=True)
        t((tx + R) / 2, y_top - 5.5 * mm, head, 9, centre=True)
        y = y_top - rh
        slots = n_rows
        while slots:
            hline(L, R, y)
            if rows:
                yr, mo, txt = rows[0]
                need = 2 if stringWidth(txt, font, 10) > R - tx - 4 * mm else 1
                if need <= slots:
                    t((yx + mx) / 2, y - 5.6 * mm, yr, 10, centre=True)
                    t((mx + tx) / 2, y - 5.6 * mm, mo, 10, centre=True)
                    if txt in ("学　歴", "職　歴"):
                        t((tx + R) / 2, y - 5.6 * mm, txt, 10, centre=True)
                    elif txt == "以上":
                        t(R - 6 * mm, y - 5.6 * mm, txt, 10, right=True)
                    elif need == 1:
                        t(tx + 2 * mm, y - 5.6 * mm, txt, 10)
                    else:
                        para(txt, tx + 2 * mm, y - 1.8 * mm, R - tx - 4 * mm, 10, leading=rh)
                    rows = rows[1:]
                    y -= rh * need
                    slots -= need
                    continue
            y -= rh
            slots -= 1
        return rows

    hist = history_rows(f, descs or {})
    t_top = rows_a[-1] - 5 * mm
    n1 = int((t_top - 24 * mm) / rh) - 1
    hist = table(hist, t_top, n1, "学歴・職歴（各別にまとめて書く）")
    para("記入上の注意　1. 鉛筆以外の黒又は青の筆記具で記入。　2. 数字はアラビア数字で、文字はくずさず正確に書く。"
         "　3. ※印のところは、該当するものを○で囲む。", L, 20 * mm, R - L, 7)
    c.showPage()

    # --- page 2 ----------------------------------------------------------------------------------
    y = H - 15 * mm
    n_more = max(6, len(hist) + 1)
    hist = table(hist, y, n_more, "学歴・職歴")
    y -= rh * (n_more + 1) + 5 * mm
    lic = [l for l in f.get("licenses", []) if licenses is None or l["text"] in licenses]
    lic_rows = [(str(l.get("date") or ""), "", l["text"]) for l in lic] + [("", "", "以上")]
    n_lic = max(6, len(lic_rows))
    table(lic_rows, y, n_lic, "免許・資格")
    y -= rh * (n_lic + 1) + 5 * mm

    def box(title, body, y_top, h):
        frame(L, y_top, R, y_top - h)
        t(L + 2 * mm, y_top - 5 * mm, title, 8.5)
        para(body, L + 3 * mm, y_top - 8 * mm, R - L - 6 * mm, 10, leading=15.5)
        return y_top - h - 5 * mm

    hope_lines = [h for h in hope if h.strip()]
    if f.get("visa") and not any("在留" in h for h in hope_lines):
        hope_lines.append(f["visa"])
    hope_h = 42 * mm
    y = box("志望の動機、特技、好きな学科、アピールポイントなど", motive.strip(), y, y - 15 * mm - hope_h - 5 * mm)
    box("本人希望記入欄（特に給料・職種・勤務時間・勤務地・その他についての希望などがあれば記入）",
        "\n".join(f"・{h.lstrip('・')}" for h in hope_lines), y, hope_h)
    c.save()
    return path


def render_shokumu(path: Path, markdown: str, on: date = None) -> Path:
    """The 職務経歴書 from simple Markdown (# title, ■ / ## headings, 【】 employer lines, ・ bullets)."""
    import re
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    f = facts()
    on = on or date.today()
    font = _font()
    st = {k: ParagraphStyle(k, fontName=font, wordWrap="CJK", **v) for k, v in {
        "title": dict(fontSize=18, leading=26, alignment=1),
        "right": dict(fontSize=10, leading=15, alignment=2),
        "h": dict(fontSize=12, leading=20, spaceBefore=8),
        "b": dict(fontSize=10, leading=16),
        "li": dict(fontSize=10, leading=16, leftIndent=10, firstLineIndent=-10),
    }.items()}
    story = [Paragraph("職 務 経 歴 書", st["title"]), Paragraph(_jdate(on), st["right"]),
             Paragraph(f"氏名：{f.get('name', '')}", st["right"]), Spacer(1, 6)]
    for raw in markdown.splitlines():
        s = re.sub(r"\*\*(.+?)\*\*", r"\1", raw.strip())
        if not s or re.sub(r"[#\s]", "", s) == "職務経歴書" or "現在" in s and re.match(r"^\d{4}\s*年", s) \
                or s.startswith("氏名"):
            continue                                  # title, date and name are written above
        if re.match(r"^#{1,3}\s+", s) or s.startswith("■"):
            story.append(Paragraph("■ " + re.sub(r"^(#{1,3}\s+|■\s*)", "", s), st["h"]))
        elif s.startswith("【"):
            story.append(Spacer(1, 4))
            story.append(Paragraph(s, st["b"]))
        elif s == "以上":
            story.append(Paragraph(s, st["right"]))
        elif re.match(r"^[-*・•]\s*", s):
            story.append(Paragraph("・" + re.sub(r"^[-*・•]\s*", "", s), st["li"]))
        else:
            story.append(Paragraph(s, st["b"]))
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm,
                      bottomMargin=16 * mm, title="職務経歴書").build(story)
    return path


def render_cover(path: Path, to: str, body: str, enclosed: list, on: date = None) -> Path:
    """The 送付状 (cover sheet) that goes on top of documents sent by post."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

    f = facts()
    on = on or date.today()
    font = _font()
    st = {k: ParagraphStyle(k, fontName=font, wordWrap="CJK", **v) for k, v in {
        "right": dict(fontSize=10.5, leading=17, alignment=2),
        "left": dict(fontSize=11, leading=18),
        "title": dict(fontSize=14, leading=22, alignment=1, spaceBefore=14, spaceAfter=14),
        "b": dict(fontSize=10.5, leading=19),
        "centre": dict(fontSize=10.5, leading=19, alignment=1, spaceBefore=10),
        "li": dict(fontSize=10.5, leading=19, leftIndent=40),
    }.items()}
    story = [Paragraph(_jdate(on).replace("現在", "").strip(), st["right"]), Spacer(1, 6)]
    story += [Paragraph(line, st["left"]) for line in to.splitlines() if line.strip()]
    story += [Spacer(1, 8), Paragraph(f"〒{f.get('postcode', '')}", st["right"]),
              Paragraph(f.get("address", ""), st["right"]), Paragraph(f.get("name", ""), st["right"]),
              Paragraph(f"電話：{f.get('phone', '')}", st["right"]),
              Paragraph(f"E-mail：{f.get('email', '')}", st["right"]),
              Paragraph("応募書類の送付について", st["title"])]
    story += [Paragraph(p.strip(), st["b"]) for p in body.splitlines() if p.strip()]
    story += [Paragraph("記", st["centre"]), Spacer(1, 4)]
    story += [Paragraph(f"・{e}　1通", st["li"]) for e in enclosed]
    story += [Spacer(1, 6), Paragraph("以上", st["right"])]
    SimpleDocTemplate(str(path), pagesize=A4, leftMargin=22 * mm, rightMargin=22 * mm, topMargin=20 * mm,
                      bottomMargin=20 * mm, title="送付状").build(story)
    return path

