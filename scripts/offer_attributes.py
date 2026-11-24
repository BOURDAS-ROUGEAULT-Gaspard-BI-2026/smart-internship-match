"""Attributs dérivés d'une offre, utilisés par les filtres du dashboard :
lieu découpé en région / département / ville, et type d'offre.

Pourquoi un module à part : merge_offer_sources.py (au moment de la fusion, où
l'on a encore les champs bruts d'Adzuna) et match_offers.py (en secours, pour
une offre dont on n'a plus que le texte du lieu) doivent produire exactement
les mêmes valeurs.
"""
import re, unicodedata

# --- Lieu ----------------------------------------------------------------------

# code -> (département, région). Sert quand Adzuna ne fournit pas "area" et
# pour les lieux venant de jobspy ("Nantes (44)", "Le Mans, Pays de la Loire").
DEPARTMENTS = {
    "01": ("Ain", "Auvergne-Rhône-Alpes"), "02": ("Aisne", "Hauts-de-France"),
    "03": ("Allier", "Auvergne-Rhône-Alpes"), "04": ("Alpes-de-Haute-Provence", "Provence-Alpes-Côte d'Azur"),
    "05": ("Hautes-Alpes", "Provence-Alpes-Côte d'Azur"), "06": ("Alpes-Maritimes", "Provence-Alpes-Côte d'Azur"),
    "07": ("Ardèche", "Auvergne-Rhône-Alpes"), "08": ("Ardennes", "Grand Est"),
    "09": ("Ariège", "Occitanie"), "10": ("Aube", "Grand Est"), "11": ("Aude", "Occitanie"),
    "12": ("Aveyron", "Occitanie"), "13": ("Bouches-du-Rhône", "Provence-Alpes-Côte d'Azur"),
    "14": ("Calvados", "Normandie"), "15": ("Cantal", "Auvergne-Rhône-Alpes"),
    "16": ("Charente", "Nouvelle-Aquitaine"), "17": ("Charente-Maritime", "Nouvelle-Aquitaine"),
    "18": ("Cher", "Centre-Val de Loire"), "19": ("Corrèze", "Nouvelle-Aquitaine"),
    "2A": ("Corse-du-Sud", "Corse"), "2B": ("Haute-Corse", "Corse"),
    "21": ("Côte-d'Or", "Bourgogne-Franche-Comté"), "22": ("Côtes-d'Armor", "Bretagne"),
    "23": ("Creuse", "Nouvelle-Aquitaine"), "24": ("Dordogne", "Nouvelle-Aquitaine"),
    "25": ("Doubs", "Bourgogne-Franche-Comté"), "26": ("Drôme", "Auvergne-Rhône-Alpes"),
    "27": ("Eure", "Normandie"), "28": ("Eure-et-Loir", "Centre-Val de Loire"),
    "29": ("Finistère", "Bretagne"), "30": ("Gard", "Occitanie"),
    "31": ("Haute-Garonne", "Occitanie"), "32": ("Gers", "Occitanie"),
    "33": ("Gironde", "Nouvelle-Aquitaine"), "34": ("Hérault", "Occitanie"),
    "35": ("Ille-et-Vilaine", "Bretagne"), "36": ("Indre", "Centre-Val de Loire"),
    "37": ("Indre-et-Loire", "Centre-Val de Loire"), "38": ("Isère", "Auvergne-Rhône-Alpes"),
    "39": ("Jura", "Bourgogne-Franche-Comté"), "40": ("Landes", "Nouvelle-Aquitaine"),
    "41": ("Loir-et-Cher", "Centre-Val de Loire"), "42": ("Loire", "Auvergne-Rhône-Alpes"),
    "43": ("Haute-Loire", "Auvergne-Rhône-Alpes"), "44": ("Loire-Atlantique", "Pays de la Loire"),
    "45": ("Loiret", "Centre-Val de Loire"), "46": ("Lot", "Occitanie"),
    "47": ("Lot-et-Garonne", "Nouvelle-Aquitaine"), "48": ("Lozère", "Occitanie"),
    "49": ("Maine-et-Loire", "Pays de la Loire"), "50": ("Manche", "Normandie"),
    "51": ("Marne", "Grand Est"), "52": ("Haute-Marne", "Grand Est"),
    "53": ("Mayenne", "Pays de la Loire"), "54": ("Meurthe-et-Moselle", "Grand Est"),
    "55": ("Meuse", "Grand Est"), "56": ("Morbihan", "Bretagne"),
    "57": ("Moselle", "Grand Est"), "58": ("Nièvre", "Bourgogne-Franche-Comté"),
    "59": ("Nord", "Hauts-de-France"), "60": ("Oise", "Hauts-de-France"),
    "61": ("Orne", "Normandie"), "62": ("Pas-de-Calais", "Hauts-de-France"),
    "63": ("Puy-de-Dôme", "Auvergne-Rhône-Alpes"), "64": ("Pyrénées-Atlantiques", "Nouvelle-Aquitaine"),
    "65": ("Hautes-Pyrénées", "Occitanie"), "66": ("Pyrénées-Orientales", "Occitanie"),
    "67": ("Bas-Rhin", "Grand Est"), "68": ("Haut-Rhin", "Grand Est"),
    "69": ("Rhône", "Auvergne-Rhône-Alpes"), "70": ("Haute-Saône", "Bourgogne-Franche-Comté"),
    "71": ("Saône-et-Loire", "Bourgogne-Franche-Comté"), "72": ("Sarthe", "Pays de la Loire"),
    "73": ("Savoie", "Auvergne-Rhône-Alpes"), "74": ("Haute-Savoie", "Auvergne-Rhône-Alpes"),
    "75": ("Paris", "Île-de-France"), "76": ("Seine-Maritime", "Normandie"),
    "77": ("Seine-et-Marne", "Île-de-France"), "78": ("Yvelines", "Île-de-France"),
    "79": ("Deux-Sèvres", "Nouvelle-Aquitaine"), "80": ("Somme", "Hauts-de-France"),
    "81": ("Tarn", "Occitanie"), "82": ("Tarn-et-Garonne", "Occitanie"),
    "83": ("Var", "Provence-Alpes-Côte d'Azur"), "84": ("Vaucluse", "Provence-Alpes-Côte d'Azur"),
    "85": ("Vendée", "Pays de la Loire"), "86": ("Vienne", "Nouvelle-Aquitaine"),
    "87": ("Haute-Vienne", "Nouvelle-Aquitaine"), "88": ("Vosges", "Grand Est"),
    "89": ("Yonne", "Bourgogne-Franche-Comté"), "90": ("Territoire de Belfort", "Bourgogne-Franche-Comté"),
    "91": ("Essonne", "Île-de-France"), "92": ("Hauts-de-Seine", "Île-de-France"),
    "93": ("Seine-Saint-Denis", "Île-de-France"), "94": ("Val-de-Marne", "Île-de-France"),
    "95": ("Val-d'Oise", "Île-de-France"),
    "971": ("Guadeloupe", "Guadeloupe"), "972": ("Martinique", "Martinique"),
    "973": ("Guyane", "Guyane"), "974": ("La Réunion", "La Réunion"), "976": ("Mayotte", "Mayotte"),
}

# Grandes villes et villes vues dans les offres -> code département. Adzuna
# écrit souvent "Ville, Arrondissement" ("Vélizy-Villacoublay, Versailles") :
# sans "area", seule cette table permet de remonter à la région. Une ville
# absente garde sa ville, avec une région inconnue -- elle reste filtrable par
# son nom.
CITIES = {
    "Paris": "75", "Marseille": "13", "Lyon": "69", "Toulouse": "31", "Nice": "06",
    "Nantes": "44", "Montpellier": "34", "Strasbourg": "67", "Bordeaux": "33",
    "Lille": "59", "Rennes": "35", "Reims": "51", "Toulon": "83", "Saint-Étienne": "42",
    "Le Havre": "76", "Grenoble": "38", "Dijon": "21", "Angers": "49", "Nîmes": "30",
    "Clermont-Ferrand": "63", "Le Mans": "72", "Aix-en-Provence": "13", "Brest": "29",
    "Tours": "37", "Amiens": "80", "Limoges": "87", "Annecy": "74", "Metz": "57",
    "Besançon": "25", "Perpignan": "66", "Orléans": "45", "Rouen": "76", "Caen": "14",
    "Nancy": "54", "Mulhouse": "68", "Poitiers": "86", "La Rochelle": "17", "Laval": "53",
    "Cholet": "49", "Saint-Nazaire": "44", "Versailles": "78", "Nanterre": "92",
    "Antony": "92", "Palaiseau": "91", "Grasse": "06", "Cannes": "06", "Vannes": "56",
    "Lorient": "56", "Niort": "79", "Pau": "64", "Bayonne": "64", "Valence": "26",
    "Chambéry": "73", "Évry": "91", "Massy": "91", "Boulogne-Billancourt": "92",
    "Issy-les-Moulineaux": "92", "La Défense": "92", "Sophia Antipolis": "06",
    "La Ciotat": "13", "Abbeville": "80", "Genas": "69", "Cherbourg-Octeville": "50",
    "Cherbourg-en-Cotentin": "50", "La Roche-sur-Yon": "85", "Angoulême": "16",
    "Troyes": "10", "Gex": "01", "Saint-Malo": "35", "Lannion": "22", "Quimper": "29",
}

def _key(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", s).split())

_DEPT_BY_KEY = {_key(name): code for code, (name, _) in DEPARTMENTS.items()}
_REGION_BY_KEY = {_key(region): region for _, region in DEPARTMENTS.values()}
_CITY_BY_KEY = {_key(name): (name, code) for name, code in CITIES.items()}

def _dept(code):
    name, region = DEPARTMENTS[code]
    return name, region

def location_parts(display_name=None, area=None):
    """-> {"region", "department", "city"} ; chaque valeur peut être None
    (offre localisée seulement "France", ou ville inconnue de la table)."""
    out = {"region": None, "department": None, "city": None}

    # 1. Adzuna "area" : [pays, région, département, (arrondissement), ville]
    if area and len(area) >= 2:
        reg = area[1]
        out["region"] = _REGION_BY_KEY.get(_key(reg), reg)
        if len(area) >= 3:
            code = _DEPT_BY_KEY.get(_key(area[2]))
            out["department"] = DEPARTMENTS[code][0] if code else area[2]
        if len(area) >= 4:
            out["city"] = area[-1]
        return out

    # 2. Sinon, on lit le texte : "Ville, Département", "Département, Région",
    #    "Ville, Arrondissement", "Nantes (44)", "Nantes, Pays de la Loire, FR"...
    text = display_name or ""
    code_m = re.search(r"\((\d{2,3}|2[ab])\)", text, re.IGNORECASE)
    parts = [p.strip() for p in re.sub(r"\(.*?\)", "", text).split(",") if p.strip()]
    city = None
    for p in parts:
        k = _key(p)
        if k in ("france", "fr"):
            continue
        if k in _REGION_BY_KEY:
            out["region"] = out["region"] or _REGION_BY_KEY[k]
        elif k in _DEPT_BY_KEY and k != "paris":  # Paris : ville ET département, traité plus bas
            name, region = _dept(_DEPT_BY_KEY[k])
            out["department"] = out["department"] or name
            out["region"] = out["region"] or region
        elif city is None:
            city = p
        elif k in _CITY_BY_KEY and not out["department"]:
            # "Vélizy-Villacoublay, Versailles" : le 2e nom est une ville connue
            name, region = _dept(_CITY_BY_KEY[k][1])
            out["department"], out["region"] = name, region
    if code_m and not out["department"]:
        code = code_m.group(1).upper().zfill(2)
        if code in DEPARTMENTS:
            out["department"], out["region"] = _dept(code)
    if city:
        known = _CITY_BY_KEY.get(_key(city))
        out["city"] = known[0] if known else city
        if known and not out["department"]:
            out["department"], out["region"] = _dept(known[1])
    if out["city"] == "Paris":
        out["department"], out["region"] = _dept("75")
    return out

# --- Type d'offre --------------------------------------------------------------
#
# Adzuna n'a pas de type "stage" (contract_type vaut seulement "permanent" ou
# "contract"), d'où la lecture du titre en premier. Une offre peut avoir
# plusieurs types ("Stage ou alternance") : on renvoie une liste.

OFFER_TYPES = ["Stage", "Alternance", "CDI", "CDD", "Non précisé"]

_TYPE_PATTERNS = [
    ("Stage", re.compile(r"\bstag(e|es|iaire|iaires)\b|\bintern(ship)?\b|\bpfe\b|fin d.?[eé]tudes", re.I)),
    ("Alternance", re.compile(r"alternan|apprenti|contrat pro", re.I)),
    ("CDI", re.compile(r"\bcdi\b", re.I)),
    ("CDD", re.compile(r"\bcdd\b|int[eé]rim", re.I)),
]

def offer_types(title, contract_type=None, job_type=None):
    found = [t for t, rx in _TYPE_PATTERNS if rx.search(title or "")]
    if not found and job_type and "intern" in str(job_type).lower():
        found = ["Stage"]  # jobspy : job_type == "internship"
    if not found and contract_type == "permanent":
        found = ["CDI"]
    # contract_type == "contract" (Adzuna) ne distingue pas stage, CDD ou
    # mission : on ne l'utilise pas pour éviter de classer un stage en CDD.
    return found or ["Non précisé"]

def offer_attributes(location=None, area=None, title=None, contract_type=None, job_type=None):
    return {**location_parts(location, area),
            "offer_types": offer_types(title, contract_type, job_type)}
