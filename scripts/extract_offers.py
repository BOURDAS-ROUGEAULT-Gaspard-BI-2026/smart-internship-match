import json, os, time
import requests

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "qwen3:8b"

PROMPT_TEMPLATE = """Extract ONLY these things from this job/internship description text
(it may be in French or English).
Return ONLY valid JSON with keys:
- required_skills: array of concrete named tools/technologies/hard skills mentioned (e.g. "Python", "Power BI") -- do not include generic soft skills or the job title
- responsibilities: array of the actual tasks/missions described
- experience_required: a short string quoting the explicit experience requirement stated in the text (e.g. "2 years", "no experience required", "Bac+5", "enrolled in a Master's program"), or null if the text does not explicitly state one. Do NOT infer this from the job title, from words like "Senior"/"Lead" in the title, or from general seniority tone -- only from an actual requirement sentence in the text.
- compensation_mentioned: a short verbatim quote of any salary/compensation/gratification FIGURE explicitly stated in the text (e.g. "75-90k EUR package", "600 euros/mois"), or null if no concrete number is stated anywhere in the text. Read the ENTIRE text, including the end, before concluding there is none.

Do not extract title, company, or location -- those come from elsewhere and are not in this text.
No explanation, just the JSON object.

TEXT:
{text}
"""

def call_ollama(prompt, retries=3, backoff=5):
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(
                OLLAMA_URL,
                proxies={"http": None, "https": None},
                json={"model": MODEL, "prompt": prompt, "format": "json", "stream": False},
                timeout=(10, 120),
            )
            resp.raise_for_status()
            return json.loads(resp.json()["response"])
        except Exception as e:
            last_error = e
            print(f"  Ollama call attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                time.sleep(backoff)
    raise RuntimeError(f"Ollama unreachable or model not available after {retries} attempts") from last_error

def main():
    # Reads the merged, common-schema file (Step 11c), not raw_offers.json directly
    # -- this script no longer needs to know which source an offer came from, since
    # merge_offer_sources.py already normalized every source to the same field names.
    with open("data/offers/merged_offers.json", encoding="utf-8") as f:
        merged = json.load(f)

    structured = []
    for offer in merged["offers"]:
        print(f"Extracting offer {offer['id']} ({offer['source']}): {offer['title']}...")
        extracted = call_ollama(PROMPT_TEMPLATE.format(text=offer.get("description", "")))
        structured.append({
            "id": offer["id"],
            "source": offer["source"],
            "title": offer["title"],
            "company": offer.get("company"),
            "location": offer.get("location"),
            "is_apprenticeship": offer.get("is_apprenticeship", False),
            "accessible_disability": offer.get("accessible_disability", False),
            "publishable": offer.get("publishable", False),
            "required_skills": extracted.get("required_skills", []),
            "responsibilities": extracted.get("responsibilities", []),
            "experience_required": extracted.get("experience_required"),
            "compensation_mentioned": extracted.get("compensation_mentioned"),
        })

    os.makedirs("data/offers", exist_ok=True)
    with open("data/offers/structured_offers.json", "w", encoding="utf-8") as f:
        json.dump({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "offers": structured}, f, indent=2, ensure_ascii=False)
    print(f"Wrote data/offers/structured_offers.json ({len(structured)} offers) -- gitignored, local only")

if __name__ == "__main__":
    main()
