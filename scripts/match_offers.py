import csv, json, os, re, time, unicodedata

def load_profile(path="data/profile/my_skills.csv"):
    profile = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            profile[row["skill"]] = {"level": int(row["level"]), "evidence": row["evidence"]}
    return profile

# --- KPI de correspondance ---------------------------------------------------
#
# Choix de conception (chacun est délibéré et justifiable, cf. CM2) :
#
# 1. Comparaison normalisée, pas de chaînes brutes. L'extraction par IA renvoie
#    la même compétence avec une casse, des accents ou une ponctuation
#    différents ("Computer vision" / "computer vision", "Cybersécurité" /
#    "cybersecurite"). Les deux côtés sont donc mis en minuscules, sans accents
#    ni ponctuation, avant la comparaison.
#
# 2. Une table d'alias explicite, et PAS de recherche de sous-chaîne. Les offres
#    sont en français et en anglais alors que le profil utilise des noms fixes :
#    "Anglais" doit correspondre à "English", "Postgres" à "PostgreSQL". La
#    recherche de sous-chaîne se tromperait justement dans les cas importants :
#    "C" est contenu dans "C++" et "C#", "Java" dans "JavaScript", "SQL" dans
#    "NoSQL". Les alias rendent chaque correspondance explicable ; les variantes
#    inconnues apparaissent dans "gaps", où elles sont visibles et peuvent être
#    ajoutées ici.
#
# 3. Score pondéré par le niveau. Posséder une compétence au niveau 4/5 compte
#    plus qu'au niveau 2/5 :
#    score = somme(niveau / 5 des compétences possédées) / (n + PRIOR).
#
# 4. Pénalité pour petit échantillon (PRIOR). Sans elle, une offre dont
#    l'extraction n'a trouvé qu'une seule compétence, que l'on possède, aurait
#    un score parfait de 1.0 et passerait devant une offre où l'on possède 6
#    compétences sur 8. Ajouter PRIOR "compétences inconnues virtuelles" au
#    dénominateur signifie : plus de preuves = plus de confiance.
#    La couverture (coverage) reste la fraction simple, non pénalisée : c'est
#    elle que lit le filtre MIN_COVERAGE de draft_cv.py.
#
# 5. Une offre sans aucune compétence extraite obtient un score de 0 et une
#    couverture de 0 : rien ne prouve qu'elle correspond, elle ne doit donc pas
#    passer devant des offres qui correspondent.

PRIOR = 2
MAX_LEVEL = 5

# formulation normalisée côté offre -> nom exact de la compétence dans my_skills.csv
ALIASES = {
    "python3": "Python",
    "js": "JavaScript",
    "ecmascript": "JavaScript",
    "csharp": "C#",
    "c sharp": "C#",
    "langage c": "C",
    "postgres": "PostgreSQL",
    "html5": "HTML",
    "css3": "CSS",
    "github": "Git",
    "gitlab": "Git",
    "rest": "API REST",
    "rest api": "API REST",
    "api": "API REST",
    "apis": "API REST",
    "api rest": "API REST",
    "restful api": "API REST",
    "huggingface": "Hugging Face",
    "transformers": "Hugging Face",
    "ml": "Machine Learning",
    "apprentissage automatique": "Machine Learning",
    "data analyse": "Data Analysis",
    "analyse de donnees": "Data Analysis",
    "data analytics": "Data Analysis",
    "reseau": "Network",
    "reseaux": "Network",
    "networking": "Network",
    "tcp ip": "Network",
    "cybersecurite": "Cybersecurity",
    "securite informatique": "Cybersecurity",
    "cyber security": "Cybersecurity",
    "gestion de projet": "Project Management",
    "project management": "Project Management",
    "anglais": "English",
    "anglais courant": "English",
    "anglais professionnel": "English",
    "fluent english": "English",
    "android": "Android Studio",
}

def normalize_skill(name):
    """Met en minuscules, retire les accents, remplace la ponctuation par des
    espaces -- mais garde les caractères qui FONT PARTIE du nom de la
    compétence ("C#", "C++", ".NET")."""
    s = unicodedata.normalize("NFKD", name or "")
    s = "".join(ch for ch in s if not unicodedata.combining(ch)).lower().strip()
    s = re.sub(r"[^a-z0-9#+.]+", " ", s)
    s = re.sub(r"\.(?![a-z0-9])", " ", s)  # retire les points finaux, garde ".net"/"node.js"
    return " ".join(s.split())

def score_offer(profile, required_skills):
    lookup = {normalize_skill(k): k for k in profile}
    for alias, target in ALIASES.items():
        if target in profile:
            lookup.setdefault(normalize_skill(alias), target)

    # Dédoublonne les compétences de l'offre après normalisation : "Python" et
    # "python" listés deux fois par l'IA ne comptent pas comme deux exigences.
    unique = {}
    for raw in required_skills or []:
        key = normalize_skill(raw)
        if key and key not in unique:
            unique[key] = raw

    matched, gaps = [], []
    for key, raw in unique.items():
        skill = lookup.get(key)
        if skill is None:
            gaps.append(raw)
        elif skill not in matched:
            # Nom du profil, pas la formulation de l'offre : build_output et
            # draft_cv.py cherchent les compétences possédées par leur nom
            # dans le profil.
            matched.append(skill)
        # sinon : deux compétences de l'offre renvoient à la même compétence
        # du profil ("Git" et "GitHub") -- comptées une seule fois.

    n = len(matched) + len(gaps)
    if n == 0:
        return {"score": 0.0, "coverage": 0.0, "matched": [], "gaps": []}

    weighted = sum(profile[s]["level"] / MAX_LEVEL for s in matched)
    return {
        "score": round(weighted / (n + PRIOR), 4),
        "coverage": round(len(matched) / n, 4),
        "matched": matched,
        "gaps": gaps,
    }

def build_output(results, profile):
    gap_counts = {}
    matched_counts = {}
    for r in results:
        for g in r["gaps"]:
            gap_counts[g] = gap_counts.get(g, 0) + 1
        for s in r["matched"]:
            matched_counts[s] = matched_counts.get(s, 0) + 1
    top_gaps = sorted(gap_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    top_matched = sorted(matched_counts.items(), key=lambda kv: kv[1], reverse=True)[:10]
    n_with_comp = sum(1 for r in results if r.get("compensation_mentioned"))
    return {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "n_offers": len(results),
        "offers": results,
        "top_skill_gaps": [{"skill": s, "count": c} for s, c in top_gaps],
        # top_matched_skills mirrors top_skill_gaps but for what you're already
        # strong in -- ranked by how often it's actually asked for across your real
        # offers, with your own self-assessed level attached so the dashboard can
        # highlight "your most in-demand strength", not just "a skill you have".
        "top_matched_skills": [{"skill": s, "count": c, "level": profile[s]["level"]} for s, c in top_matched],
        # Set expectations, don't hide the gap: real testing (see Step 12's note)
        # found compensation stated explicitly in only ~6.5% of real postings, so
        # this is reported as a count, not built into a chart that would mostly be
        # empty space.
        "n_offers_with_compensation": n_with_comp,
    }

def main():
    profile = load_profile()
    with open("data/offers/structured_offers.json", encoding="utf-8") as f:
        data = json.load(f)

    # extract_offers.py ne recopie pas url/date_posted : on les reprend depuis
    # merged_offers.json (par id) pour que le dashboard puisse lier chaque
    # offre -- obligatoire pour afficher des offres Adzuna.
    links = {}
    if os.path.exists("data/offers/merged_offers.json"):
        with open("data/offers/merged_offers.json", encoding="utf-8") as f:
            links = {o["id"]: o for o in json.load(f)["offers"]}

    results = []
    for offer in data["offers"]:
        m = score_offer(profile, offer["required_skills"])
        src = links.get(offer["id"], {})
        extra = {"url": src.get("url"), "date_posted": src.get("date_posted")}
        results.append({**extra, **offer, **m})

    results.sort(key=lambda r: r["score"], reverse=True)
    for r in results:
        print(f"  {r['score']:.3f}  {r['title']} @ {r['company']}  ({r['source']}, "
              f"coverage {r['coverage']:.0%}, gaps: {r['gaps']})")

    # Two outputs, not one: matches_all_local.json (every source, gitignored, for
    # your own eyes only) and docs/data/matches.json (publishable sources only,
    # committed, visible on your public Pages dashboard). "publishable" was set in
    # Step 11c -- True for France Travail's official data, False for anything from
    # jobspy (Step 11b). If you never did Step 11b, every offer is publishable and
    # the two files end up identical -- this split is a genuine no-op with one source.
    os.makedirs("data/offers", exist_ok=True)
    with open("data/offers/matches_all_local.json", "w", encoding="utf-8") as f:
        json.dump(build_output(results, profile), f, indent=2, ensure_ascii=False)
    print(f"Wrote data/offers/matches_all_local.json ({len(results)} offers) -- gitignored, local only")

    public_results = [r for r in results if r.get("publishable", False)]
    os.makedirs("docs/data", exist_ok=True)
    with open("docs/data/matches.json", "w", encoding="utf-8") as f:
        json.dump(build_output(public_results, profile), f, indent=2, ensure_ascii=False)
    print(f"Wrote docs/data/matches.json ({len(public_results)} of {len(results)} offers -- publishable sources only)")

if __name__ == "__main__":
    main()
