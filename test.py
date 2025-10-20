import torch
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import json
import re
from peft import PeftModel

# ===== Paths =====
BASE_MODEL = "t5-large"
MODEL_DIR = "./t5_lora_output/checkpoint-54"  # fused LoRA model

# ===== Load tokenizer and model =====
tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
base_model = AutoModelForSeq2SeqLM.from_pretrained(BASE_MODEL)

model = PeftModel.from_pretrained(base_model, MODEL_DIR)
base_model.eval()

device = "cuda" if torch.cuda.is_available() else "cpu"
base_model.to(device)

# ===== Example input =====
category = "Data Science"
info = {
    "Phone": "+123456789",
    "Email": "example@email.com",
    "Education": "MSc in Computer Science 2005-2007",
    "Experience": "2 years at AI company",
    "Skills": "Python, Pandas, Machine Learning",
    "Projects": "Resume Parser, Job Recommender",
    "Tools": "Jupyter, VS Code, Git, C++"
}

# Combine category and full info into input prompt
info_text = "\n".join([f"{k}: {v}" for k, v in info.items()])

# Few-shot examples to encourage the model to output the structured form
example1_in = (
    "Generate resume for category: Data Science\nInfo:\n"
    "Phone: +111111111\nEmail: a@ex.com\nSkills: Python\n"
)
example1_out = (
    "Phone: +111111111\nEmail: a@ex.com\nEducation: MSc Data Science\n"
    "Experience: 2 years\nSkills: Python\nProjects: ProjectA\nTools: Jupyter\n"
)

example2_in = (
    "Generate resume for category: Data Science\nInfo:\n"
    "Phone: +222222222\nEmail: b@ex.com\nSkills: Pandas\n"
)
example2_out = (
    "Phone: +222222222\nEmail: b@ex.com\nEducation: BSc IT\n"
    "Experience: 1 year\nSkills: Pandas\nProjects: ProjectB\nTools: VS Code\n"
)

instruction = (
    "Now produce ONLY the following lines, one field per line in this exact order:\n"
    "Phone: ...\nEmail: ...\nEducation: ...\nExperience: ...\nSkills: ...\nProjects: ...\nTools: ...\n"
)

input_text = example1_in + example1_out + "\n" + example2_in + example2_out + "\n"
input_text += f"Generate resume for category: {category}\nInfo:\n{info_text}\n" + instruction

# ===== Tokenize input =====
inputs = tokenizer(
    input_text,
    return_tensors="pt",
    truncation=True,
    max_length=512
).to(device)

# ===== Generate resume =====
with torch.no_grad():
    generated_ids = model.generate(
        **inputs,
        max_new_tokens=256,
        num_beams=4,
        temperature=0.0,
        no_repeat_ngram_size=3,
        early_stopping=True
    )

resume_text = tokenizer.decode(generated_ids[0], skip_special_tokens=True)
print("\n=== Generated Resume ===\n")
print(resume_text)

# ===== Parse resume fields =====
fields = ["Phone", "Email", "Education", "Experience", "Skills", "Projects", "Tools"]
parsed_info = {}

def first_email(text):
    m = re.search(r"([\w\.-]+@[\w\.-]+)", text)
    return m.group(1).strip() if m else ""

def first_phone(text):
    # match +123 456 7890 or 123-456-7890 or long digit sequences
    m = re.search(r"(\+?\d[\d\s\-]{6,}\d)", text)
    return m.group(1).strip() if m else ""

def collapse_repeats(value):
    if not value:
        return value
    # remove repeated 'Info:' or repeated email/phone blocks by taking text before second occurrence
    # If email exists, keep only up to first repeated email occurrence
    e = first_email(value)
    p = first_phone(value)
    # prefer to cut at the second appearance of email or phone or 'Info:' marker
    cut_pos = None
    if e:
        # find second occurrence
        idx1 = value.find(e)
        idx2 = value.find(e, idx1 + 1)
        if idx2 != -1:
            cut_pos = idx2
    if cut_pos is None and p:
        idx1 = value.find(p)
        idx2 = value.find(p, idx1 + 1)
        if idx2 != -1:
            cut_pos = idx2
    if cut_pos is None:
        info_idx = value.find('Info:')
        if info_idx != -1:
            # if 'Info:' appears later, cut it off
            # but if 'Info:' is at start and content has labels, keep more
            cut_pos = info_idx
    if cut_pos:
        value = value[:cut_pos]

    # strip stray label artifacts
    value = re.sub(r"\s+Info:\s*$", "", value).strip()
    # collapse multiple whitespace/newlines
    value = re.sub(r"\s+", " ", value).strip()
    return value

for field in fields:
    match = re.search(rf"{field}:\s*(.*?)(?=\s*(?:Phone:|Email:|Education:|Experience:|Skills:|Projects:|Tools:)|\Z)", resume_text, re.DOTALL)
    raw = match.group(1).strip() if match else ""
    cleaned = collapse_repeats(raw)
    parsed_info[field] = cleaned

# Heuristic fallbacks: if phone/email fields contain extra text or are empty, extract the first valid occurrence
if parsed_info.get("Phone"):
    # If phone field contains an email or many tokens, take the first phone-like substring
    phone_candidate = first_phone(parsed_info["Phone"]) or first_phone(resume_text)
    parsed_info["Phone"] = phone_candidate
else:
    parsed_info["Phone"] = first_phone(resume_text)

if parsed_info.get("Email"):
    email_candidate = first_email(parsed_info["Email"]) or first_email(resume_text)
    parsed_info["Email"] = email_candidate
else:
    parsed_info["Email"] = first_email(resume_text)

# Final pass: trim values to a reasonable length
for k, v in parsed_info.items():
    if isinstance(v, str) and len(v) > 400:
        parsed_info[k] = v[:400].rsplit(' ', 1)[0] + '...'

print("\n=== Parsed Info (JSON-like) ===\n")
print(json.dumps(parsed_info, indent=2, ensure_ascii=False))