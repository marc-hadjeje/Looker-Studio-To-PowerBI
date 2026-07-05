"""
PBIP (.pbip) project generation from Looker Studio reports.

Generates complete Power BI project structure with:
- Model definition (TMDL)
- Report definition (PBIR v4.0)
- Data model relationships
- Measures and calculated columns
- Visual elements
"""

from pathlib import Path
from typing import Dict, List, Any
import json
import uuid
import re
import hashlib


class PBIPGenerator:
    """Generates Power BI .pbip project structure."""
    
    def __init__(self, output_dir: str, project_name: str):
        self.output_dir = Path(output_dir)
        self.project_name = project_name
        # Keep filesystem paths short on Windows to avoid MAX_PATH issues.
        self.path_name = self._to_path_safe_name(project_name)
        self.project_dir = self.output_dir / f"{self.path_name}_pbip"
        self.semantic_model_dir = self.project_dir / f"{self.path_name}.SemanticModel"
        self.semantic_model_definition_dir = self.semantic_model_dir / "definition"
        self.report_dir = self.project_dir / f"{self.path_name}.Report"
        self.report_definition_dir = self.report_dir / "definition"

    def _to_path_safe_name(self, name: str, max_len: int = 24) -> str:
        """Normalize and shorten names used in filesystem paths."""
        normalized = re.sub(r'[^A-Za-z0-9_-]+', '_', str(name or 'report')).strip('._')
        if not normalized:
            normalized = 'report'
        if len(normalized) <= max_len:
            return normalized
        digest = hashlib.sha1(normalized.encode('utf-8')).hexdigest()[:6]
        return f"{normalized[:max_len - 7]}_{digest}"
    
    def create_project_structure(self) -> Path:
        """Create the .pbip project directory structure."""
        self.semantic_model_definition_dir.mkdir(parents=True, exist_ok=True)
        self.report_definition_dir.mkdir(parents=True, exist_ok=True)

        # Create main project file (PBIP standard)
        pbip_content = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/pbip/pbipProperties/1.0.0/schema.json",
            "version": "1.0",
            "artifacts": [
                {
                    "report": {
                        "path": f"{self.path_name}.Report"
                    }
                }
            ],
            "settings": {
                "enableAutoRecovery": True
            }
        }
        pbip_file = self.project_dir / f"{self.path_name}.pbip"
        pbip_file.write_text(json.dumps(pbip_content, indent=2), encoding='utf-8')

        # Keep hidden .pbip in sync for compatibility with existing open flows.
        legacy_pbip_file = self.project_dir / ".pbip"
        legacy_pbip_file.write_text(json.dumps(pbip_content, indent=2), encoding='utf-8')

        # Create report metadata files
        report_platform = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {
                "type": "Report",
                "displayName": self.project_name,
            },
            "config": {
                "version": "2.0",
                "logicalId": str(uuid.uuid4()),
            },
        }
        (self.report_dir / ".platform").write_text(json.dumps(report_platform, indent=2), encoding='utf-8')

        report_definition = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definitionProperties/2.0.0/schema.json",
            "version": "4.0",
            "datasetReference": {
                "byPath": {
                    "path": f"../{self.path_name}.SemanticModel"
                }
            },
        }
        (self.report_dir / "definition.pbir").write_text(json.dumps(report_definition, indent=2), encoding='utf-8')

        report_version = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json",
            "version": "2.0.0",
        }
        (self.report_definition_dir / "version.json").write_text(json.dumps(report_version, indent=2), encoding='utf-8')
        (self.report_definition_dir / "pages").mkdir(parents=True, exist_ok=True)

        # Create semantic model metadata files
        model_platform = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/gitIntegration/platformProperties/2.0.0/schema.json",
            "metadata": {
                "type": "SemanticModel",
                "displayName": self.project_name,
            },
            "config": {
                "version": "2.0",
                "logicalId": str(uuid.uuid4()),
            },
        }
        (self.semantic_model_dir / ".platform").write_text(json.dumps(model_platform, indent=2), encoding='utf-8')

        model_definition = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/semanticModel/definitionProperties/1.0.0/schema.json",
            "version": "4.2",
            "settings": {
                "qnaEnabled": True,
            },
        }
        (self.semantic_model_dir / "definition.pbism").write_text(json.dumps(model_definition, indent=2), encoding='utf-8')
        
        return self.project_dir
    
    def generate_model(self, data_sources: Dict[str, Any], measures: List[Dict] = None,
                      relationships: List[Dict] = None, formulas: Dict[str, Any] = None,
                      pages: Dict[str, Any] = None) -> None:
        """Generate TMDL semantic model with real tables, columns and measures."""

        self._table_names = {}

        # Emit one TMDL table per data source (columns + measures + M partition).
        self._generate_tables_tmdl(data_sources, formulas or {}, pages or {})

        # Generate database.tmdl / model.tmdl once table names are known.
        self._generate_database_tmdl(data_sources)
        self._generate_model_tmdl()

        if relationships:
            self._generate_relationships_tmdl(relationships)

    def _generate_model_tmdl(self) -> None:
        """Generate a valid model.tmdl file referencing generated tables."""

        table_names = list(getattr(self, '_table_names', {}).values())
        model_tmdl = (
            "model Model\n"
            "\tculture: en-US\n"
            "\tdefaultPowerBIDataSourceVersion: powerBI_V3\n"
            "\tsourceQueryCulture: en-US\n"
        )
        if table_names:
            model_tmdl += f"\n\tannotation PBI_QueryOrder = {json.dumps(table_names)}\n"

        (self.semantic_model_definition_dir / "model.tmdl").write_text(model_tmdl, encoding='utf-8')
    
    def _generate_database_tmdl(self, data_sources: Dict) -> None:
        """Generate database.tmdl with model configuration."""

        db_tmdl = """database
	compatibilityLevel: 1600
"""
        
        (self.semantic_model_definition_dir / "database.tmdl").write_text(db_tmdl, encoding='utf-8')
    
    def _generate_tables_tmdl(self, data_sources: Dict, formulas: Dict = None,
                              pages: Dict = None) -> None:
        """Generate real TMDL table definitions (columns + measures + M partition)."""

        formulas = formulas or {}
        pages = pages or {}
        tables_dir = self.semantic_model_definition_dir / "tables"
        tables_dir.mkdir(parents=True, exist_ok=True)

        if not hasattr(self, '_table_names'):
            self._table_names = {}

        for source_id, source in data_sources.items():
            table_name = self._safe_table_name(source.get('name') or source_id)
            self._table_names[source_id] = table_name

            query = source.get('query', '') or ''
            columns = self._parse_query_columns(query)
            measures = self._build_measures_for_source(source_id, table_name, formulas, pages)

            # Guarantee every column referenced by a measure exists on the table.
            existing = {c['name'] for c in columns}
            for col in self._referenced_columns(measures):
                if col not in existing:
                    existing.add(col)
                    columns.append({'name': col, 'dataType': self._infer_data_type(col)})

            tmdl = self._render_table_tmdl(table_name, source, columns, measures, query)
            (tables_dir / f"{table_name}.tmdl").write_text(tmdl, encoding='utf-8')

    # ------------------------------------------------------------------ helpers

    def _safe_table_name(self, name: str) -> str:
        cleaned = re.sub(r'[^A-Za-z0-9_ ]+', '', str(name or 'Table')).strip()
        return cleaned or 'Table'

    def _tmdl_name(self, name: str) -> str:
        """Quote a TMDL identifier if it is not a simple bareword."""
        if re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', name or ''):
            return name
        escaped = str(name).replace("'", "''")
        return f"'{escaped}'"

    def _infer_data_type(self, name: str) -> str:
        n = (name or '').lower()
        if 'date' in n or n.endswith('_at') or n.endswith('_time') or n == 'timestamp':
            return 'dateTime'
        if any(k in n for k in ('amount', 'price', 'cost', 'profit', 'sales', 'revenue',
                                 'margin', 'ratio', 'pct', 'rate', 'value', 'total', 'avg',
                                 'net', 'gross')):
            return 'double'
        if any(k in n for k in ('qty', 'quantity', 'count', 'number', 'num', 'year',
                                 'month', 'day')):
            return 'int64'
        return 'string'

    def _split_top_level(self, text: str) -> List[str]:
        parts, depth, cur, in_tick = [], 0, '', False
        for ch in text:
            if ch == '`':
                in_tick = not in_tick
            if not in_tick:
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth = max(0, depth - 1)
                elif ch == ',' and depth == 0:
                    parts.append(cur)
                    cur = ''
                    continue
            cur += ch
        if cur.strip():
            parts.append(cur)
        return parts

    def _parse_query_columns(self, query: str) -> List[Dict[str, str]]:
        if not query:
            return []
        m = re.search(r'\bSELECT\b(.*?)\bFROM\b', query, re.IGNORECASE | re.DOTALL)
        if not m:
            return []
        columns, seen = [], set()
        for part in self._split_top_level(m.group(1)):
            part = part.strip()
            if not part or part == '*':
                continue
            alias_match = re.search(r'\bAS\b\s+([`"\[]?[A-Za-z_][A-Za-z0-9_]*[`"\]]?)\s*$',
                                    part, re.IGNORECASE)
            if alias_match:
                alias = alias_match.group(1)
            else:
                token = part.split()[-1]
                alias = token.split('.')[-1]
            alias = alias.strip('`"[]')
            if alias and alias not in seen and re.match(r'^[A-Za-z_][A-Za-z0-9_]*$', alias):
                seen.add(alias)
                columns.append({'name': alias, 'dataType': self._infer_data_type(alias)})
        return columns

    def _looker_metric_to_dax(self, metric: str, table: str) -> str:
        if not metric:
            return ''

        def repl(mo):
            agg = mo.group(1).upper()
            col = mo.group(2)
            agg = {'AVG': 'AVERAGE', 'COUNTD': 'DISTINCTCOUNT'}.get(agg, agg)
            return f"{agg}('{table}'[{col}])"

        return re.sub(
            r'\b(SUM|AVERAGE|AVG|DISTINCTCOUNT|COUNTD|COUNTA|COUNT|MIN|MAX)\s*\(\s*([A-Za-z_][A-Za-z0-9_]*)\s*\)',
            repl, metric)

    def _build_measures_for_source(self, source_id: str, table_name: str,
                                   formulas: Dict, pages: Dict) -> List[Dict[str, str]]:
        measures, seen = [], set()

        # Calculated fields -> DAX measures.
        for f in formulas.values():
            fs = f.get('sourceId')
            if fs and fs != source_id:
                continue
            name = f.get('name')
            dax = (f.get('daxExpression') or '').replace('\r', ' ').replace('\n', ' ').strip()
            # Qualify any bare Looker-style aggregations (e.g. SUM(col)) to the table.
            dax = self._looker_metric_to_dax(dax, table_name)
            if name and dax and name not in seen:
                seen.add(name)
                measures.append({'name': name, 'dax': dax})

        # Visual metrics -> DAX measures.
        for page in pages.values():
            for v in page.get('visuals', []):
                vs = v.get('sourceId')
                if vs and vs != source_id:
                    continue
                metric = v.get('metric', '')
                name = v.get('title') or v.get('name')
                if not metric or not name or name in seen:
                    continue
                dax = self._looker_metric_to_dax(metric, table_name)
                if dax and dax != metric:
                    seen.add(name)
                    measures.append({'name': name, 'dax': dax})

        return measures

    def _referenced_columns(self, measures: List[Dict]) -> List[str]:
        cols = []
        for meas in measures:
            for col in re.findall(r"\[([A-Za-z_][A-Za-z0-9_]*)\]", meas.get('dax', '')):
                if col not in cols:
                    cols.append(col)
        return cols

    def _summarize_by(self, data_type: str) -> str:
        return 'sum' if data_type in ('double', 'int64') else 'none'

    def _m_partition_source(self, source: Dict, query: str) -> str:
        pbi_type = source.get('powerbiType', '')
        safe_query = query.replace('"', '""') if query else ''
        if pbi_type == 'GoogleBigQuery' and safe_query:
            project = source.get('projectId', '')
            billing = f'[BillingProject = "{project}"]' if project else ''
            return (
                "let\n"
                f"    Source = GoogleBigQuery.Database({billing}),\n"
                f'    Data = Value.NativeQuery(Source, "{safe_query}")\n'
                "in\n"
                "    Data"
            )
        if safe_query:
            return (
                "let\n"
                f'    Source = Value.NativeQuery(null, "{safe_query}")\n'
                "in\n"
                "    Source"
            )
        return (
            "let\n"
            "    Source = #table({}, {})\n"
            "in\n"
            "    Source"
        )

    def _render_table_tmdl(self, table_name: str, source: Dict, columns: List[Dict],
                           measures: List[Dict], query: str) -> str:
        tname = self._tmdl_name(table_name)
        lines = [f"table {tname}", f"\tlineageTag: {uuid.uuid4()}", ""]

        for col in columns:
            cname = self._tmdl_name(col['name'])
            dtype = col['dataType']
            lines.append(f"\tcolumn {cname}")
            lines.append(f"\t\tdataType: {dtype}")
            lines.append(f"\t\tsummarizeBy: {self._summarize_by(dtype)}")
            lines.append(f"\t\tsourceColumn: {col['name']}")
            lines.append(f"\t\tlineageTag: {uuid.uuid4()}")
            lines.append("")

        for meas in measures:
            mname = self._tmdl_name(meas['name'])
            lines.append(f"\tmeasure {mname} = {meas['dax']}")
            lines.append(f"\t\tlineageTag: {uuid.uuid4()}")
            lines.append("")

        m_source = self._m_partition_source(source, query)
        indented = "\n".join("\t\t\t" + ln for ln in m_source.split("\n"))
        lines.append(f"\tpartition {tname} = m")
        lines.append("\t\tmode: import")
        lines.append("\t\tsource = ```")
        lines.append(indented)
        lines.append("\t\t\t```")
        lines.append("")

        return "\n".join(lines) + "\n"

    def _generate_relationships_tmdl(self, relationships: List[Dict]) -> None:
        """Generate relationship definitions."""

        rel_content = "// Relationships placeholder\n"

        (self.semantic_model_definition_dir / "relationships.tmdl").write_text(rel_content, encoding='utf-8')
    
    def generate_report(self, pages: Dict[str, Any], controls: Dict[str, Any],
                       theme: Dict = None) -> None:
        """Generate Power BI report structure."""

        report_def = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/2.0.0/schema.json",
            "settings": {
                "hideVisualContainerHeader": True,
                "useStylableVisualContainerHeader": True,
                "exportDataMode": "None",
                "defaultDrillFilterOtherVisuals": True,
                "allowChangeFilterTypes": True,
                "useEnhancedTooltips": True,
            },
        }

        (self.report_definition_dir / "report.json").write_text(
            json.dumps(report_def, indent=2),
            encoding='utf-8',
        )

        # PBIR requires pages metadata and at least one concrete page definition.
        pages_root = self.report_definition_dir / "pages"
        pages_root.mkdir(parents=True, exist_ok=True)

        input_pages = list(pages.values()) if isinstance(pages, dict) else []
        if not input_pages:
            input_pages = [{"name": "Page 1", "visuals": []}]

        page_order: List[str] = []
        for idx, page_info in enumerate(input_pages):
            internal_name = "ReportSection" if idx == 0 else f"ReportSection{idx}"
            page_order.append(internal_name)

            page_dir = pages_root / internal_name
            page_dir.mkdir(parents=True, exist_ok=True)
            (page_dir / "visuals").mkdir(parents=True, exist_ok=True)

            page_def = {
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.0.0/schema.json",
                "name": internal_name,
                "displayName": page_info.get("name", f"Page {idx + 1}"),
                "displayOption": "FitToPage",
                "height": 720,
                "width": 1280,
            }
            (page_dir / "page.json").write_text(json.dumps(page_def, indent=2), encoding='utf-8')

        pages_metadata = {
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.0.0/schema.json",
            "pageOrder": page_order,
            "activePageName": page_order[0],
        }
        (pages_root / "pages.json").write_text(json.dumps(pages_metadata, indent=2), encoding='utf-8')
    
    def _generate_report_pages(self, pages: Dict[str, Any]) -> List[Dict]:
        """Generate report page definitions."""
        
        report_pages = []
        
        for page_id, page_info in pages.items():
            page_def = {
                "name": page_info.get('name', f"Page_{page_id}"),
                "displayName": page_info.get('name', f"Page_{page_id}"),
                "visuals": self._generate_visuals(page_info.get('visuals', page_info.get('elements', []))),
            }
            report_pages.append(page_def)
        
        return report_pages
    
    def _generate_visuals(self, elements: List[Dict]) -> List[Dict]:
        """Generate visual definitions."""
        
        visuals = []
        
        for i, element in enumerate(elements):
            visual_def = {
                "name": element.get('name', f"Visual_{i}"),
                "type": element.get('type', 'table'),
                "title": element.get('title', ''),
                "position": element.get('position', {}),
                "size": element.get('size', {}),
            }
            visuals.append(visual_def)
        
        return visuals
    
    def _generate_filters(self, controls: Dict[str, Any]) -> List[Dict]:
        """Generate filter/slicer definitions."""
        
        filters = []
        
        for control_id, control_info in controls.items():
            filter_def = {
                "name": control_info.get('name', control_id),
                "type": control_info.get('type', 'Filter'),
                "field": control_info.get('field', ''),
            }
            filters.append(filter_def)
        
        return filters
    
    def create_config_file(self, config: Dict[str, Any]) -> None:
        """Create project configuration file."""
        
        config_content = {
            "projectName": self.project_name,
            "sourceReport": config.get('sourceReport'),
            "dataSourcesCount": config.get('dataSourcesCount', 0),
            "tablesCount": config.get('tablesCount', 0),
            "measuresCount": config.get('measuresCount', 0),
            "refreshMode": config.get('refreshMode', 'Import'),
            "migratedFrom": "Looker Studio (BigQuery)",
            "createdDate": config.get('createdDate'),
        }
        
        config_file = self.project_dir / ".pbip-config.json"
        config_file.write_text(json.dumps(config_content, indent=2), encoding='utf-8')
    
    def create_readme(self) -> None:
        """Create project README with migration notes."""
        
        readme = f"""# {self.project_name} - Power BI Project

Generated from Looker Studio report using BigQuery as the data source.

## Project Structure

- **{self.project_name}.SemanticModel/** - TMDL semantic model definition
- **{self.project_name}.Report/** - Report and visual definitions

## Data Sources

This project connects to BigQuery datasets. Before opening in Power BI Desktop:

1. Configure BigQuery credentials in Power BI Desktop
2. Update data source connections in the model
3. Test query execution and data refresh

## Next Steps

1. Open this project in Power BI Desktop (December 2025+)
2. Configure each BigQuery data source connection
3. Update row-level security (RLS) if needed
4. Publish to Power BI Service

## Notes

- Some formulas may require manual review and adjustment
- Complex Looker calculations may need DAX optimization
- BigQuery-specific functions should be validated in DAX context

For more information, see the migration documentation.
"""
        
        (self.project_dir / "README.md").write_text(readme, encoding='utf-8')


class PBIPValidator:
    """Validates generated PBIP projects."""
    
    @staticmethod
    def validate_structure(project_dir: Path) -> tuple[bool, list[str]]:
        """Validate that project has correct structure."""
        
        issues = []
        
        required_files = [
            f"{project_dir.name.replace('_pbip', '')}.pbip",
            f"{project_dir.name.replace('_pbip', '')}.SemanticModel/definition/database.tmdl",
            f"{project_dir.name.replace('_pbip', '')}.Report/definition/report.json",
        ]
        
        for file_path in required_files:
            full_path = project_dir / file_path
            if not full_path.exists():
                issues.append(f"Missing required file: {file_path}")
        
        return len(issues) == 0, issues
    
    @staticmethod
    def validate_model(model_dir: Path) -> tuple[bool, list[str]]:
        """Validate model definition."""
        
        issues = []
        
        db_file = model_dir / "definition" / "database.tmdl"
        if not db_file.exists():
            issues.append("database.tmdl not found")
            return False, issues
        
        content = db_file.read_text()
        if 'database' not in content:
            issues.append("Invalid database.tmdl - missing database definition")
        
        return len(issues) == 0, issues
