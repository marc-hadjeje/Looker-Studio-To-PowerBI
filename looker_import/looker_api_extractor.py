"""
Looker Studio API extraction via REST API.

Retrieves report definitions directly from Looker Studio without manual export.
"""

import json
from typing import Dict, List, Optional, Any
import requests


class LookerStudioAPIClient:
    """Client for Looker Studio REST API."""
    
    BASE_URL = "https://datastudio.google.com/api"
    
    def __init__(self, credentials):
        """
        Initialize Looker Studio API client.
        
        Args:
            credentials: Google credentials object (service account or OAuth)
        """
        self.credentials = credentials
        self.session = requests.Session()
        self._setup_session()
    
    def _setup_session(self):
        """Setup HTTP session with credentials."""
        try:
            from google.auth.transport.requests import Request
            
            # Refresh credentials if needed
            if self.credentials.expired:
                self.credentials.refresh(Request())
            
            # Add authorization header
            self.session.headers.update({
                'Authorization': f'Bearer {self.credentials.token}',
                'Content-Type': 'application/json',
            })
        
        except Exception as e:
            print(f"Warning: Could not setup session credentials: {e}")

    def _parse_json_response(self, response: requests.Response, context: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response and print actionable diagnostics when payload is not JSON."""
        try:
            return response.json()
        except ValueError as e:
            content_type = response.headers.get('Content-Type', 'unknown')
            body_preview = (response.text or '').strip().replace('\n', ' ')[:300]
            print(
                f"{context}: Non-JSON response "
                f"(status={response.status_code}, content-type={content_type})."
            )
            if body_preview:
                print(f"{context}: Response preview: {body_preview}")
            print(f"{context}: JSON parse error: {e}")
            return None
    
    def list_reports(self, shared_with_me: bool = False) -> List[Dict[str, Any]]:
        """
        List accessible reports.
        
        Args:
            shared_with_me: Only list reports shared with user
            
        Returns:
            List of report metadata
        """
        try:
            # Looker Studio API endpoint for listing reports
            # Note: This requires proper API access
            url = f"{self.BASE_URL}/reports"
            
            params = {}
            if shared_with_me:
                params['sharedWithMe'] = 'true'
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            payload = self._parse_json_response(response, 'Failed to list reports')
            if payload is None:
                return []

            return payload.get('reports', [])
        
        except requests.exceptions.RequestException as e:
            print(f"Failed to list reports: {e}")
            return []
    
    def get_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Get report definition by ID.
        
        Args:
            report_id: Looker Studio report ID
            
        Returns:
            Report schema or None if failed
        """
        try:
            url = f"{self.BASE_URL}/reports/{report_id}"
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            return self._parse_json_response(response, f"Failed to get report {report_id}")
        
        except requests.exceptions.RequestException as e:
            print(f"Failed to get report {report_id}: {e}")
            return None
    
    def export_report_json(self, report_id: str, output_path: str) -> bool:
        """
        Export report as JSON.
        
        Args:
            report_id: Looker Studio report ID
            output_path: Path to save JSON file
            
        Returns:
            True if successful
        """
        try:
            report_data = self.get_report(report_id)
            
            if report_data is None:
                return False
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(report_data, f, indent=2)
            
            print(f"✓ Exported report to: {output_path}")
            return True
        
        except Exception as e:
            print(f"Failed to export report: {e}")
            return False
    
    def search_reports(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for reports by title or ID.
        
        Args:
            query: Search query
            
        Returns:
            List of matching reports
        """
        try:
            url = f"{self.BASE_URL}/reports/search"
            
            params = {'q': query}
            
            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            payload = self._parse_json_response(response, 'Search failed')
            if payload is None:
                return []

            return payload.get('results', [])
        
        except requests.exceptions.RequestException as e:
            print(f"Search failed: {e}")
            return []


class LookerStudioProgrammaticExtractor:
    """Extract Looker Studio report structure programmatically."""
    
    def __init__(self, credentials):
        """
        Initialize extractor.
        
        Args:
            credentials: Google credentials
        """
        self.client = LookerStudioAPIClient(credentials)
        self.extracted_reports = {}
    
    def extract_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """
        Extract a single report by ID.
        
        Args:
            report_id: Looker Studio report ID (from URL)
            
        Returns:
            Report schema
        """
        print(f"Extracting report: {report_id}")
        
        report = self.client.get_report(report_id)
        
        if report:
            self.extracted_reports[report_id] = report
            self._log_extraction_summary(report)
        
        return report
    
    def extract_all_accessible(self) -> Dict[str, Dict[str, Any]]:
        """
        Extract all reports accessible to user.
        
        Returns:
            Dict of report_id -> report_schema
        """
        print("Fetching list of accessible reports...")
        
        reports = self.client.list_reports(shared_with_me=True)
        
        print(f"Found {len(reports)} reports")
        
        for report_info in reports:
            report_id = report_info.get('id')
            if report_id:
                report = self.extract_report(report_id)
                if report:
                    self.extracted_reports[report_id] = report
        
        return self.extracted_reports
    
    def _log_extraction_summary(self, report: Dict) -> None:
        """Log summary of extracted report."""
        title = report.get('title', 'Untitled')
        data_sources = len(report.get('dataSources', []))
        pages = len(report.get('pages', []))
        controls = len(report.get('parameterControls', []))
        
        print(f"  ✓ Title: {title}")
        print(f"  ✓ Data Sources: {data_sources}")
        print(f"  ✓ Pages: {pages}")
        print(f"  ✓ Controls: {controls}")
    
    def get_report_preview(self, report_id: str) -> Dict[str, Any]:
        """
        Get preview summary of report without full extraction.
        
        Args:
            report_id: Report ID
            
        Returns:
            Preview info
        """
        report = self.client.get_report(report_id)
        
        if not report:
            return {}
        
        return {
            'id': report.get('id'),
            'title': report.get('title'),
            'description': report.get('description', ''),
            'dataSources': len(report.get('dataSources', [])),
            'pages': len(report.get('pages', [])),
            'controls': len(report.get('parameterControls', [])),
            'owner': report.get('owner', {}).get('displayName', 'Unknown'),
        }


class AlternativeExtractionMethods:
    """Alternative extraction methods when API is limited."""
    
    @staticmethod
    def extract_via_public_json_endpoint(report_id: str) -> Optional[Dict]:
        """
        Try to extract from public JSON endpoint if available.
        
        Note: This may not work for all reports due to access restrictions.
        """
        try:
            # Looker Studio public data endpoint
            url = f"https://datastudio.google.com/api/reports/{report_id}/data"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            return response.json()
        
        except Exception as e:
            print(f"Public endpoint extraction failed: {e}")
            return None
    
    @staticmethod
    def parse_report_url(url: str) -> Optional[str]:
        """
        Extract report ID from Looker Studio URL.
        
        Example:
            https://datastudio.google.com/reporting/abc123def456/page/page1
            → abc123def456
        """
        import re
        
        pattern = r'datastudio\.google\.com/reporting/([a-zA-Z0-9]+)'
        match = re.search(pattern, url)
        
        if match:
            return match.group(1)
        
        return None
