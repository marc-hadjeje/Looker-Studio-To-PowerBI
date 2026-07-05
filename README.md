<p align="center">
  <img src="https://img.shields.io/badge/Looker%20Studio-4285F4?style=for-the-badge&logo=google&logoColor=white" alt="Looker Studio"/>
  <img src="https://img.shields.io/badge/%E2%86%92-gray?style=for-the-badge" alt="arrow"/>
  <img src="https://img.shields.io/badge/Power%20BI-F2C811?style=for-the-badge&logo=powerbi&logoColor=black" alt="Power BI"/>
</p>

<h1 align="center">Looker Studio to Power BI Migration</h1>

<p align="center">
  <strong>Migrate your Looker Studio reports to Power BI in seconds — fully automated, zero manual rework.</strong>
</p>

<p align="center">
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-key-features">Features</a> •
  <a href="#-how-it-works">How It Works</a> •
  <a href="#-supported-sources">Data Sources</a> •
  <a href="#-deployment">Deployment</a> •
  <a href="#-documentation">Docs</a>
</p>

---

## ⚡ Quick Start

The engine always consumes the **same input contract**: a JSON file following this
project's schema (`{ id, title, dataSources[], pages[], visuals[], parameterControls[] }`).
Once you have such a file, migration is one command:

```bash
python migrate.py report.json
```

> [!IMPORTANT]
> **Looker Studio has no native JSON export and no public API that returns a report
> definition.** The internal `datastudio.google.com/api` endpoint returns an HTML login
> page, not JSON — so any "live extraction by report ID" is not reliable. To feed the
> engine, use one of the **3 real extraction approaches** below.

### 3 ways to obtain the input JSON

**1️⃣ Screenshot + BigQuery scan (recommended)**
Capture the Looker report, scan the BigQuery source schema you already have access to,
then let the tooling rebuild the model and report from scratch.
```bash
python examples/generate_sample_reports.py \
  --schema-file examples/bigquery_schema.generated.json \
  --screenshot-file report.png --layout-mode auto \
  --output-dir looker_reports_auto
python migrate.py looker_reports_auto/<report>.json
```

**2️⃣ Hand-written input JSON (or a bundled sample)**
The `looker_reports_*/*.json` files are **samples** that follow the input contract. Copy
one as a template, adjust data sources / visuals, then migrate.
```bash
python migrate.py looker_reports_retail_star/retail_exec_dashboard.json
```

**3️⃣ DevTools Network capture**
Open the report → `F12` → **Network** → filter **Fetch/XHR** → reload → find the request
carrying the report definition → **Copy → Copy response** → save as `report.json`, then
`python migrate.py report.json`. This is the only way to see Looker Studio's *real*
internal JSON (undocumented, more complex than the home-made format).

> [!NOTE]
> See [docs/LOOKER_EXTRACTION_GUIDE.md](docs/LOOKER_EXTRACTION_GUIDE.md) for the full
> details of these 3 approaches.

> [!TIP]
> The output is a `.pbip` project — just double-click to open in **Power BI Desktop** (December 2025+).

<details>
<summary><b>📦 Installation</b></summary>

```bash
git clone https://github.com/your-org/Looker-Studio-To-PowerBI.git
cd Looker-Studio-To-PowerBI
python migrate.py --report-id "report_id"
```

**Requirements:** Python 3.9+ • No `pip install` needed — pure standard library.

Optional (for Google Sheets, Analytics, or deployment):
```bash
pip install google-api-python-client google-auth-oauthlib azure-identity requests
```
</details>

---

## ✨ Key Features

| Feature | Status | Notes |
|---------|--------|-------|
| **Report & Dashboard Import** | ✅ | Parse Looker Studio JSON schema |
| **Data Source Mapping** | ✅ | Google Sheets, BigQuery, GA4, Analytics, YouTube |
| **Control Conversion** | ✅ | Date, text, dropdown filters → Power Query parameters |
| **Chart/Visual Generation** | ✅ | Scorecards, tables, time series, geo maps |
| **Formula Conversion** | ✅ | Looker formulas → DAX (180+ mappings) |
| **Interactive Filters** | ✅ | Cross-report filtering, date range pickers |
| **Deployment** | ✅ | Deploy to Power BI Service directly |
| **Batch Migration** | ✅ | Migrate entire report collections |
| **Assessment Mode** | ✅ | Pre-migration readiness analysis |
| **Fabric Output** | ✅ | Generate Lakehouse + DirectLake models |
| **Custom Themes** | ✅ | Brand color mapping (Looker → Power BI) |

---

## 📋 More Migration Options

```bash
# 📁 Batch — migrate multiple reports
python migrate.py --batch --input-dir reports/ --output-dir /tmp/output

# 🔍 Pre-migration assessment
python migrate.py --report-id "report_id" --assess

# 🚀 Migrate + deploy to Power BI Service
python migrate.py --report-id "report_id" --deploy WORKSPACE_ID

# 🧙 Interactive wizard (guided step-by-step)
python migrate.py --wizard

# 🏭 Fabric-native output (Lakehouse + Dataflow + DirectLake)
python migrate.py report.json --output-format fabric

# ⚡ Optimize DAX + auto-inject Time Intelligence
python migrate.py report.json --optimize-dax --time-intelligence auto

# 🌐 Map data sources to custom Power BI connections
python migrate.py report.json --datasource-config config.json

# 📊 Generate migration assessment report
python migrate.py --batch --input-dir reports/ --global-assess
```

---

## 🏗️ How It Works

### 1️⃣ Extract
- Provide a report as a JSON input file (this project's input schema) or scan BigQuery sources directly
- Retrieve Looker Studio report schema & data sources
- Parse embedded queries, formulas, controls

### 2️⃣ Transform
- Map Looker data sources to Power BI connections
- Convert Looker formulas to DAX
- Transform controls to Power Query parameters
- Optimize table schemas

### 3️⃣ Generate
- Create PBIP project structure
- Generate TMDL semantic model
- Build Power BI report pages & visuals
- Configure data refresh & deployment

### 4️⃣ Deploy (Optional)
- Publish to Power BI Service
- Configure row-level security (RLS)
- Set up refresh schedule
- Map Looker data permissions

---

## 📊 Supported Data Sources

| Source | Support | Notes |
|--------|---------|-------|
| **Google Sheets** | ✅ Full | Query connectors, named ranges |
| **BigQuery** | ✅ Full | SQL queries, datasets |
| **Google Analytics 4** | ✅ Full | Dimensions, metrics, segments |
| **Google Analytics (UA)** | ✅ Full | Legacy property support |
| **YouTube Analytics** | ✅ Partial | Channel & video metrics |
| **Admetrics** | ✅ Partial | Ad platform integrations |
| **SAP Connector** | ⚠️ Manual | Requires custom mapping |
| **Salesforce** | ⚠️ Manual | Use Power BI native connectors |
| **Custom SQL** | ✅ Full | Converted to T-SQL / DAX queries |

---

## 🔄 Formula Conversion (180+ Functions)

### Common Mappings

**Looker Formula** → **DAX Equivalent**

| Looker | Power BI / DAX | Example |
|--------|---|---------|
| `CASE` | `SWITCH` | `CASE WHEN x THEN y END` |
| `CONCAT` | `CONCATENATE` / `&` | `CONCAT(field1, field2)` |
| `DATE_DIFF` | `DATEDIFF` | `DATE_DIFF(date1, date2, 'day')` |
| `CURRENT_DATE` | `TODAY()` | `CURRENT_DATE()` |
| `SAFE_DIVIDE` | `DIVIDE` | `SAFE_DIVIDE(a, b)` → `DIVIDE(a, b)` |
| `PERCENTILE` | `PERCENTILE.INC` | `PERCENTILE(values, 0.9)` |
| `RUNNING_TOTAL` | `SUM(..., ALL)` | Windowing functions |

📖 **Full reference:** [FORMULA_CONVERSION_REFERENCE.md](docs/LOOKER_TO_DAX_REFERENCE.md)

---

## 📚 Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [Quick Start Guide](docs/QUICK_START.md)
- [Migration Checklist](docs/MIGRATION_CHECKLIST.md)
- [Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- [Known Limitations](docs/KNOWN_LIMITATIONS.md)
- [FAQ](docs/FAQ.md)
- [Roadmap](docs/ROADMAP.md)

---

## 🚀 Deployment

### To Power BI Service
```bash
python migrate.py report.json --deploy WORKSPACE_ID \
    --tenant-id "your-tenant-id" \
    --client-id "your-app-id" \
    --client-secret "your-secret"
```

### To Fabric (Microsoft Fabric)
```bash
python migrate.py report.json --output-format fabric \
    --deploy-fabric WORKSPACE_ID
```

---

## 🤝 Contributing

We welcome contributions! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

---

## 📄 License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.

---

## ❓ Support & Community

- 📖 [Documentation](docs/)
- 🐛 [Bug Reports](https://github.com/your-org/Looker-Studio-To-PowerBI/issues)
- 💬 [Discussions](https://github.com/your-org/Looker-Studio-To-PowerBI/discussions)
- 🔗 [Related Tools](https://github.com/your-org/Looker-Studio-To-PowerBI/wiki)

---

**Made with ❤️ by the Looker Studio → Power BI community**
