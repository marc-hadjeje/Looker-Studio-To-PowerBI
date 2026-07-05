# Looker Studio to Power BI Migration - Examples

Collection d'exemples démontrant les différentes façons de migrer depuis Looker Studio vers Power BI.

## 📚 Exemples Disponibles

### 1. Extraction manuelle (JSON)

**Fichier :** Télécharger manuellement depuis Looker Studio  
**Usage :**
```bash
# Ouvrir rapport dans Looker Studio
# Menu ☰ → Télécharger → JSON
# Sauvegarder: reports/my_report.json

python migrate.py reports/my_report.json
```

### 2. Extraction programmatique via API

**Fichier :** `full_migration_example.py`

#### Setup initial
```bash
# Setup authentification (une fois)
python examples/full_migration_example.py --auth
# → Choisir: Service Account ou OAuth
# → Fournir credentials
```

#### Lister les rapports
```bash
# Voir tous les rapports accessibles
python examples/full_migration_example.py --list

# Output:
# abc123def456
#   Title: Sales Dashboard 2024
#   Sources: 2, Pages: 5
#
# xyz789uvw123
#   Title: Marketing Report
#   Sources: 3, Pages: 3
```

#### Extraire un rapport
```bash
# Extraire rapport spécifique
python examples/full_migration_example.py --extract abc123def456

# Output:
# ✓ Report extracted and saved to: examples/exports/Sales_Dashboard_2024.json
```

#### Workflow complet
```bash
# Exécuter toute la pipeline
python examples/full_migration_example.py --full

# Steps:
# 1. Vérifier authentification
# 2. Lister les rapports
# 3. Extraire le premier
# 4. Générer projet Power BI
```

### 3. Batch migration

**Usage :**
```bash
# Lister ET exporter tous les rapports
python migrate.py --list-reports --batch --output-dir ./exports/

# Migrer tous les rapports exportés
python migrate.py --batch --input-dir ./exports/ --output-dir ./pbip_projects/

# Output:
# pbip_projects/
#   ├── SalesDashboard_pbip/
#   ├── Marketing_pbip/
#   └── Finance_pbip/
```

### 4. Extraction directe via ligne de commande

```bash
# Authentification
python migrate.py --auth service-account --credentials-file /path/to/sa.json

# Lister rapports
python migrate.py --list-reports

# Migrer un rapport
python migrate.py --report-id "abc123def456" --verbose

# Migrer tous
python migrate.py --list-reports --batch
```

### 5. Generation adaptee a tes tables BigQuery

Si tu veux des exemples qui collent a ton schema au lieu des dashboards generiques, utilise le mode adaptatif.

**Schema exemple :** `examples/bigquery_schema.example.json`

```bash
# Copier le schema exemple et le remplir avec tes vraies tables / colonnes
python examples/generate_sample_reports.py \
  --schema-file ./examples/bigquery_schema.example.json \
  --project-id "mon-projet-gcp" \
  --dataset-id "ma_base_par_defaut" \
  --output-dir ./looker_reports_adaptes/

# Puis migrer les JSON generes
python migrate.py --batch --input-dir ./looker_reports_adaptes/
```

Le script detecte automatiquement les tables de type sales, marketing, customer ou finance a partir des noms et des colonnes, puis cree un exemple Looker Studio adapte pour chacune.

---

## 🔧 Configuration Prérequis

### 1. Google Cloud Project

```bash
# Créer projet
https://console.cloud.google.com
→ New Project → "Looker-Migration"

# Activer APIs
https://console.cloud.google.com/apis/library
→ Enable:
  - Looker Studio Reporting API
  - Google Sheets API
  - BigQuery API

# Créer service account
APIs & Services → Credentials
→ Create Service Account → Download JSON key
→ Save as: .credentials/service-account.json

# Assigner roles IAM
IAM & Admin → Roles
→ Assign:
  - roles/bigquery.dataViewer
  - roles/sheets.viewer
```

### 2. Installer dépendances

```bash
# Toutes les dépendances Google
pip install -r requirements.txt

# Ou manuellement
pip install google-auth google-auth-oauthlib google-api-python-client
```

### 3. Donner accès aux rapports

Dans Looker Studio :
```
1. Ouvrir le rapport
2. Menu ☰ → Paramètres → Partager
3. Ajouter: [service-account-email@project.iam.gserviceaccount.com]
4. Permission: Viewer/Editor
```

---

## 📊 Exemple Complet Pas à Pas

### Scenario : Migrer 3 rapports Looker Studio

#### Étape 1 : Setup
```bash
# 1. Créer projet GCP + service account
# 2. Télécharger service-account.json
# 3. Partager rapports avec service account

# 4. Mettre à jour path
cp ~/Downloads/service-account.json .credentials/service-account.json
```

#### Étape 2 : Authentification
```bash
python migrate.py --auth service-account --credentials-file .credentials/service-account.json
# ✓ Service account authenticated
```

#### Étape 3 : Explorer
```bash
python examples/full_migration_example.py --list
# Affiche tous les rapports accessibles
```

#### Étape 4 : Migrer un rapport
```bash
python migrate.py --report-id "abc123def456"
# ✓ Report extracted
# ✓ Components transformed
# ✓ Power BI project generated
# Output: looker_migration_output/Sales_Dashboard_pbip/
```

#### Étape 5 : Ouvrir dans Power BI
```bash
# Double-click:
# looker_migration_output/Sales_Dashboard_pbip/

# Ou via Power BI Desktop:
# File → Open → looker_migration_output/Sales_Dashboard_pbip/
```

#### Étape 6 : Configurer connexions
```
Power BI Desktop:
1. Home → Get Data → BigQuery
   → Sign in with service account
   → Select dataset & tables

2. Home → Get Data → Web
   → Import Google Sheets
   → Or convert to Excel Online

3. Refresh data
   → Test connection
```

---

## 🔍 Debugging & Troubleshooting

### Logs détaillés
```bash
# Mode verbose pour debug
python migrate.py --report-id "abc123" --verbose
```

### Check auth
```bash
# Vérifier credentials
ls -la .credentials/
# → service-account.json OK?
# → oauth-token.pickle présent?
```

### Test connexion BigQuery
```bash
# Via Python
from google.cloud import bigquery
client = bigquery.Client(project="my-project")
print(list(client.list_datasets()))
```

### Test Google Sheets
```bash
# Vérifier feuille accessible
# URL: https://docs.google.com/spreadsheets/d/[SHEET_ID]/edit
# → Partage avec service account
```

---

## 📝 Sample JSON Structure (Exporté)

```json
{
  "id": "abc123def456",
  "title": "Sales Dashboard 2024",
  "dataSources": [
    {
      "id": "ds1",
      "sourceType": "BigQuery",
      "name": "Sales Data",
      "configuration": {
        "projectId": "my-gcp-project",
        "datasetId": "sales_analytics",
        "query": "SELECT * FROM sales WHERE date > @start_date"
      }
    },
    {
      "id": "ds2",
      "sourceType": "GoogleSheets",
      "configuration": {
        "spreadsheetId": "1abc...",
        "worksheetName": "Targets"
      }
    }
  ],
  "pages": [...],
  "parameterControls": [...]
}
```

---

## 🎯 Recommandations

| Scenario | Recommandation |
|----------|----------------|
| **1 rapport** | Export JSON manual + `python migrate.py report.json` |
| **Plusieurs rapports** | `python migrate.py --batch --input-dir reports/` |
| **Automation** | `python migrate.py --report-id "id" --deploy WORKSPACE_ID` |
| **CI/CD** | GitHub Actions + service account (voir API_EXTRACTION_GUIDE.md) |
| **Production** | Batch extraction nightly + deploy to Fabric |

---

## 📚 Ressources

- [API_EXTRACTION_GUIDE.md](../docs/API_EXTRACTION_GUIDE.md) - Guide détaillé des APIs
- [LOOKER_EXTRACTION_GUIDE.md](../docs/LOOKER_EXTRACTION_GUIDE.md) - Extraction Looker Studio
- [README.md](../README.md) - Documentation principale
