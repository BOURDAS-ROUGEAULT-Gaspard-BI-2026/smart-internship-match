import json, os, time
import requests

# Adzuna Jobs API (https://developer.adzuna.com) -- replaces the France Travail
# "Offres d'emploi v2" API used in the original manual.
#
# Differences worth knowing compared to France Travail:
# - No OAuth2 / token step: app_id and app_key are passed as plain query
#   parameters on every request.
# - Pagination is in the URL path (/search/1, /search/2, ...) with
#   results_per_page (max 50), instead of a "range" parameter.
# - There is no "stage" contract type either (contract_type is only
#   "permanent" / "contract"), so -- like the France Travail version -- this
#   searches by keyword: real internship postings say "stage"/"stagiaire".
# - The "description" field is a SNIPPET (a few hundred characters), not the
#   full text. The full ad is only reachable via redirect_url. Keep that in
#   mind when interpreting what extract_offers.py manages to extract.
# - Free tier is rate-limited (on the order of a few hundred calls per day),
#   so keep MAX_PAGES small -- a weekly run needs only a handful of calls.

COUNTRY = "fr"
SEARCH_URL = f"https://api.adzuna.com/v1/api/jobs/{COUNTRY}/search/{{page}}"

APP_ID = os.environ["ADZUNA_APP_ID"]
APP_KEY = os.environ["ADZUNA_APP_KEY"]

# Edit this to your own search.
# - "what" requires ALL words to match (title + description). Use "what_or"
#   instead if you want ANY of several words.
# - No "where" filter: nationwide by default. Add e.g. "where": "Le Mans" and
#   "distance": 50 (km) to restrict to a region.
SEARCH_PARAMS = {
    "what": "stage informatique",
    "sort_by": "date",           # most recent first
    "results_per_page": 50,      # Adzuna's maximum per page
}
MAX_PAGES = 2                    # 2 x 50 = up to 100 offers per run

# 4xx errors (bad keys, bad parameters) won't fix themselves -- only retry
# on rate-limiting and server-side errors.
RETRYABLE_STATUS = {429, 500, 502, 503, 504}

def search_page(page, retries=4, backoff=5):
    params = {"app_id": APP_ID, "app_key": APP_KEY,
              "content-type": "application/json", **SEARCH_PARAMS}
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(SEARCH_URL.format(page=page), params=params,
                                timeout=(10, 30))
            print(f"  page {page}, attempt {attempt}/{retries}: HTTP {resp.status_code}")
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code not in RETRYABLE_STATUS:
                # Never print the request URL here: it contains app_key.
                raise RuntimeError(f"Adzuna returned HTTP {resp.status_code}: {resp.text[:500]}")
            last_error = RuntimeError(f"HTTP {resp.status_code}")
        except requests.exceptions.RequestException as e:
            # Report the exception type only: str(e) can include the full
            # URL, and therefore the app_key, in the public Actions logs.
            last_error = e
            print(f"  page {page}, attempt {attempt}/{retries} failed: {type(e).__name__}")
        if attempt < retries:
            time.sleep(backoff * attempt)
    raise RuntimeError(f"Could not fetch page {page} after {retries} attempts") from last_error

def main():
    offers, total = [], None
    for page in range(1, MAX_PAGES + 1):
        print(f"Searching Adzuna, page {page}...")
        data = search_page(page)
        total = data.get("count", total)
        results = data.get("results", [])
        offers.extend(results)
        if len(results) < SEARCH_PARAMS["results_per_page"]:
            break  # last page reached
        time.sleep(1)  # be gentle with the free-tier rate limit

    print(f"Found {len(offers)} offers (Adzuna reports {total} matching in total)")

    os.makedirs("data/offers", exist_ok=True)
    with open("data/offers/raw_offers.json", "w", encoding="utf-8") as f:
        json.dump({"fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "source": "adzuna",
                   "search_params": SEARCH_PARAMS,  # credentials deliberately not saved
                   "offers": offers}, f, indent=2, ensure_ascii=False)
    print("Wrote data/offers/raw_offers.json")
    if offers:
        print("First offer preview:", json.dumps(offers[0], ensure_ascii=False, indent=2)[:800])

if __name__ == "__main__":
    main()
