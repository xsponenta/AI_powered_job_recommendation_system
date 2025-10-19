import pandas as pd
import re
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline, BitsAndBytesConfig
from tqdm import tqdm
import torch
import time

DATA_PATH = "data/UpdatedResumeDataSet.csv"
OUTPUT_PATH = "cv_augmented_dataset.csv"
MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.2"
MAX_NEW_TOKENS = 300

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[INFO] Using device: {device}")

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16
)

print(f"[INFO] Loading model: {MODEL_NAME} in 4-bit")
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_NAME,
    device_map="auto",
    quantization_config=bnb_config,
    torch_dtype=torch.bfloat16
)

SYSTEM_PROMPT = """You are an expert at extracting structured information from resumes. 
Extract ONLY the following fields from the resume text. Format your response exactly as shown below:

Education: [list education details]
Experience: [list work experience]
Skills: [list skills and technologies]
Projects: [list key projects]
Tools: [list tools and software]

If a field is not found, write "Not specified". Be concise and only include relevant information."""

def create_prompt(resume_text):
    return f"""<s>[INST] {SYSTEM_PROMPT}

Resume Text:
{resume_text}

Extracted Information:
[/INST]"""

generator = pipeline(
    "text-generation", 
    model=model, 
    tokenizer=tokenizer, 
    max_new_tokens=MAX_NEW_TOKENS,
    temperature=0.1,
    do_sample=True
)

if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
generator.model.config.pad_token_id = generator.model.config.eos_token_id

df = pd.read_csv(DATA_PATH)
if "augmented_text" not in df.columns:
    df["augmented_text"] = ""

phone_regex = re.compile(r"\+?\d[\d\s-]{7,}\d")
email_regex = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")

def clean_extraction_result(text):
    """Clean the model output to remove prompt repetition"""

    if "Extracted Information:" in text:
        text = text.split("Extracted Information:")[-1].strip()
    
    text = text.replace("[INST]", "").replace("[/INST]", "").strip()
    
    return text

def parse_extracted_text(text):
    """Parse the extracted text into structured format"""
    lines = text.split('\n')
    parsed = {
        'Education': '',
        'Experience': '', 
        'Skills': '',
        'Projects': '',
        'Tools': ''
    }
    
    current_section = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        for section in parsed.keys():
            if line.lower().startswith(section.lower()):
                current_section = section
                content = line[len(section):].lstrip(' :')
                if content:
                    parsed[section] = content
                break
        else:
            if current_section and parsed[current_section]:
                parsed[current_section] += " " + line
            elif current_section:
                parsed[current_section] = line
                
    return parsed

start_time = time.time()
success = 0
total = len(df)

for i, row in tqdm(df.iterrows(), total=total, desc="Processing"):
    resume_text = str(row.get("Resume", "")).strip()
    if not resume_text:
        continue

    phone = phone_regex.findall(resume_text)
    email = email_regex.findall(resume_text)

    prompt = create_prompt(resume_text)

    try:
        result = generator(
            prompt, 
            max_new_tokens=MAX_NEW_TOKENS, 
            do_sample=True,
            temperature=0.1,
            pad_token_id=tokenizer.eos_token_id
        )[0]["generated_text"]
        
        clean_result = clean_extraction_result(result)
        
        parsed_info = parse_extracted_text(clean_result)
        
        structured_output = f"Phone: {', '.join(phone) if phone else 'Not specified'}\n"
        structured_output += f"Email: {', '.join(email) if email else 'Not specified'}\n"
        
        for section, content in parsed_info.items():
            if content:
                structured_output += f"{section}: {content}\n"
            else:
                structured_output += f"{section}: Not specified\n"
        
        df.at[i, "augmented_text"] = structured_output.strip()
        success += 1

        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()

        if (i + 1) % 3 == 0:
            df.to_csv(OUTPUT_PATH, index=False)

    except RuntimeError as e:
        print(f"Error at index {i}: {e}")
        torch.cuda.empty_cache()
        continue
    except Exception as e:
        print(f"Unexpected error at index {i}: {e}")
        continue

df.to_csv(OUTPUT_PATH, index=False)
end_time = time.time()
print(f"Done. Successful extractions: {success}/{total}")
print(f"Time taken: {end_time - start_time:.2f} seconds")