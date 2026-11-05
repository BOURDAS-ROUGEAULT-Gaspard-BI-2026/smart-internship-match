import json, os, re

RAW_ADZUNA_PATH = "data/offers/raw_offers.json"
JOBSPY_PATH = "data/offers/jobspy_offers.json"
MERGED_PATH = "data/offers/merged_offers.json"

APPRENTICESHIP_RE = re.compile(r"alternan|apprenti", re.IGNORECASE)

def normalize_adzuna(raw_offers):
    # Adzuna's documented result fields: id, title, description (a snippet,
    # not the full text), company.display_name, location.display_name,
    # redirect_url, created. Adzuna has no apprenticeship or disability flag:
    # apprenticeship is guessed from the title, disability is unknown (False).
    normalized = []
    for o in raw_offers:
        title = o.get("title") or ""
        normalized.append({
            "id": f"adz_{o['id']}",
            "source": "adzuna",
            "title": title,
            "company": (o.get("company") or {}).get("display_name"),
            "location": (o.get("location") or {}).get("display_name"),
            "description": o.get("description", ""),
            "url": o.get("redirect_url"),
            "date_posted": o.get("created"),
            "is_apprenticeship": bool(APPRENTICESHIP_RE.search(title)),
            "accessible_disability": False,
            # Adzuna's API terms allow displaying results, provided they are
            # attributed to Adzuna and link to redirect_url -- if you publish
            # them, show "Jobs by Adzuna" and keep the url.
            "publishable": True,
        })
    return normalized

def load_jobspy():
    if not os.path.exists(JOBSPY_PATH):
        print(f"{JOBSPY_PATH} not found -- skipping (fine if you didn't do Step 11b).")
        return []
    with open(JOBSPY_PATH, encoding="utf-8") as f:
        data = json.load(f)
    return [
        {**o, "is_apprenticeship": False, "accessible_disability": False,
         "publishable": False}  # scraped content -- never published, see Step 11b
        for o in data["offers"]
    ]

def main():
    with open(RAW_ADZUNA_PATH, encoding="utf-8") as f:
        adzuna_raw = json.load(f)
    adzuna_offers = normalize_adzuna(adzuna_raw["offers"])
    jobspy_offers = load_jobspy()

    merged = adzuna_offers + jobspy_offers
    print(f"Merged {len(adzuna_offers)} Adzuna + {len(jobspy_offers)} jobspy = {len(merged)} total")

    os.makedirs("data/offers", exist_ok=True)
    with open(MERGED_PATH, "w", encoding="utf-8") as f:
        json.dump({"offers": merged}, f, indent=2, ensure_ascii=False)
    print(f"Wrote {MERGED_PATH} ({len(merged)} offers) -- gitignored, local only")

if __name__ == "__main__":
    main()
