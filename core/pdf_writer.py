import fitz
import re


# -------------------------
# Cleaning helpers
# -------------------------

PLACEHOLDER_PATTERNS = [
    r"\[.*?optional.*?\]",
    r"\[.*?add.*?\]",
    r"\[.*?replace.*?\]",
    r"\[.*?company name.*?\]",
    r"\[.*?job title.*?\]",
    r"\[.*?dates.*?\]",
    r"\[.*?\]",
]

def clean_placeholders(text: str) -> str:
    for pat in PLACEHOLDER_PATTERNS:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)
    return text


def clean_text(text: str) -> str:
    return (
        text.replace("\u2013", "-")
        .replace("\u2014", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
    )


# -------------------------
# Resume parser (LLM output)
# -------------------------

def parse_resume(raw_text: str):
    raw_text = clean_placeholders(raw_text)
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

    sections = {}
    current = None

    for line in lines:
        key = line.upper().replace(":", "")
        if key in {"SUMMARY", "SKILLS", "EXPERIENCE", "PROJECTS", "EDUCATION"}:
            current = key
            sections[current] = []
            continue

        if current:
            sections[current].append(line)

    return sections


# -------------------------
# PDF generator
# -------------------------

def generate_resume_pdf_from_text(raw_text: str, profile: dict, out_path: str):
    doc = fitz.open()
    page = doc.new_page()

    W, H = page.rect.width, page.rect.height
    MARGIN_X = 50
    Y = 50

    FONT = "Helvetica"
    FONT_BOLD = "Helvetica-Bold"

    def new_page_if_needed(h=40):
        nonlocal page, Y
        if Y + h > H - 50:
            page = doc.new_page()
            Y = 50

    def write(text, size=10, bold=False, indent=0):
        nonlocal Y, page
        text = clean_text(text)
        font = FONT_BOLD if bold else FONT

        max_width = W - MARGIN_X * 2 - indent
        words = text.split()
        line = ""

        for word in words:
            test = (line + " " + word).strip()
            if fitz.get_text_length(test, fontname=font, fontsize=size) <= max_width:
                line = test
            else:
                if Y > H - 60:
                    page = doc.new_page()
                    Y = 50

                page.insert_text(
                    (MARGIN_X + indent, Y),
                    line,
                    fontsize=size,
                    fontname=font,
                )
                Y += size * 1.4
                line = word

        if line:
            if Y > H - 60:
                page = doc.new_page()
                Y = 50

            page.insert_text(
                (MARGIN_X + indent, Y),
                line,
                fontsize=size,
                fontname=font,
            )
            Y += size * 1.6



    def section(title):
        nonlocal Y
        new_page_if_needed(40)
        write(title, size=12, bold=True)
        page.draw_line(
            (MARGIN_X, Y - 4),
            (W - MARGIN_X, Y - 4),
        )
        Y += 8

    # -------------------------
    # HEADER
    # -------------------------

    write(profile.get("full_name", ""), size=18, bold=True)

    contact = " | ".join(
        v for v in [
            profile.get("location"),
            profile.get("phone"),
            profile.get("email"),
            profile.get("linkedin"),
            profile.get("github"),
        ]
        if v
    )
    if contact:
        write(contact, size=10)

    Y += 10

    # -------------------------
    # EDUCATION (ONLY FROM PROFILE)
    # -------------------------

    edu = profile.get("education", {})
    if any(edu.values()):
        section("EDUCATION")
        edu_line = " | ".join(
            v for v in [
                edu.get("degree"),
                edu.get("university"),
                edu.get("year"),
            ]
            if v
        )
        write(edu_line)

    # -------------------------
    # PARSE MODEL CONTENT
    # -------------------------

    sections = parse_resume(raw_text)

    # -------------------------
    # SUMMARY
    # -------------------------

    if "SUMMARY" in sections:
        section("SUMMARY")
        for line in sections["SUMMARY"]:
            write(line)

    # -------------------------
    # SKILLS
    # -------------------------

    if "SKILLS" in sections:
        section("SKILLS")
        for line in sections["SKILLS"]:
            if "university name" in line.lower():
                continue
            write("• " + line.lstrip("*- "), indent=12)

    # -------------------------
    # EXPERIENCE
    # -------------------------

    section("EXPERIENCE")

    exp = profile.get("profile_experience")

    if exp:
        header = " | ".join(
            v for v in [
                exp.get("company"),
                exp.get("position"),
                exp.get("type"),
                exp.get("years"),
            ]
            if v
        )
        write(header, bold=True)

    if "EXPERIENCE" in sections:
        for line in sections["EXPERIENCE"]:
            if "education" in line.lower():
                continue
            if line.startswith("*") or line.startswith("-"):
                write("• " + line.lstrip("*- "), indent=12)
            else:
                write(line)

    # -------------------------
    # PROJECTS
    # -------------------------

    if "PROJECTS" in sections:
        section("PROJECTS")
        for line in sections["PROJECTS"]:
            if line.startswith("*"):
                write("• " + line.lstrip("*- "), indent=12)
            else:
                write(line)

    doc.save(out_path)