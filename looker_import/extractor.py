"""
Looker Studio report schema extraction.

Parses Looker Studio JSON exports or Google API responses to extract:
- Data sources and queries
- Report controls and filters
- Pages and visualizations
- Calculated fields and formulas
"""

import json
from typing import Dict, List, Any, Optional
from pathlib import Path


class LookerStudioExtractor:
    """Extracts components from Looker Studio report schemas."""
    
    def __init__(self):
        self.report_schema = {}
        self.data_sources = {}
        self.controls = {}
        self.pages = {}
        self.formulas = {}
    
    def load_from_json(self, json_path: str) -> Dict[str, Any]:
        """Load Looker Studio report from JSON export."""
        with open(json_path, 'r', encoding='utf-8') as f:
            self.report_schema = json.load(f)
        return self.report_schema
    
    def load_from_google_api(self, report_id: str, credentials) -> Dict[str, Any]:
        """Load Looker Studio report from Google API."""
        # TODO: Implement Google API integration
        raise NotImplementedError("Google API integration not yet implemented")
    
    def extract_data_sources(self) -> Dict[str, Dict[str, Any]]:
        """Extract all data sources from report."""
        self.data_sources = {}
        
        for source in self.report_schema.get('dataSources', []):
            source_id = source.get('id', '')
            source_type = source.get('sourceType', '').lower()
            
            self.data_sources[source_id] = {
                'id': source_id,
                'type': source_type,
                'name': source.get('name', f'Source_{source_id}'),
                'configuration': source.get('dataSourceParameters', {}),
                'query': source.get('query', ''),
                'fields': source.get('fields', []),
                'connectorId': source.get('connectorId', ''),
            }
        
        return self.data_sources
    
    def extract_controls(self) -> Dict[str, Dict[str, Any]]:
        """Extract filter controls and parameters."""
        self.controls = {}
        
        for control in self.report_schema.get('parameterControls', []):
            control_id = control.get('id', '')
            control_type = control.get('controlType', control.get('type', '')).lower()
            
            self.controls[control_id] = {
                'id': control_id,
                'type': control_type,
                'name': control.get('name', f'Control_{control_id}'),
                'linkedParameter': control.get('linkedParameter', control.get('linkedField', '')),
                'options': control.get('options', control.get('defaultValue', [])),
                'defaultValue': control.get('defaultValue', ''),
                'style': control.get('style', {}),
            }
        
        return self.controls
    
    def extract_pages(self) -> Dict[str, Dict[str, Any]]:
        """Extract pages and visual elements."""
        self.pages = {}
        
        for page in self.report_schema.get('pages', []):
            page_id = page.get('id', '')
            
            self.pages[page_id] = {
                'id': page_id,
                'name': page.get('name', f'Page_{page_id}'),
                'layout': page.get('layout', 'GRID'),
                'elements': page.get('elements', page.get('visuals', [])),
            }
        
        return self.pages
    
    def extract_formulas(self) -> Dict[str, Dict[str, Any]]:
        """Extract calculated fields and custom formulas."""
        self.formulas = {}
        
        for field in self.report_schema.get('calculatedFields', []):
            field_id = field.get('id', '')
            
            self.formulas[field_id] = {
                'id': field_id,
                'name': field.get('name', ''),
                'expression': field.get('expression', ''),
                'type': field.get('type', 'STRING'),
                'sourceId': field.get('sourceId', ''),
            }
        
        return self.formulas
    
    def extract_all(self) -> Dict[str, Any]:
        """Extract all components."""
        return {
            'report': self.report_schema,
            'dataSources': self.extract_data_sources(),
            'controls': self.extract_controls(),
            'pages': self.extract_pages(),
            'formulas': self.extract_formulas(),
        }
    
    def get_report_metadata(self) -> Dict[str, Any]:
        """Get report-level metadata."""
        return {
            'title': self.report_schema.get('title', 'Untitled Report'),
            'description': self.report_schema.get('description', ''),
            'owner': self.report_schema.get('owner', {}),
            'created': self.report_schema.get('created', ''),
            'modified': self.report_schema.get('modified', ''),
        }
    
    def validate_schema(self) -> List[str]:
        """Validate report schema and return list of issues."""
        issues = []
        
        if not self.report_schema:
            issues.append("No report schema loaded")
        
        if 'dataSources' not in self.report_schema:
            issues.append("No data sources found")
        
        if 'pages' not in self.report_schema or not self.report_schema['pages']:
            issues.append("No pages found")
        
        return issues
