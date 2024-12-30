from groq import Groq
import os
import csv
from pathlib import Path
from tqdm import tqdm

API_KEY = os.getenv("GROQ_API_KEY")

client = Groq(
    api_key=API_KEY
)


def update_cwe_ids(csv_filepath):
    with open(csv_filepath, mode='r') as file:
        reader = csv.DictReader(file)
        rows = list(reader)

    for row in tqdm(rows, desc="Updating CWE IDs"):
        if row['cwe'] == 'CWE-unknown':
            rule = row['id']
            completion = client.chat.completions.create(
                model="llama-3.1-70b-versatile",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a cybersecurity expert specializing in static code analysis and vulnerability mapping. Your role is to accurately map warnings from static analysis tools (CodeQL, PMD, SpotBugs, Semgrep) to their corresponding CWE (Common Weakness Enumeration) IDs in the format 'CWE-xxxx'.\n\nWhen given a warning, identify the most relevant CWE ID and provide a brief explanation for your mapping decision. Ensure your responses are concise, accurate, and align with standard cybersecurity practices. If the warning is ambiguous, suggest the closest matching CWE ID based on the provided context.\n\nYour output should only contain CWE-xxx without any irrelevant messages."
                    },
                    {
                        "role": "user",
                        "content": rule
                    },
                ],
                temperature=0.5,
                max_tokens=1024,
                top_p=0.65,
                stream=False,
                stop=None,
            )
            cwe_id = 'CWE-unknown'
            got_cwe_id = completion.choices[0].message.content
            if got_cwe_id.startswith('CWE-'):
                cwe_id = got_cwe_id
            row['cwe'] = cwe_id

    with open(csv_filepath, mode='w', newline='') as file:
        writer = csv.DictWriter(file, fieldnames=reader.fieldnames)
        writer.writeheader()
        writer.writerows(rows)

update_cwe_ids(Path('./rules.csv').absolute())
