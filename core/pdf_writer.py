import fitz
import re

PLACEHOLDER_PATTERNS = [
    r"\[optional:.*?\]",
    r"\[if you have.*?\]",
    r"\[add another.*?\]",
    r"\[your .*?\]",
    r"\(mention .*?\)",
]

def remove_placeholders(text: str) -> str:
    for pat in PLACEHOLDER_PATTERNS:
        text = re.sub(pat, "", text, flags=re.IGNORECASE)
    return text


def clean_text_for_pdf(text: str) -> str:
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2022": "*",
        "**": "",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

def parse_resume_robust(raw_text: str):
    raw_text = remove_placeholders(raw_text)
    lines = raw_text.split("\n")

    data = {
        "sections": {}
    }

    KNOWN_HEADERS = {
        "summary": "SUMMARY",
        "experience": "EXPERIENCE",
        "education": "EDUCATION",
        "skills": "SKILLS",
        "projects": "PROJECTS",
        "languages": "LANGUAGES",
        "certifications": "CERTIFICATIONS",
        "technical skills": "SKILLS",
    }

    current_section = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        clean = line.replace("*", "").replace(":", "").strip().lower()

        if clean in KNOWN_HEADERS:
            current_section = KNOWN_HEADERS[clean]
            data["sections"][current_section] = []
            continue

        if clean in {"plan", "resume"}:
            continue

        if current_section:
            data["sections"][current_section].append(line)

    return data

def create_resume_pdf(parsed_data, profile: dict, output_filename="generated_resume.pdf"):
    doc = fitz.open()
    page = doc.new_page()

    width, height = page.rect.width, page.rect.height

    margin_left = 50
    margin_right = 50
    margin_top = 50
    y = margin_top

    font_reg = "Helvetica"
    font_bold = "Helvetica-Bold"

    def check_page_break(extra=40):
        nonlocal page, y
        if y + extra > height - 50:
            page = doc.new_page()
            y = margin_top

    def write_text(text, size, font, is_bullet=False, indent=0):
        nonlocal y
        text = clean_text_for_pdf(text)
        rect = fitz.Rect(margin_left + indent, y, width - margin_right, height - 50)
        check_page_break(20)
        try:
            rc = page.insert_textbox(rect, text, fontsize=size, fontname=font, align=0)
        except:
            rc = page.insert_textbox(rect, text, fontsize=size, align=0)
        line_length = (width - margin_left - margin_right - indent) / (size * 0.5)
        if len(text) == 0: 
            lines_count = 1
        else:
            lines_count = (len(text) / line_length) + 1
        height_inc = lines_count * size * 1.4
        y += height_inc + 1

    full_name = profile.get("full_name", "")
    if full_name:
        write_text(full_name, 18, font_bold)

    contact_parts = []
    for key in ["location", "phone", "email", "linkedin", "github"]:
        val = profile.get(key)
        if val:
            contact_parts.append(val)

    if contact_parts:
        write_text(" | ".join(contact_parts), 10, font_reg)

    y += 15

    for section, lines in parsed_data["sections"].items():
        check_page_break(30)

        write_text(section.upper(), 12, font_bold)
        page.draw_line(
            (margin_left, y - 3),
            (width - margin_right, y - 3),
        )
        y += 10

        for line in lines:
            line = line.strip()
            if not line:
                continue
            if line.startswith("*") or line.startswith("-"):
                txt = line.lstrip("*- ").strip()
                write_text(f"• {txt}", 10, font_reg, indent=12)
            elif "|" in line:
                write_text(line, 10, font_bold)
            else:
                write_text(line, 10, font_reg)

        y += 10

    doc.save(output_filename)
    print(f"PDF generated: {output_filename}")


def generate_resume_pdf_from_text(raw_text: str, profile: dict, output_path: str):
    parsed = parse_resume_robust(raw_text)
    create_resume_pdf(parsed, profile, output_path)