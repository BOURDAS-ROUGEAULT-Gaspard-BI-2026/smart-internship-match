import json, os, time
import pandas as pd
from jobspy import scrape_jobs

# See the caveats above before running this. Summary: jobspy scrapes commercial
# platforms whose ToS prohibits it -- a different risk category than every other
# source in this course. Runs local-only, on demand, never in GitHub Actions.

SITES = ["indeed", "zip_recruiter"]  # deliberately excludes linkedin, google -- see Step 11b
SEARCH_TERM = "stage informatique"
LOCATION = "France"
RESULTS_WANTED = 30
HOURS_OLD = 336  # 14 days -- this runs manually/occasionally, not on a schedule

def safe(row, key, default=None):
    # pandas NaN is truthy in Python (bool(float('nan')) is True), so a plain
    # `row.get(key) or default` silently returns the NaN itself instead of the
    # default -- confirmed on real scraped data, where ~half the rows had NaN
    # in optional fields like `description`. pd.notna() is the actual check needed.
    v = row.get(key)
    return v if pd.notna(v) else default

def main():
    print(f"Scraping {SITES} for '{SEARCH_TERM}' in {LOCATION}...")
    jobs = scrape_jobs(
        site_name=SITES,
        search_term=SEARCH_TERM,
        location=LOCATION,
        results_wanted=RESULTS_WANTED,
        hours_old=HOURS_OLD,
        country_indeed=LOCATION,
    )
    print(f"Found {len(jobs)} raw results")

    # jobspy normalizes job_type across sites into its own vocabulary that includes
    # "internship" directly -- confirmed on a real run of this exact logic
    # (2026-09-08): a genuine French "Stage" posting on Indeed came back with
    # job_type == "internship". More precise than France Travail's contract-type
    # taxonomy, which has no internship category at all (see fetch_offers.py).
    interns = jobs[jobs["job_type"].fillna("").str.contains("internship", case=False)]
    print(f"{len(interns)} of those are tagged job_type=internship")

    offers = []
    for _, row in interns.iterrows():
        offers.append({
            "id": f"jobspy_{safe(row, 'id')}",
            "source": safe(row, "site"),
            "title": safe(row, "title"),
            "company": safe(row, "company"),
            "location": safe(row, "location"),
            "description": safe(row, "description", ""),
            "url": safe(row, "job_url"),
            "date_posted": str(safe(row, "date_posted")) if safe(row, "date_posted") else None,
        })

    os.makedirs("data/offers", exist_ok=True)
    with open("data/offers/jobspy_offers.json", "w", encoding="utf-8") as f:
        json.dump({"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "offers": offers}, f, indent=2, ensure_ascii=False)
    print(f"Wrote data/offers/jobspy_offers.json ({len(offers)} offers) -- gitignored, local only")

if __name__ == "__main__":
    main()
