# smart-internship-match

Lien vers le Dashboard : https://bourdas-rougeault-gaspard-bi-2026.github.io/smart-internship-match/

## Compte rendu du TP

Ce dépôt contient un pipeline de recherche de stage en six étapes : collecte des offres,
structuration par IA, calcul d'un score de correspondance avec mon profil, rédaction
assistée d'accroches de lettres de motivation, tableau de bord et suivi des candidatures.
Cette section décrit les choix faits à chaque étape et les écarts avec le manuel.

### 1. Mise en place

- Dépôt **public**, pour pouvoir publier le dashboard avec GitHub Pages (dossier `docs/`
  de la branche `main`). Les workflows ont les droits en écriture sur le dépôt.
- Profil de compétences dans `data/profile/my_skills.csv` : 25 compétences notées de 1 à 5,
  chacune avec une preuve concrète (cours, projet).
- **Choix de confidentialité** (étape 5) : le profil est publié, mais il ne contient que des
  informations que je mettrais sur un CV. Les brouillons de lettres, les offres issues du
  scraping et les fichiers intermédiaires ne sont jamais versionnés (voir `.gitignore`).
- Les traitements par IA tournent en local avec **Ollama** et le modèle `qwen3:8b` : aucune
  offre ni donnée de profil n'est envoyée à un service externe.

### 2. Collecte des offres

**Adzuna au lieu de France Travail.** À la demande de l'enseignant, l'API France Travail
prévue par le manuel a été remplacée par l'API Adzuna
([developer.adzuna.com](https://developer.adzuna.com)).

| | France Travail (manuel) | Adzuna (ce dépôt) |
|---|---|---|
| Authentification | OAuth2 (`client_id` / `client_secret` → token) | `app_id` / `app_key` passés dans chaque requête |
| Secrets GitHub | `FRANCETRAVAIL_CLIENT_ID`, `FRANCETRAVAIL_CLIENT_SECRET` | `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` |
| Recherche | `motsCles=stage informatique`, 50 offres | `what=stage informatique`, jusqu'à 100 offres (2 pages de 50) |
| Préfixe des identifiants | `ft_…` | `adz_…` |

- `scripts/fetch_offers.py` a été réécrit pour Adzuna et produit toujours
  `data/offers/raw_offers.json`.
- Les identifiants sont stockés dans les **secrets GitHub**, jamais dans le code.
- Le workflow `.github/workflows/fetch_offers.yml` lance la collecte **chaque lundi à 7 h**
  (ou à la main) et committe le résultat.

**Seconde source, locale : Indeed via jobspy** (`scripts/fetch_offers_jobspy.py`). Le
script récupère 30 offres « stage informatique » en France publiées dans les 14 derniers
jours. Il tourne uniquement en local et à la demande, car le scraping va contre les
conditions d'utilisation des plateformes. ZipRecruiter a été retiré : ce site ne couvre
que les États-Unis et le Canada, et répondait aux recherches en France par une
redirection (HTTP 307) sans résultat.

**Fusion** (`scripts/merge_offer_sources.py`). Les deux sources sont converties vers un
schéma commun. `normalize_adzuna()` remplace `normalize_france_travail()`. Chaque offre
porte un champ `publishable` : `true` pour Adzuna, `false` pour jobspy.

### 3. Structuration par IA

`scripts/extract_offers.py` envoie la description de chaque offre à `qwen3:8b` et
récupère en JSON les compétences techniques demandées, les missions, l'expérience exigée
et la rémunération. Le prompt interdit de déduire l'expérience du titre (« Senior »…) et
demande de citer la rémunération mot pour mot, pour limiter les inventions du modèle.

### 4. KPI de correspondance

C'est `score_offer()` dans `scripts/match_offers.py`. Choix retenus :

1. **Comparaison normalisée** : minuscules, sans accents ni ponctuation, en gardant `#`,
   `+` et `.` (pour `C#`, `C++`, `.NET`). L'IA renvoie la même compétence avec des
   écritures différentes (« Computer vision » / « computer vision »).
2. **Table d'alias explicite plutôt que recherche de sous-chaîne** : « Anglais » =
   « English », « Postgres » = « PostgreSQL »… Une recherche de sous-chaîne ferait
   correspondre « C » à « C++ », « Java » à « JavaScript » ou « SQL » à « NoSQL ».
3. **Score pondéré par le niveau** :
   `score = somme(niveau / 5 des compétences possédées) / (nb compétences demandées + 2)`.
4. **Pénalité pour petit échantillon** (le `+ 2`) : une offre dont on n'a extrait qu'une
   compétence, que je possède, ne doit pas passer devant une offre où j'en possède 6 sur 8.
5. **Couverture** = part simple des compétences demandées que je possède. C'est elle que
   `draft_cv.py` filtre.
6. Une offre sans compétence extraite a un score et une couverture de **0** : rien ne
   montre qu'elle correspond.

Le script écrit deux fichiers : `data/offers/matches_all_local.json` (toutes les sources,
local uniquement) et `docs/data/matches.json` (offres publiables seulement, affichées sur
le dashboard). Il recopie aussi le lien et la date de publication de chaque offre, que le
dashboard affiche.

### 5. Rédaction assistée

`scripts/draft_cv.py` rédige avec `qwen3:8b` le paragraphe d'accroche d'une lettre de
motivation pour les **3 meilleures offres ayant au moins 30 % de couverture**. Le prompt ne
transmet que les compétences réellement en commun et leurs preuves, et interdit d'inventer
une expérience. Les brouillons sont écrits dans `output/cv_drafts/`, qui n'est pas
versionné. Je les relis et les corrige avant tout usage.

### 6. Dashboard

`docs/index.html`, publié sur GitHub Pages. Chaque bloc indique à quoi il sert :

- **Mes critères** (ajouté après le retour de l'enseignant) : des filtres qui entrent dans
  le calcul du score, pas seulement dans l'affichage.
  - **Lieu** : on ajoute autant de villes, départements ou régions que voulu, chacun
    *prioritaire* ou *exclu* (ex. : Le Mans et Nantes prioritaires, Île-de-France exclue).
    Le niveau le plus précis l'emporte : exclure une région mais prioriser une de ses villes
    garde cette ville.
  - **Type d'offre** (Stage, Alternance, CDI, CDD, Non précisé) : priorité, neutre ou
    exclusion pour chacun. Par défaut, alternance, CDI et CDD sont exclus.
  - **Métier** : Développement, Data / IA, DevOps / Cloud / Systèmes, Réseaux /
    Cybersécurité, Informatique industrielle / Embarqué, Test / Qualité, Support /
    Technicien, Gestion de projet / Business, Autre (informatique), Hors informatique.
    Famille déduite du titre (motifs vérifiés sur les titres réels collectés). Une offre
    peut avoir plusieurs familles (« Chef de projet BI » = gestion de projet + data) : elle
    est prioritaire si une de ses familles l'est, exclue seulement si toutes le sont.
    « Hors informatique » (juriste, recrutement, secrétariat… que ramène la recherche
    Adzuna) est exclu par défaut.
  - Pour chaque critère, une option « seulement mes priorités » exclut tout le reste.
  - **Score ajusté** = score compétences × (1 + bonus × nombre de critères prioritaires
    remplis parmi lieu, type et métier), avec un bonus réglable (50 % par défaut). Le multiplicateur est affiché sous
    chaque score. Les critères ne remplacent pas les compétences : une offre à 0 reste à 0.
  - Les offres exclues sortent du classement, du compteur principal et des graphiques
    d'efficacité, qui sont recalculés sur les offres retenues. Elles restent visibles
    (grisées, avec la raison) si on coche « afficher les offres exclues ».
  - Les critères sont gardés dans le navigateur (`localStorage`).
  - Région, département, ville, type et métier sont calculés par `scripts/offer_attributes.py`,
    appelé par `merge_offer_sources.py` (à partir du champ `location.area` d'Adzuna, le plus
    fiable) et, en secours, par `match_offers.py` (à partir du texte du lieu et du titre).
    Le type et le métier sont lus dans le titre, car Adzuna n'a pas de type « stage » et
    sa description est tronquée.
- **Où postuler en premier** : tableau des offres trié par score ajusté, avec la
  couverture, les compétences que j'ai et celles qui manquent, et le lien vers l'offre.
  Recherche texte, filtre « seulement les offres évaluables » et filtre qui masque les
  doublons.
- **Efficacité de la recherche** : compétences manquantes les plus demandées (quoi
  apprendre), mes compétences les plus demandées avec mon niveau (quoi mettre en avant
  dans le CV), répartition des scores (la recherche ramène-t-elle des offres adaptées ou
  du bruit ?).
- **Santé du pipeline** : offres collectées, taux d'extraction de compétences, doublons,
  offres qui ne sont pas des stages, rémunération mentionnée, âge des données.
- **Suivi des candidatures** : candidatures envoyées, taux de réponse, entretiens et
  entonnoir. Les données sont saisies à la main dans `docs/data/applications.csv`.

**Contrôle de suivi** : le dashboard signale les candidatures **sans réponse depuis plus
de 10 jours**, avec le message « Relancer ». Il signale aussi des données trop anciennes
(le workflow tourne chaque lundi).

La mention « Jobs by Adzuna » et le lien vers chaque offre sont affichés, comme l'exigent
les conditions d'utilisation d'Adzuna.

### Résultats et limites

Sur le dernier run local : 118 offres (100 Adzuna, 18 Indeed).

- **Descriptions Adzuna tronquées.** Adzuna ne renvoie qu'un extrait d'environ 500
  caractères par offre, contre plus de 4 000 en moyenne pour Indeed. L'extraction n'a
  trouvé **aucune compétence pour 98 des 100 offres Adzuna**, qui ont donc un score de 0.
  Ce n'est pas un mauvais match : on manque d'information pour les évaluer. Comme seules
  les offres Adzuna sont publiables, le dashboard public classe surtout des offres non
  évaluables. Les offres Indeed, complètes, donnent un classement plus utile, mais
  restent en local.
- **Recherche peu précise.** La recherche Adzuna renvoie des doublons et des offres qui ne
  sont pas des stages (alternance, CDI hors informatique). Le dashboard les compte et
  permet de les masquer.
- **Champs absents.** Adzuna n'indique ni l'alternance ni l'accessibilité aux personnes
  handicapées : `is_apprenticeship` est déduit du titre et `accessible_disability` vaut
  toujours `false`.
- **Rémunération rarement indiquée** : 10 offres sur 118. Elle est affichée comme un
  simple compteur, pas comme un graphique.
- **Quota de l'offre gratuite Adzuna** : d'où le maximum de 2 pages par run.
- Sur l'ensemble des offres, les compétences les plus demandées que je n'ai pas sont
  **Excel, React, Power BI et .NET**. Mes compétences les plus demandées sont **Python,
  Git et SQL**.
