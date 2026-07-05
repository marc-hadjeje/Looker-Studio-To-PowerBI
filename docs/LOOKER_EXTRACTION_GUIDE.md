# Processus de Récupération des Sources Looker Studio

Il existe plusieurs façons d'alimenter la migration vers Power BI.

> [!IMPORTANT]
> **Looker Studio n'offre AUCUN export natif de la définition d'un rapport en JSON.**
> Le menu Looker Studio permet d'exporter un rapport en **PDF**, ou les **données** d'un
> graphe en CSV/Google Sheets — mais **jamais** la structure du rapport (pages, visuals,
> formules) sous forme de fichier. Il n'existe pas non plus d'API publique Google qui
> retourne cette définition. Toute affirmation contraire (ancienne version de ce guide
> incluse) est **fausse**.

## 🧩 Le format JSON de ce dépôt est un format d'ENTRÉE maison

Le schéma `{ id, title, dataSources[], pages[], visuals[], parameterControls[] }` utilisé
par `migrate.py` et par les exemples (`looker_reports_*/*.json`) est un **format d'entrée
défini par ce projet**. Ce n'est **pas** le JSON interne réel de Looker Studio. Les fichiers
d'exemple sont **générés synthétiquement** par `examples/generate_sample_reports.py` à
partir d'un schéma BigQuery (le champ `generatedFromTableSchema` dans ces fichiers en est
la preuve).

> [!NOTE]
> **Ces JSON sont des échantillons.** Ils ne "sortent" pas de Looker Studio : ce sont des
> exemples qui **respectent le contrat d'entrée** attendu par l'outil, et qui suffisent
> donc à faire tourner la moulinette de migration (`migrate.py`) jusqu'à produire un
> projet Power BI (`.pbip`). Autrement dit, tant qu'un fichier respecte cette structure
> — peu importe qu'il vienne d'un screenshot + scan BigQuery, d'une saisie manuelle ou
> d'une capture Network — la moulinette sait le convertir. L'échantillon sert de
> **preuve de fonctionnement** et de **gabarit** à reproduire.

Structure attendue en entrée par l'outil :

```json
{
  "id": "report_id",
  "title": "My Report",
  "dataSources": [
    {
      "id": "ds1",
      "sourceType": "BigQuery",
      "name": "Sales Data",
      "configuration": {
        "projectId": "my-gcp-project",
        "datasetId": "analytics",
        "query": "SELECT * FROM sales"
      }
    },
    {
      "id": "ds2",
      "sourceType": "GoogleSheets",
      "configuration": {
        "spreadsheetId": "1abc...",
        "worksheetName": "Sheet1"
      }
    }
  ],
  "pages": [],
  "parameterControls": []
}
```

## 🎯 Les 3 approches réelles pour reconstruire un rapport

> [!TIP]
> **En amont — inventorier tous vos rapports (étape 0).** Avant d'extraire, cataloguez ce
> que vous avez à migrer. Le script console communautaire
> [digilytiks/looker-studio-report-exporter](https://github.com/digilytiks/looker-studio-report-exporter)
> scrolle la page d'accueil Looker Studio et copie **la liste de tous vos rapports**
> (nom, URL, propriétaire, date de dernière modification) au format **CSV** (à coller
> dans Google Sheets / Excel). Ouvrez Looker Studio connecté → console DevTools
> (`Ctrl+Shift+J` / `Cmd+Option+J`) → collez le script → Entrée. ⚠️ Il récupère
> uniquement les **métadonnées et URLs** des rapports (pas leur structure) : c'est le
> point de départ idéal pour ensuite appliquer l'une des 3 approches ci-dessous, rapport
> par rapport.

1. **Screenshot + scan BigQuery** — capturer le rapport, scanner le schéma des sources
   BigQuery (auxquelles vous avez accès via l'API), puis reconstruire le modèle et le
   rapport Power BI. C'est le pipeline `generate_sample_reports.py --screenshot-file` +
   `migrate.py`.
2. **Format d'entrée maison** — écrire/compléter à la main le JSON au format ci-dessus,
   puis `python migrate.py mon_rapport.json`.
3. **Capture Network (DevTools)** — ouvrir le rapport, `F12` → onglet **Network** →
   filtrer **Fetch/XHR** → recharger la page → repérer la requête qui contient la
   définition du rapport → **Copy → Copy response**. C'est le seul moyen de voir le
   *vrai* JSON interne de Looker Studio (structure non documentée et bien plus complexe
   que le format maison).

> [!NOTE]
> **Variante : export CSV par table via Selenium.** Le projet communautaire
> [woskam/looker-studio-automation](https://github.com/woskam/looker-studio-automation)
> pilote Chrome avec Selenium pour ouvrir le menu 3-points d'une table Looker Studio et
> télécharger son **CSV** (login via copie des cookies Chrome, GUI obligatoire car Google
> bloque le headless). ⚠️ Cette technique récupère **les données d'une table, PAS la
> structure du rapport** (pages, visuels, formules, mise en page). Elle peut compléter
> l'approche 1 pour quelqu'un **sans accès direct BigQuery** ; si vous avez l'accès
> BigQuery, le scan direct reste plus fiable (ni scraping, ni cookies, ni anti-bot).

---

## 2️⃣ Option B : Google Looker Studio Reporting API

### Setup

#### 1. Créer un projet GCP
```bash
# Goto https://console.cloud.google.com
# Créer un nouveau projet
# Nom: "Looker-Studio-Migration"
```

#### 2. Activer les APIs
```bash
# Dans Google Cloud Console:
# - Activer "Looker Studio Reporting API"
# - Activer "Google Sheets API"
# - Activer "BigQuery API"
```

#### 3. Créer des credentials
```bash
# Type: Service Account
# Télécharger la clé JSON
# Sauvegarder: looker-studio-sa.json
```

#### 4. Donner accès au rapport
```
# Dans Looker Studio:
1. Ouvrir le rapport
2. Partager → Ajouter l'email du service account
3. Permission: Viewer/Editor
```

### Code Python pour récupérer via API

```python
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import requests

# Authentification
credentials = service_account.Credentials.from_service_account_file(
    'looker-studio-sa.json',
    scopes=['https://www.googleapis.com/auth/datastudio']
)

# Refresh token si nécessaire
credentials.refresh(Request())

# Récupérer le rapport
REPORT_ID = "your-report-id"  # Depuis l'URL du rapport
url = f"https://datastudio.google.com/api/reports/{REPORT_ID}"

headers = {
    'Authorization': f'Bearer {credentials.token}',
    'Content-Type': 'application/json'
}

response = requests.get(url, headers=headers)
report_data = response.json()

print(report_data)
```

**Avantages :**
- Accès programmatique
- Possible automatiser batch
- Récupère données actualisées

**Limitations :**
- API limitée (pas tous les détails exposés)
- Quota limité
- Configuration complexe

---

## 3️⃣ Option C : Récupérer Directement les Sources (Recommandé pour production)

Au lieu de passer par Looker Studio, récupérer les données directement depuis :

### A. BigQuery
```python
from google.cloud import bigquery

client = bigquery.Client(project="my-project")

# Lister les datasets
datasets = list(client.list_datasets())
for ds in datasets:
    print(f"Dataset: {ds.dataset_id}")
    
    # Lister les tables
    tables = list(client.list_tables(ds.dataset_id))
    for table in tables:
        print(f"  - Table: {table.table_id}")
        
        # Récupérer le schéma
        table_ref = client.get_table(f"{ds.dataset_id}.{table.table_id}")
        print(f"    Columns: {[f.name for f in table_ref.schema]}")

# Exécuter une requête BigQuery
query = "SELECT * FROM `my-project.dataset.table` LIMIT 10"
results = client.query(query)
for row in results:
    print(row)
```

### B. Google Sheets
```python
from google.auth.transport.requests import Request
from google.oauth2.service_account import Credentials
import requests

credentials = service_account.Credentials.from_service_account_file(
    'sheets-sa.json',
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)

SPREADSHEET_ID = "1abc..."
SHEET_NAME = "Sales"

# Récupérer les données
url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}/values/{SHEET_NAME}"

headers = {
    'Authorization': f'Bearer {credentials.token}'
}

response = requests.get(url, headers=headers)
data = response.json()

print(data['values'])  # Toutes les lignes
```

**Avantages :**
- Récupère données actuelles (pas juste structure)
- Indépendant de Looker Studio
- Utile pour validation + preview

---

## 4️⃣ Implémentation dans le Script migrate.py

```bash
# Option 1: Depuis un JSON au format d'entrée maison
python migrate.py rapport_export.json

# Option 2: Batch - migrer plusieurs rapports
python migrate.py --batch --input-dir ./looker_exports/ --output-dir ./pbip_projects/

# Option 3: Assessment seulement (validation)
python migrate.py rapport_export.json --assess --verbose
```

---

## 📋 Checklist de Configuration

### Pour BigQuery
- [ ] Projet GCP créé
- [ ] BigQuery API activée
- [ ] Service account créé et clé JSON téléchargée
- [ ] Permissions IAM: `roles/bigquery.dataViewer`
- [ ] Tester connexion: `bq ls --project_id=my-project`

### Pour Google Sheets
- [ ] Google Sheets API activée
- [ ] Service account a accès aux feuilles (partagées)
- [ ] Spreadsheet IDs collectés

### Pour Looker Studio API
- [ ] Looker Studio Reporting API activée
- [ ] Report IDs collectés
- [ ] Service account a permission "Viewer" sur rapports

---

## 🚀 Recommandation pour Votre Setup

Vu que vous avez **BigQuery + Google Sheets** comme sources :

**Étape 1 - Récupération (QUICKSTART)**
```bash
# Looker Studio n'exporte PAS la définition d'un rapport en JSON.
# Utilisez l'une des 3 approches réelles (voir le haut de ce guide) :
#   1. Screenshot + scan BigQuery  → examples/generate_sample_reports.py
#   2. Écrire le JSON au format d'entrée maison
#   3. Capture Network via DevTools (Copy → Copy response)

mkdir -p examples/looker_reports/
# Sauvegarder le JSON obtenu dans : examples/looker_reports/my_report.json
```

**Étape 2 - Migration**
```bash
python migrate.py examples/looker_reports/my_report.json --output-dir ./migrations/
```

**Étape 3 - Ouvrir dans Power BI**
```bash
# Fichier généré:
# ./migrations/my_report_pbip/

# Double-cliquer le dossier ou:
# Power BI Desktop → Open → migrations/my_report_pbip/
```

**Étape 4 - Configuration connexions Power BI**
```
1. BigQuery: Configure credentials dans Power BI
2. Google Sheets: Basculer vers Excel Online
3. Tester refresh des données
```

## Adapter les exemples a vos tables BigQuery

Si vous voulez des rapports Looker Studio d'exemple qui suivent votre schema BigQuery, utilisez le mode adaptatif.

```bash
# 1. Copier et remplir le schema exemple avec vos tables / colonnes
python examples/generate_sample_reports.py \
  --schema-file ./examples/bigquery_schema.example.json \
  --project-id "mon-projet-gcp" \
  --dataset-id "ma_base" \
  --output-dir ./looker_reports_adaptes/

# 2. Migrer les JSON generes vers Power BI
python migrate.py --batch --input-dir ./looker_reports_adaptes/
```

Le generateur adapte automatiquement les profils de pages selon les noms de tables et de colonnes. Par exemple, une table contenant `order`, `revenue` ou `campaign` sera mappee vers une mise en page sales ou marketing plus pertinente.

---

## Troubleshooting

| Problème | Solution |
|----------|----------|
| JSON invalide | Vérifier export depuis Looker Studio v2+ |
| BigQuery requête échoue | Vérifier syntaxe, convertir de BigQuery SQL à T-SQL |
| Google Sheets non trouvée | Vérifier ID feuille, permissions partage |
| Formules Looker inconnues | Consulter [LOOKER_TO_DAX_REFERENCE.md](./docs/LOOKER_TO_DAX_REFERENCE.md) |

