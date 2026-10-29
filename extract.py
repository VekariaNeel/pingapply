import os, json, re
from groq import Groq

groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])
GROQ_MODEL = os.environ.get("GROQ_MODEL", "openai/gpt-oss-120b")

def extract_job(text: str) -> dict:
    res = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        temperature=0,
        messages=[{
            "role": "user",
            "content": f"""Extract job posting info from this WhatsApp message. Reply ONLY valid JSON, no markdown fences.
Schema: {{"is_job_posting": bool, "role": string|null, "skills": [string], "location": string|null, "contact_phone": string|null, "contact_email": string|null}}

Message: \"\"\"{text}\"\"\""""
        }]
    )
    content = res.choices[0].message.content.strip()
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content, flags=re.IGNORECASE).strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {"is_job_posting": False}
