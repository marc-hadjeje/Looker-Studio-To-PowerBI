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
    
    def generate_model(self, data_sources: Dict[str, Any], measures: List[Dict],
                      relationships: List[Dict] = None) -> None:
        """Generate TMDL semantic model."""
        
        # Generate database.tmdl
        self._generate_database_tmdl(data_sources)
        self._generate_model_tmdl()
        
        # Generate placeholder folders/files expected by PBIP/TMDL projects.
        self._generate_tables_tmdl(data_sources)

        if relationships:
            self._generate_relationships_tmdl(relationships)

    def _generate_model_tmdl(self) -> None:
        """Generate a minimal valid model.tmdl file."""

        model_tmdl = """model Model
	culture: en-US
	defaultPowerBIDataSourceVersion: powerBI_V3
	sourceQueryCulture: en-US
"""

        (self.semantic_model_definition_dir / "model.tmdl").write_text(model_tmdl, encoding='utf-8')
    
    def _generate_database_tmdl(self, data_sources: Dict) -> None:
        """Generate database.tmdl with model configuration."""

        db_tmdl = """database
	compatibilityLevel: 1600
"""
        
        (self.semantic_model_definition_dir / "database.tmdl").write_text(db_tmdl, encoding='utf-8')
    
    def _generate_tables_tmdl(self, data_sources: Dict) -> None:
        """Generate placeholder table artifacts.

        The current converter does not yet emit full valid TMDL table definitions,
        so keep this empty but create the standard folder expected by PBIP projects.
        """

        tables_dir = self.semantic_model_definition_dir / "tables"
        tables_dir.mkdir(parents=True, exist_ok=True)
    
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
