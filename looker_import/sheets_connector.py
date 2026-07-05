"""
Google Sheets integration for Looker Studio to Power BI migration.

Handles:
- Google Sheets authentication (OAuth, service account)
- Spreadsheet and sheet discovery
- Data range extraction
- Named range detection
- Query and formula parsing
"""

from typing import Dict, List, Any, Optional, Tuple
import json


class GoogleSheetsConnector:
    """Manages Google Sheets connections and operations."""
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        Initialize Google Sheets connector.
        
        Args:
            credentials_path: Path to service account JSON or OAuth credentials
        """
        self.credentials_path = credentials_path
        self.client = None
        self.spreadsheets = {}
        self.sheets_cache = {}
    
    def authenticate(self, credentials_json: Optional[str] = None) -> bool:
        """Authenticate with Google Sheets using OAuth or service account."""
        try:
            # TODO: Implement Google Sheets authentication
            # from google.auth.transport.requests import Request
            # from google.oauth2.service_account import Credentials
            return True
        except Exception as e:
            print(f"Google Sheets authentication failed: {e}")
            return False
    
    def list_spreadsheets(self) -> List[Dict]:
        """List all accessible spreadsheets."""
        return self.spreadsheets
    
    def get_spreadsheet_metadata(self, spreadsheet_id: str) -> Dict[str, Any]:
        """Get metadata for a spreadsheet."""
        return {
            'id': spreadsheet_id,
            'title': '',
            'locale': 'en_US',
            'sheets': [],
            'namedRanges': [],
        }
    
    def list_sheets(self, spreadsheet_id: str) -> List[str]:
        """List all sheets in a spreadsheet."""
        return self.sheets_cache.get(spreadsheet_id, [])
    
    def get_sheet_data(self, spreadsheet_id: str, sheet_range: str) -> List[List[Any]]:
        """Get data from a specific sheet range."""
        # TODO: Implement sheet data retrieval
        return []
    
    def get_sheet_headers(self, spreadsheet_id: str, sheet_name: str) -> List[str]:
        """Get header row from a sheet."""
        # TODO: Implement header extraction
        return []
    
    def get_named_ranges(self, spreadsheet_id: str) -> Dict[str, Dict]:
        """Get all named ranges in a spreadsheet."""
        return {}
    
    def validate_sheet_connection(self, spreadsheet_id: str) -> Tuple[bool, Optional[str]]:
        """Validate connection to a spreadsheet."""
        # TODO: Implement connection validation
        return True, None


class GoogleSheetsExtractor:
    """Extracts Looker Studio reports using Google Sheets as data source."""
    
    def __init__(self):
        self.connector = GoogleSheetsConnector()
        self.looker_sheets_queries = {}
        self.sheets_mappings = {}
    
    def extract_sheets_from_looker(self, report_schema: Dict) -> Dict[str, Dict]:
        """Extract Google Sheets data sources from Looker Studio report."""
        sheets_sources = {}
        
        for source in report_schema.get('dataSources', []):
            if source.get('sourceType', '').lower() == 'google_sheets':
                source_id = source.get('id')
                config = source.get('configuration', {})
                
                sheets_sources[source_id] = {
                    'spreadsheetId': config.get('spreadsheetId', ''),
                    'worksheetName': config.get('worksheetName', ''),
                    'range': config.get('range', ''),
                    'namedRange': config.get('namedRange', ''),
                    'hasHeaders': config.get('hasHeaders', True),
                    'query': source.get('query', ''),
                    'name': source.get('name', f'Sheet_{source_id}'),
                }
        
        self.looker_sheets_queries = sheets_sources
        return sheets_sources
    
    def extract_sheet_schema(self, sheets_sources: Dict[str, Dict]) -> Dict[str, Dict]:
        """Extract schema information from Google Sheets."""
        schemas = {}
        
        for source_id, sheet_info in sheets_sources.items():
            # Get headers to infer schema
            headers = self.connector.get_sheet_headers(
                sheet_info['spreadsheetId'],
                sheet_info['worksheetName']
            )
            
            schemas[source_id] = {
                'columns': headers,
                'rowCount': 0,  # TODO: Get actual row count
                'dataTypes': self._infer_data_types(headers),
            }
        
        return schemas
    
    def _infer_data_types(self, headers: List[str]) -> Dict[str, str]:
        """Infer data types from column names and samples."""
        type_mapping = {}
        
        for header in headers:
            header_lower = header.lower()
            
            if any(x in header_lower for x in ['date', 'time', 'day', 'month', 'year']):
                type_mapping[header] = 'DateTime'
            elif any(x in header_lower for x in ['count', 'amount', 'total', 'revenue', 'cost']):
                type_mapping[header] = 'Decimal'
            elif any(x in header_lower for x in ['flag', 'is_', 'has_']):
                type_mapping[header] = 'Boolean'
            else:
                type_mapping[header] = 'String'
        
        return type_mapping
    
    def convert_sheets_to_power_bi(self, sheets_sources: Dict[str, Dict]) -> Dict[str, Dict]:
        """Convert Google Sheets sources to Power BI format."""
        converted = {}
        
        for source_id, sheet_info in sheets_sources.items():
            converted[source_id] = {
                'powerbiType': 'ExcelOnline',
                'name': sheet_info.get('name'),
                'spreadsheetUrl': self._build_sheets_url(sheet_info['spreadsheetId']),
                'worksheetName': sheet_info.get('worksheetName'),
                'range': sheet_info.get('range'),
                'namedRange': sheet_info.get('namedRange'),
                'connectionType': 'GoogleSheets',
                'refreshMode': 'Schedule',
                'refreshInterval': 24,  # hours
            }
        
        self.sheets_mappings = converted
        return converted
    
    def _build_sheets_url(self, spreadsheet_id: str) -> str:
        """Build Google Sheets URL."""
        return f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit"


class GoogleSheetsToDataflowMapper:
    """Maps Google Sheets to Power BI Dataflow Gen2 or DirectLake."""
    
    def __init__(self):
        self.m_queries = []
    
    def generate_m_query(self, sheet_config: Dict) -> str:
        """Generate Power Query M for Google Sheets."""
        
        spreadsheet_id = sheet_config.get('spreadsheetId')
        worksheet_name = sheet_config.get('worksheetName', 'Sheet1')
        has_headers = sheet_config.get('hasHeaders', True)
        
        m_expression = f"""
let
    Source = Excel.Workbook(
        Web.Contents(
            "https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=xlsx"
        ),
        null,
        true
    ),
    Sheet = Source{{[Item="{worksheet_name}", Kind="Sheet"]}}[Data],
    PromotedHeaders = if {str(has_headers).lower()} then Table.PromoteHeaders(Sheet) else Sheet
in
    PromotedHeaders
"""
        
        self.m_queries.append(m_expression)
        return m_expression
    
    def generate_direct_lake_mapping(self, sheet_config: Dict) -> Dict[str, Any]:
        """Generate Direct Lake mapping for Fabric Lakehouse."""
        
        return {
            'sourceType': 'GoogleSheets',
            'spreadsheetId': sheet_config.get('spreadsheetId'),
            'worksheetName': sheet_config.get('worksheetName'),
            'lakehouseTable': self._normalize_table_name(sheet_config.get('name')),
            'refreshMode': 'Scheduled',
            'refreshInterval': '1 day',
        }
    
    def _normalize_table_name(self, name: str) -> str:
        """Normalize sheet name to valid Lakehouse table name."""
        return name.replace(' ', '_').replace('-', '_').lower()


class CombinedDataSourceManager:
    """Manages multiple data sources (BigQuery + Google Sheets) for migration."""
    
    def __init__(self):
        from .bigquery_connector import BigQueryExtractor
        self.bigquery_extractor = BigQueryExtractor(project_id='')
        self.sheets_extractor = GoogleSheetsExtractor()
        self.combined_sources = {}
    
    def extract_all_sources(self, report_schema: Dict) -> Dict[str, Dict]:
        """Extract all data sources from Looker Studio (BigQuery + Sheets)."""
        
        all_sources = {}
        
        # Extract BigQuery sources
        bq_sources = self.bigquery_extractor.extract_queries_from_looker(report_schema)
        for source_id, source in bq_sources.items():
            all_sources[source_id] = {
                **source,
                'sourceType': 'bigquery',
                'priority': 1,  # Higher priority for BigQuery
            }
        
        # Extract Google Sheets sources
        sheets_sources = self.sheets_extractor.extract_sheets_from_looker(report_schema)
        for source_id, source in sheets_sources.items():
            all_sources[source_id] = {
                **source,
                'sourceType': 'google_sheets',
                'priority': 2,
            }
        
        self.combined_sources = all_sources
        return all_sources
    
    def convert_all_sources(self) -> Dict[str, Dict]:
        """Convert all sources to Power BI format."""
        
        converted = {}
        
        for source_id, source in self.combined_sources.items():
            if source['sourceType'] == 'bigquery':
                # Convert BigQuery query to T-SQL
                converted[source_id] = {
                    'name': source.get('name'),
                    'type': 'BigQuery',
                    'connectionType': 'PowerBI.com',
                    'query': self.bigquery_extractor._convert_bigquery_to_tsql(
                        source.get('original', '')
                    ),
                }
            elif source['sourceType'] == 'google_sheets':
                # Convert Sheets to Excel Online or direct lake
                converted[source_id] = {
                    'name': source.get('name'),
                    'type': 'GoogleSheets',
                    'connectionType': 'ExcelOnline',
                    'spreadsheetUrl': source.get('spreadsheetUrl', ''),
                }
        
        return converted
    
    def get_migration_summary(self) -> Dict[str, Any]:
        """Get summary of data source migration."""
        
        bq_count = sum(
            1 for s in self.combined_sources.values()
            if s['sourceType'] == 'bigquery'
        )
        sheets_count = sum(
            1 for s in self.combined_sources.values()
            if s['sourceType'] == 'google_sheets'
        )
        
        return {
            'totalSources': len(self.combined_sources),
            'bigQuerySources': bq_count,
            'googleSheetsSources': sheets_count,
            'sources': self.combined_sources,
        }
