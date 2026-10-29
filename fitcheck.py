import os, json, re
from groq import Groq

groq_client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

RESUME_PATH = "resume.txt"
if not os.path.exists(RESUME_PATH):
    if os.path.exists("resume.example.txt"):
        print("[Warning] 'resume.txt' not found! Falling back to 'resume.example.txt'. Please create your own 'resume.txt'.")
        RESUME_PATH = "resume.example.txt"
    else:
        raise FileNotFoundError("Neither 'resume.txt' nor 'resume.example.txt' was found in the project root.")

with open(RESUME_PATH, encoding="utf-8") as f:
    RESUME_TEXT = f.read()

def fit_check(job: dict) -> dict:
    res = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0,
        messages=[{
            "role": "user",
            "content": f"""Score how well this candidate's resume fits this job, 0-100. Reply ONLY JSON: {{"score": number, "reason": string}}

Resume:
{RESUME_TEXT}

Job: {json.dumps(job)}"""
        }]
    )
    content = res.choices[0].message.content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE).strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"score": 0, "reason": "parse failed"}
