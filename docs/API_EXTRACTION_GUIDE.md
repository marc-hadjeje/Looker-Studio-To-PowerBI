# Extraction Programmatique via Google API

Guide d'utilisation pour extraire automatiquement les rapports Looker Studio, BigQuery et Google Sheets.

## 🔧 Prérequis

### Installation des dépendances Google
```bash
pip install google-auth google-auth-oauthlib google-api-python-client
```

### Setup du projet GCP

1. **Créer un projet Google Cloud**
```
https://console.cloud.google.com
→ Créer un nouveau projet
→ Nom: "Looker-Studio-Migration"
```

2. **Activer les APIs requises**
```
Google Cloud Console → APIs & Services → Library
→ Chercher et activer:
  ✓ Looker Studio Reporting API
  ✓ Google Sheets API
  ✓ BigQuery API
```

3. **Créer les credentials**
```
APIs & Services → Credentials
→ Create Credentials → Service Account

Remplir les infos:
  - Service account name: looker-migration
  - Grant roles: 
    ✓ BigQuery Data Viewer
    ✓ Sheets Viewer
    ✓ Looker Studio Report Viewer (si disponible)

Télécharger la clé JSON:
  → Rename: service-account.json
  → Sauvegarder: .credentials/service-account.json
```

---

## 📝 Utilisation

### 1️⃣ Configuration Authentification (Une fois)

**Option A : Authentification interactive**
```bash
python migrate.py --auth
# Menu interactif pour choisir Service Account ou OAuth
```

**Option B : Avec fichier service account**
```bash
python migrate.py --auth service-account --credentials-file /path/to/service-account.json
```

**Option C : OAuth 2.0**
```bash
python migrate.py --auth oauth
# Ouvre navigateur pour consentement utilisateur
```

Après setup, credentials sauvegardés dans `.credentials/`

---

### 2️⃣ Lister les Rapports Accessibles

```bash
python migrate.py --list-reports

# Output:
# ✓ Found 3 reports:
#
#   abc123def456
#     Title: Sales Dashboard 2024
#     Sources: 2, Pages: 5
#
#   xyz789uvw123
#     Title: Marketing KPIs
#     Sources: 3, Pages: 3
```

---

### 3️⃣ Migrer Directement depuis Looker Studio (API)

```bash
# Récupérer report ID depuis URL
# https://datastudio.google.com/reporting/abc123def456/page/page1
#                                       ^ report ID

python migrate.py --report-id "abc123def456"

# Workflow:
# 1. Extrait rapport via API Looker Studio
# 2. Sauvegarde JSON dans: looker_migration_output/exports/
# 3. Génère projet .pbip automatiquement
# 4. Output: looker_migration_output/SalesDashboard2024_pbip/
```

---

### 4️⃣ Batch Migration (Tous les Rapports Accessibles)

```bash
# 1. Lister et exporter tous les rapports
python migrate.py --list-reports --batch

# 2. Migrer tous les rapports exportés
python migrate.py --batch --input-dir looker_migration_output/exports/

# Cela génère:
# looker_migration_output/
#   ├── Report1_pbip/
#   ├── Report2_pbip/
#   └── Report3_pbip/
```

---

## 🔑 Workflow Complet (Exemple Réel)

### Étape 1 : Setup initial
```bash
# Setup authentification (une fois)
python migrate.py --auth
# → Choisir: 1. Service Account
# → Fournir chemin: .credentials/service-account.json
```

### Étape 2 : Explorer rapports
```bash
# Voir quels rapports sont accessibles
python migrate.py --list-reports

# Output:
# abc123def456 - Sales Dashboard
# xyz789uvw123 - Marketing Report
```

### Étape 3 : Migrer un rapport
```bash
# Migrer "Sales Dashboard"
python migrate.py --report-id "abc123def456" --verbose

# Génère:
# ✓ Extraction: BigQuery queries + Google Sheets
# ✓ Transformation: Formules Looker → DAX
# ✓ Generation: Power BI .pbip project
# ✓ Output: looker_migration_output/SalesDashboard_pbip/
```

### Étape 4 : Ouvrir dans Power BI
```bash
# Double-click le dossier:
# looker_migration_output/SalesDashboard_pbip/

# Ou via Power BI Desktop:
# File → Open → looker_migration_output/SalesDashboard_pbip/
```

### Étape 5 : Configurer connexions
Dans Power BI Desktop:
1. **BigQuery** : Configure credentials dans "Get Data"
2. **Google Sheets** : Convert to Excel Online ou import
3. **Refresh** : Test that data loads

---

## 🔒 Gestion des Credentials

### Localisation
```
.credentials/
├── service-account.json      # Service Account credentials
├── oauth-token.pickle        # OAuth token (cached)
└── oauth-credentials.json    # OAuth config
```

### Sécurité
```bash
# Ne pas committer les credentials!
echo ".credentials/" >> .gitignore

# Ou pour fichiers spécifiques
echo ".credentials/*.json" >> .gitignore
echo ".credentials/*.pickle" >> .gitignore
```

### Rotation des Credentials
```bash
# Créer nouvelle clé service account dans GCP Console
# Puis:
python migrate.py --auth service-account --credentials-file /new/service-account.json

# Ou supprimer et reconfigurer:
rm -rf .credentials/
python migrate.py --auth
```

---

## 🔗 Intégration CI/CD

### GitHub Actions
```yaml
name: Looker Migration

on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly

jobs:
  migrate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
      
      - name: Setup GCP credentials
        env:
          GCP_SA_KEY: ${{ secrets.GCP_SERVICE_ACCOUNT }}
        run: |
          mkdir -p .credentials
          echo "$GCP_SA_KEY" > .credentials/service-account.json
      
      - name: Migrate all reports
        run: |
          python migrate.py --list-reports
          python migrate.py --batch --input-dir ./exports/
      
      - name: Upload artifacts
        uses: actions/upload-artifact@v2
        with:
          name: pbip-projects
          path: looker_migration_output/*_pbip/
```

---

## 🐛 Troubleshooting

| Problème | Solution |
|----------|----------|
| `Auth failed: No auth configured` | Exécuter: `python migrate.py --auth` |
| `Permission denied` | Vérifier roles IAM dans Google Cloud Console |
| `Report not found` | Vérifier report ID dans URL Looker Studio |
| `BigQuery query fails` | Vérifier dataset/project dans configuration |
| `Sheets not accessible` | Partager feuille avec service account email |
| `Token expired` | Script reconfigure automatiquement via refresh token |

---

## 📚 Références

- [Google Cloud Service Account](https://cloud.google.com/iam/docs/creating-managing-service-accounts)
- [Looker Studio Sharing & Access](https://support.google.com/datastudio/answer/9012577)
- [BigQuery API Client Libraries](https://cloud.google.com/bigquery/docs/reference/libraries)
- [Google Sheets API Guide](https://developers.google.com/sheets/api/guides/concepts)
