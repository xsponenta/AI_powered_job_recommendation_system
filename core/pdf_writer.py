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

def clean_text_for_pdf(text):
    """
    Replaces characters that often break standard PDF fonts.
    """
    replacements = {
        "\u2013": "-",    # En-dash to hyphen
        "\u2014": "-",    # Em-dash to hyphen
        "\u2018": "'",    # Smart single quote left
        "\u2019": "'",    # Smart single quote right
        "\u201c": '"',    # Smart double quote left
        "\u201d": '"',    # Smart double quote right
        "\u2022": "*",    # Bullet point char
        "**": "",         # REMOVE BOLD MARKERS entirely
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text

def parse_resume_robust(raw_text):
    raw_text = remove_placeholders(raw_text)
    lines = raw_text.split('\n')

    data = {
        "header": [], 
        "sections": {}
    }
    
    KNOWN_HEADERS = [
        "summary", "experience", "education", "skills", 
        "projects", "languages", "certifications", "technical skills"
    ]
    
    current_section = "header"
    
    for line in lines:
        line = line.strip()
        if not line:
            continue

        clean_check = line.replace("*", "").replace(":", "").strip().lower()
        
        if "important considerations" in clean_check:
            break
            
        if clean_check == "plan" or clean_check == "resume":
            continue

        is_new_section = False
        section_name = ""
        
        if clean_check in KNOWN_HEADERS:
            is_new_section = True
            section_name = line.replace("*", "").replace(":", "").strip()
        elif line.startswith("**") and line.endswith("**") and len(clean_check) < 40:
            is_new_section = True
            section_name = line.replace("*", "").replace(":", "").strip()
            
        if is_new_section:
            current_section = section_name
            data["sections"][current_section] = []
        else:
            if current_section == "header":
                if line.startswith("*") or line.startswith("-"):
                    continue
                if "plan:" in line.lower():
                    continue
                data["header"].append(line)
            else:
                data["sections"][current_section].append(line)
                
    return data

def create_resume_pdf(parsed_data, output_filename="generated_resume.pdf"):
    doc = fitz.open()
    page = doc.new_page()
    width, height = page.rect.width, page.rect.height
    
    margin_left = 50
    margin_right = 50
    margin_top = 50
    y_position = margin_top
    
    font_reg = "Helvetica"
    font_bold = "Helvetica-Bold"

    def check_page_break(needed_height):
        nonlocal y_position, page
        if y_position + needed_height > height - 50:
            page = doc.new_page()
            y_position = margin_top

    def write_text(text, size, font, is_bullet=False, indent=0):
        nonlocal y_position
        
        text = clean_text_for_pdf(text)
        
        rect = fitz.Rect(margin_left + indent, y_position, width - margin_right, height - 50)
        
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
        y_position += height_inc + 1

        profile = parsed_data.get("profile", {})

        header_line = profile.get("full_name", "")
        if header_line:
            write_text(header_line, 18, font_bold)

        contact_parts = []
        for key in ["location", "phone", "email", "linkedin", "github"]:
            val = profile.get(key)
            if val:
                contact_parts.append(val)

        if contact_parts:
            write_text(" | ".join(contact_parts), 10, font_reg)

        y_position += 6

        edu = profile.get("education", {})
        if any(edu.values()):
            write_text("EDUCATION", 12, font_bold)
            page.draw_line((margin_left, y_position-2), (width - margin_right, y_position-2))
            y_position += 4

            edu_line = " | ".join(v for v in [
                edu.get("degree"),
                edu.get("university"),
                edu.get("year")
            ] if v)

            write_text(edu_line, 10, font_reg)
            y_position += 6


    for section, lines in parsed_data["sections"].items():
        check_page_break(30)

        write_text(section.upper(), 12, font_bold)
        page.draw_line((margin_left, y_position-2), (width - margin_right, y_position-2))
        y_position += 2
        
        for line in lines:
            clean_line = line.strip()
            
            if "|" in clean_line: 
                write_text(clean_line, 10, font_bold)
                
            elif clean_line.startswith("*") or clean_line.startswith("-"):
                txt = clean_line.lstrip("*- ").strip()
                write_text(f"• {txt}", 10, font_reg, indent=10)
                
            elif clean_line.startswith("**"):
                write_text(clean_line, 10, font_bold)
                
            else:
                write_text(clean_line, 10, font_reg)
        
        y_position += 5

    doc.save(output_filename)
    print(f"PDF Generated: {output_filename}")

def generate_resume_pdf_from_text(raw_text: str, output_path: str):
    parsed = parse_resume_robust(raw_text)
    create_resume_pdf(parsed, output_path)