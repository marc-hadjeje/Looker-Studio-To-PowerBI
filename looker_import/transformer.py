"""
Transform Looker Studio components to Power BI equivalents.

Handles:
- Formula conversion (Looker → DAX)
- Control transformation (filters → parameters)
- Data source mapping
- Visual conversion
"""

from typing import Dict, List, Any, Tuple
from .dax_recipes import LookerToDaxConverter


class LookerStudioTransformer:
    """Transforms Looker Studio components to Power BI equivalents."""
    
    def __init__(self):
        self.dax_converter = LookerToDaxConverter()
        self.data_source_mapping = {}
        self.control_mapping = {}
        self.formula_mapping = {}
    
    def transform_data_sources(self, data_sources: Dict[str, Dict[str, Any]],
                              datasource_config: Dict = None) -> Dict[str, Dict[str, Any]]:
        """Transform Looker Studio data sources to Power BI connections."""
        transformed = {}
        config = datasource_config or {}
        
        for source_id, source in data_sources.items():
            if not source.get('name'):
                source = {**source, 'name': source_id}

            source_type = source.get('type', source.get('sourceType', '')).lower()
            
            if source_type == 'google_sheets':
                transformed[source_id] = self._transform_sheets_source(source, config)
            elif source_type == 'bigquery':
                transformed[source_id] = self._transform_bigquery_source(source, config)
            elif source_type == 'google_analytics_4':
                transformed[source_id] = self._transform_ga4_source(source, config)
            elif source_type == 'google_analytics':
                transformed[source_id] = self._transform_ua_source(source, config)
            else:
                transformed[source_id] = self._transform_custom_source(source, config)
        
        self.data_source_mapping = transformed
        return transformed
    
    def _transform_sheets_source(self, source: Dict, config: Dict) -> Dict[str, Any]:
        """Transform Google Sheets source."""
        return {
            'powerbiType': 'ExcelOnline',
            'name': source.get('name'),
            'spreadsheetUrl': config.get('spreadsheetUrl', ''),
            'worksheetName': source.get('configuration', {}).get('worksheetName', ''),
            'namedRange': source.get('configuration', {}).get('namedRange', ''),
            'connectionString': source.get('configuration', {}).get('connectionString', ''),
        }
    
    def _transform_bigquery_source(self, source: Dict, config: Dict) -> Dict[str, Any]:
        """Transform BigQuery source."""
        return {
            'powerbiType': 'GoogleBigQuery',
            'name': source.get('name'),
            'projectId': source.get('configuration', {}).get('projectId', ''),
            'datasetId': source.get('configuration', {}).get('datasetId', ''),
            'query': source.get('query', source.get('original', '')),
        }
    
    def _transform_ga4_source(self, source: Dict, config: Dict) -> Dict[str, Any]:
        """Transform Google Analytics 4 source."""
        return {
            'powerbiType': 'GoogleAnalytics4',
            'name': source.get('name'),
            'propertyId': source.get('configuration', {}).get('propertyId', ''),
            'dateRange': source.get('configuration', {}).get('dateRange', ''),
        }
    
    def _transform_ua_source(self, source: Dict, config: Dict) -> Dict[str, Any]:
        """Transform Google Analytics (UA) source."""
        return {
            'powerbiType': 'GoogleAnalytics',
            'name': source.get('name'),
            'viewId': source.get('configuration', {}).get('viewId', ''),
            'profileId': source.get('configuration', {}).get('profileId', ''),
        }
    
    def _transform_custom_source(self, source: Dict, config: Dict) -> Dict[str, Any]:
        """Transform generic/custom source."""
        return {
            'powerbiType': 'CustomAPI',
            'name': source.get('name'),
            'sourceType': source.get('type'),
            'configuration': source.get('configuration', {}),
        }
    
    def transform_controls(self, controls: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Transform Looker Studio controls to Power BI parameters."""
        transformed = {}
        
        for control_id, control in controls.items():
            control_type = control['type']
            
            if control_type == 'filter_control':
                transformed[control_id] = self._transform_filter_control(control)
            elif control_type == 'date_range_control':
                transformed[control_id] = self._transform_date_range_control(control)
            elif control_type == 'dropdown_control':
                transformed[control_id] = self._transform_dropdown_control(control)
            else:
                transformed[control_id] = self._transform_generic_control(control)
        
        self.control_mapping = transformed
        return transformed
    
    def _transform_filter_control(self, control: Dict) -> Dict[str, Any]:
        """Transform filter control."""
        return {
            'powerbiType': 'Slicer',
            'name': control.get('name'),
            'field': control.get('linkedParameter', ''),
            'displayMode': 'List',
        }
    
    def _transform_date_range_control(self, control: Dict) -> Dict[str, Any]:
        """Transform date range control."""
        return {
            'powerbiType': 'DateSlicerRange',
            'name': control.get('name'),
            'field': control.get('linkedParameter', ''),
            'defaultStart': control.get('options', {}).get('startDate', ''),
            'defaultEnd': control.get('options', {}).get('endDate', ''),
        }
    
    def _transform_dropdown_control(self, control: Dict) -> Dict[str, Any]:
        """Transform dropdown control."""
        return {
            'powerbiType': 'Dropdown',
            'name': control.get('name'),
            'field': control.get('linkedParameter', ''),
            'options': control.get('options', []),
            'multiSelect': control.get('style', {}).get('multiSelect', False),
        }
    
    def _transform_generic_control(self, control: Dict) -> Dict[str, Any]:
        """Transform generic control."""
        return {
            'powerbiType': 'Parameter',
            'name': control.get('name'),
            'type': control.get('type'),
            'linkedParameter': control.get('linkedParameter', ''),
        }
    
    def transform_formulas(self, formulas: Dict[str, Dict[str, Any]]) -> Dict[str, Tuple[str, str]]:
        """Transform Looker formulas to DAX expressions."""
        transformed = {}
        
        for formula_id, formula in formulas.items():
            looker_expr = formula.get('expression', '')
            dax_expr = self.dax_converter.convert(looker_expr)
            
            transformed[formula_id] = {
                'name': formula.get('name'),
                'lookerExpression': looker_expr,
                'daxExpression': dax_expr,
                'type': formula.get('type'),
                'fidelity': self.dax_converter.get_fidelity_score(looker_expr),
            }
        
        self.formula_mapping = transformed
        return transformed
    
    def transform_pages(self, pages: Dict[str, Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """Transform pages and visual layout."""
        transformed = {}
        
        for page_id, page in pages.items():
            transformed[page_id] = {
                'name': page.get('name'),
                'layout': self._transform_layout(page.get('layout', 'GRID')),
                'visuals': [
                    self._transform_visual(element)
                    for element in page.get('elements', [])
                ],
            }
        
        return transformed
    
    def _transform_layout(self, layout_type: Any) -> str:
        """Transform page layout type."""
        if isinstance(layout_type, dict):
            return 'grid'

        if not isinstance(layout_type, str):
            layout_type = str(layout_type or 'GRID')

        mapping = {
            'GRID': 'grid',
            'FREE': 'freeform',
            'TAB': 'tab',
        }
        return mapping.get(layout_type.upper(), 'grid')
    
    def _transform_visual(self, element: Dict) -> Dict[str, Any]:
        """Transform visual element."""
        element_type = element.get('type', 'UNKNOWN')
        
        visual_mapping = {
            'SCORECARD': 'card',
            'TABLE': 'table',
            'CHART': self._detect_chart_type(element),
            'IMAGE': 'image',
            'TEXT': 'textbox',
            'GAUGE': 'gauge',
            'GEO_MAP': 'map',
        }
        
        return {
            'name': element.get('name', ''),
            'powerbiType': visual_mapping.get(element_type, 'visual'),
            'title': element.get('title', ''),
            'sourceId': element.get('sourceId', ''),
            'style': element.get('style', {}),
        }
    
    def _detect_chart_type(self, element: Dict) -> str:
        """Detect specific chart type."""
        chart_config = element.get('chartConfig', {})
        chart_type = chart_config.get('chartType', 'line').lower()
        
        mapping = {
            'line': 'lineChart',
            'column': 'columnChart',
            'bar': 'barChart',
            'pie': 'pieChart',
            'area': 'areaChart',
            'scatter': 'scatterChart',
            'bubble': 'bubbleChart',
        }
        
        return mapping.get(chart_type, 'lineChart')
    
    def get_migration_summary(self) -> Dict[str, Any]:
        """Get summary of all transformations."""
        return {
            'dataSources': len(self.data_source_mapping),
            'controls': len(self.control_mapping),
            'formulas': len(self.formula_mapping),
            'formulaFidelity': self._calculate_fidelity(),
        }
    
    def _calculate_fidelity(self) -> float:
        """Calculate average formula fidelity."""
        if not self.formula_mapping:
            return 100.0
        
        total = sum(
            formula.get('fidelity', 0)
            for formula in self.formula_mapping.values()
        )
        
        return total / len(self.formula_mapping)
