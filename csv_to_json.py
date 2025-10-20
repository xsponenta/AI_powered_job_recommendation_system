import csv
import json

input_csv = "cv_augmented_dataset.csv"

output_jsonl = "cv_augmented_dataset.jsonl"

with open(input_csv, newline='', encoding="utf-8") as csvfile, open(output_jsonl, "w", encoding="utf-8") as jsonlfile:
    reader = csv.DictReader(csvfile)
    
    for i, row in enumerate(reader):
        compl_lines = row["augmented_text"].splitlines()
        if compl_lines == []:
            print('compl_lines emplty', i)
            continue
        try:
            data = {
                "category": row["Category"].strip(),
                "resume": row["Resume"].strip() + "\n\n###\n\n",
                    "info": {
                    
                            "Phone": compl_lines[0][compl_lines[0].index(':')+2:],
                            "Email": compl_lines[1][compl_lines[1].index(':')+2:],
                            "Education": compl_lines[2][compl_lines[2].index(':')+2:],
                            "Experience": compl_lines[3][compl_lines[3].index(':')+2:],
                            "Skills": compl_lines[4][compl_lines[4].index(':')+2:],
                            "Projects": compl_lines[5][compl_lines[5].index(':')+2:],
                            "Tools": compl_lines[6][compl_lines[6].index(':')+2:]
                    }
            }
        except ValueError:
            continue

        jsonlfile.write(json.dumps(data, ensure_ascii=False) +'\n')

print(f"Converted {input_csv} to {output_jsonl} successfully!")