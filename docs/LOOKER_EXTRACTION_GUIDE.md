# Processus de Récupération des Sources Looker Studio

Il existe plusieurs façons de récupérer les données depuis Looker Studio pour la migration vers Power BI.

## 1️⃣ Option A : Export JSON (Recommandé pour commencer)

### Via l'interface Looker Studio
```
1. Ouvrir le rapport dans Looker Studio
2. Menu ☰ → "Télécharger le rapport"
3. Format : JSON
4. Fichier téléchargé = structure complète du rapport
```

**Avantages :**
- Simple, pas d'authentification complexe
- Récupère structure complète (datasources, filtres, visuals)
- Pas besoin de clé API

**Limitations :**
- Export manuel (pas d'automatisation)
- Données de visualisation non incluses

**Fichier JSON contient :**
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
  "pages": [...],
  "parameterControls": [...]
}
```

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
# Option 1: Depuis JSON exporté
python migrate.py rapport_export.json

# Option 2: Depuis Looker Studio (avec auth)
python migrate.py --report-id "abc123" --auth

# Option 3: Batch - récupérer plusieurs rapports
python migrate.py --batch --input-dir ./looker_exports/ --output-dir ./pbip_projects/

# Option 4: Assessment seulement (validation)
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
# Export manuel du rapport Looker Studio en JSON
# Sauvegarder dans: examples/looker_reports/

mkdir -p examples/looker_reports/
# Télécharger rapport JSON depuis Looker Studio
# → my_report.json
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

