# smart-internship-match

Lien vers le Dashboard : https://bourdas-rougeault-gaspard-bi-2026.github.io/smart-internship-match/

## Source des offres : Adzuna au lieu de France Travail

À la demande de l'enseignant, l'API France Travail (francetravail.io), prévue par le
manuel du TP, a été remplacée par l'**API Adzuna** ([developer.adzuna.com](https://developer.adzuna.com)).

### Ce qui a changé

| | France Travail (manuel) | Adzuna (ce dépôt) |
|---|---|---|
| Inscription | Création d'une « application » + abonnement à « Offres d'emploi v2 » | Les identifiants sont fournis dès l'inscription |
| Authentification | OAuth2 (`client_id` / `client_secret` → token) | `app_id` / `app_key` passés directement dans chaque requête |
| Secrets GitHub | `FRANCETRAVAIL_CLIENT_ID`, `FRANCETRAVAIL_CLIENT_SECRET` | `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` |
| Recherche | `motsCles=stage informatique`, 50 offres | `what=stage informatique`, jusqu'à 100 offres (2 pages de 50) |
| Préfixe des identifiants | `ft_…` | `adz_…` |

Fichiers modifiés :
- `scripts/fetch_offers.py` : réécrit pour l'API Adzuna. Il produit toujours `data/offers/raw_offers.json`.
- `scripts/merge_offer_sources.py` : `normalize_adzuna()` remplace `normalize_france_travail()` et
  convertit les champs Adzuna vers le même schéma commun. Les scripts suivants
  (`extract_offers.py`, `match_offers.py`, `draft_cv.py`) n'ont pas changé.
- `.github/workflows/fetch_offers.yml` : il utilise les nouveaux secrets.

### Ce que ça implique

- **Descriptions tronquées.** Adzuna ne renvoie qu'un extrait d'environ 500 caractères par
  offre, contre plus de 4 000 caractères en moyenne pour Indeed. Sur le dernier run,
  l'extraction par IA n'a trouvé **aucune compétence pour 91 des 100 offres Adzuna**.
  Ces offres ont donc un score et une couverture de 0. Cela ne veut pas dire qu'elles
  correspondent mal au profil : on manque simplement d'information pour les évaluer.
- **Recherche moins précise.** La recherche par mots-clés d'Adzuna renvoie aussi des
  doublons (18 sur le dernier run) et des offres qui ne sont pas des stages : formations
  en alternance, CDI hors informatique…
- **Champs absents.** Adzuna n'indique ni l'alternance ni l'accessibilité aux personnes
  handicapées. `is_apprenticeship` est déduit du titre (« alternance », « apprenti ») et
  `accessible_disability` vaut toujours `false`.
- **Avantages.** Chaque offre a un lien (`url`) et une date de publication (`date_posted`),
  qui restaient vides avec France Travail.
- **Conditions d'utilisation.** Les offres peuvent être publiées sur le dashboard à
  condition de mentionner « Jobs by Adzuna » et de garder le lien vers chaque offre.
  L'offre gratuite limite aussi le nombre d'appels, d'où le maximum de 2 pages par run.

### Autre changement

ZipRecruiter a été retiré de `scripts/fetch_offers_jobspy.py`. Ce site ne couvre que les
États-Unis et le Canada, et répondait aux recherches en France par une redirection
(HTTP 307) sans aucun résultat.
