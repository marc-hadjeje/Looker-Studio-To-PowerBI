"""
Main script for Looker Studio to Power BI migration

Pipeline:
1. Extract report schema from Looker Studio (via Google API or JSON export)
2. Parse data sources, queries, controls, and formulas
3. Generate the Power BI project (.pbip) with TMDL model
4. Generate migration report with per-item fidelity tracking

Supports:
- Single report migration:     python migrate.py report.json
- Batch migration:             python migrate.py --batch --input-dir reports/
- Live from Looker Studio:     python migrate.py --report-id "id" --auth
- Custom output directory:     python migrate.py report.json --output-dir out/
- Verbose logging:             python migrate.py report.json --verbose
"""

import os
import sys
import json
import logging
import argparse
import tempfile
from datetime import datetime
from enum import IntEnum
from html import escape
from pathlib import Path

# Import migration components
try:
    from looker_import.extractor import LookerStudioExtractor
    from looker_import.transformer import LookerStudioTransformer
    from looker_import.generator import PBIPGenerator
    from looker_import.sheets_connector import CombinedDataSourceManager
    from looker_import.auth_handler import GoogleAuthHandler, CredentialsManager
    from looker_import.looker_api_extractor import LookerStudioProgrammaticExtractor
except ImportError:
    # Graceful fallback if running from different location
    pass


# ── Structured exit codes ────────────────────────────────────────────

class ExitCode(IntEnum):
    """Structured exit codes for CI/CD integration."""
    SUCCESS = 0
    GENERAL_ERROR = 1
    FILE_NOT_FOUND = 2
    EXTRACTION_FAILED = 3
    GENERATION_FAILED = 4
    VALIDATION_FAILED = 5
    ASSESSMENT_FAILED = 6
    BATCH_PARTIAL_FAIL = 7
    AUTH_FAILED = 8
    KEYBOARD_INTERRUPT = 130


# Ensure Unicode output on Windows consoles
if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except (AttributeError, OSError):
        pass


# ── Logging setup ────────────────────────────────────────────────────

def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure logging with appropriate level."""
    level = logging.DEBUG if verbose else logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    
    return logging.getLogger(__name__)


logger = setup_logging()


# ── Main migration logic ─────────────────────────────────────────────

class LookerStudioMigrator:
    """Main class for Looker Studio to Power BI migration."""
    
    def __init__(self, output_dir: str = None, verbose: bool = False):
        self.output_dir = output_dir or 'looker_migration_output'
        self.verbose = verbose
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Initialize components
        self.extractor = LookerStudioExtractor()
        self.transformer = LookerStudioTransformer()
        self.generator = None
        self.data_source_manager = CombinedDataSourceManager()
        
        # Create output directory
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def migrate_from_json(self, json_path: str) -> str:
        """Migrate a Looker Studio report from exported JSON."""
        try:
            self.logger.info(f"Loading Looker Studio report from {json_path}")
            
            # Step 1: Extract report schema
            report_schema = self.extractor.load_from_json(json_path)
            metadata = self.extractor.get_report_metadata()
            report_name = metadata.get('title', 'Looker_Report').replace(' ', '_')
            
            self.logger.info(f"Extracted report: {report_name}")
            
            # Step 2: Validate schema
            validation_issues = self.extractor.validate_schema()
            if validation_issues:
                for issue in validation_issues:
                    self.logger.warning(f"Schema issue: {issue}")
            
            # Step 3: Extract all components (BigQuery + Google Sheets)
            self.logger.info("Extracting data sources (BigQuery + Google Sheets)...")
            all_sources = self.data_source_manager.extract_all_sources(report_schema)
            
            data_sources = self.extractor.extract_data_sources()
            controls = self.extractor.extract_controls()
            pages = self.extractor.extract_pages()
            formulas = self.extractor.extract_formulas()
            
            # Step 4: Log data source summary
            summary = self.data_source_manager.get_migration_summary()
            self.logger.info(f"Found {summary['totalSources']} data sources:")
            self.logger.info(f"  - BigQuery: {summary['bigQuerySources']}")
            self.logger.info(f"  - Google Sheets: {summary['googleSheetsSources']}")
            self.logger.info(f"Found {len(controls)} controls/filters")
            self.logger.info(f"Found {len(pages)} pages")
            
            # Step 5: Transform components
            self.logger.info("Transforming components...")
            transformed_sources = self.transformer.transform_data_sources(all_sources)
            transformed_controls = self.transformer.transform_controls(controls)
            transformed_formulas = self.transformer.transform_formulas(formulas)
            transformed_pages = self.transformer.transform_pages(pages)
            
            # Log transformation summary
            transform_summary = self.transformer.get_migration_summary()
            self.logger.info(f"Transformation summary:")
            self.logger.info(f"  - Average formula fidelity: {transform_summary['formulaFidelity']:.1f}%")
            
            # Step 6: Generate Power BI project
            self.logger.info("Generating Power BI .pbip project...")
            self.generator = PBIPGenerator(self.output_dir, report_name)
            project_dir = self.generator.create_project_structure()
            
            # Generate model
            self.generator.generate_model(
                data_sources=transformed_sources,
                formulas=transformed_formulas,
                pages=transformed_pages,
                relationships=[]
            )
            
            # Generate report
            self.generator.generate_report(
                pages=transformed_pages,
                controls=transformed_controls
            )
            
            # Create configuration
            self.generator.create_config_file({
                'sourceReport': report_name,
                'dataSourcesCount': len(all_sources),
                'tablesCount': len(data_sources),
                'measuresCount': len(formulas),
                'createdDate': datetime.now().isoformat(),
            })
            
            # Create README
            self.generator.create_readme()
            
            # Step 7: Generate migration report
            self._generate_migration_report(project_dir, summary, transform_summary)
            
            self.logger.info(f"✓ Migration complete: {project_dir}")
            return str(project_dir)
            
        except FileNotFoundError:
            self.logger.error(f"File not found: {json_path}")
            raise
        except json.JSONDecodeError:
            self.logger.error(f"Invalid JSON file: {json_path}")
            raise
        except Exception as e:
            self.logger.error(f"Migration failed: {e}", exc_info=True)
            raise
    
    def _extract_data_sources(self, report_schema: dict) -> dict:
        """Extract and parse data sources from report schema."""
        data_sources = {}
        
        for source in report_schema.get('dataSources', []):
            source_id = source.get('id')
            source_type = source.get('sourceType', '').lower()
            
            data_sources[source_id] = {
                'type': source_type,
                'name': source.get('name', f'Source_{source_id}'),
                'configuration': source.get('dataSourceParameters', {}),
                'query': source.get('query', ''),
            }
        
        return data_sources
    
    def _extract_controls(self, report_schema: dict) -> dict:
        """Extract filter controls from report schema."""
        controls = {}
        
        for control in report_schema.get('parameterControls', []):
            control_id = control.get('id')
            control_type = control.get('controlType', '').lower()
            
            controls[control_id] = {
                'type': control_type,
                'name': control.get('name', f'Control_{control_id}'),
                'field': control.get('linkedParameter', ''),
                'options': control.get('options', []),
            }
        
        return controls
    
    def _extract_pages(self, report_schema: dict) -> dict:
        """Extract pages and visuals from report schema."""
        pages = {}
        
        for page in report_schema.get('pages', []):
            page_id = page.get('id')
            
            pages[page_id] = {
                'name': page.get('name', f'Page_{page_id}'),
                'visuals': page.get('charts', []),
            }
        
        return pages
    
    def _extract_formulas(self, report_schema: dict) -> list:
        """Extract custom formulas and calculated fields."""
        formulas = []
        
        for field in report_schema.get('calculatedFields', []):
            formulas.append({
                'name': field.get('name'),
                'expression': field.get('expression', ''),
                'looker_type': field.get('type'),
            })
        
        return formulas
    
    def _generate_migration_report(self, project_dir: Path, data_summary: dict,
                                  transform_summary: dict) -> None:
        """Generate detailed migration report."""
        
        report = {
            'migrationDate': datetime.now().isoformat(),
            'projectPath': str(project_dir),
            'dataSources': data_summary,
            'transformation': transform_summary,
            'notes': [
                'BigQuery queries have been converted to T-SQL format',
                'Google Sheets connections use ExcelOnline connector',
                'Review all formulas for DAX compatibility',
                'Update connection credentials before publishing',
            ],
        }
        
        report_file = project_dir / '.migration-report.json'
        report_file.write_text(json.dumps(report, indent=2))

        dashboard_file = project_dir / 'MIGRATION_DASHBOARD.html'
        self._generate_migration_dashboard_html(report, dashboard_file)
        
        self.logger.info(f"Migration report: {report_file}")
        self.logger.info(f"Migration dashboard: {dashboard_file}")

    def _generate_migration_dashboard_html(self, report: dict, output_file: Path) -> None:
        """Generate a lightweight HTML dashboard from migration report JSON."""
        ds = report.get('dataSources', {})
        tr = report.get('transformation', {})
        sources = ds.get('sources', {})

        source_rows = []
        for source_id, source in sources.items():
            source_rows.append(
                f"<tr><td>{escape(str(source_id))}</td>"
                f"<td>{escape(str(source.get('sourceType', '')))}</td>"
                f"<td>{escape(str(source.get('dataset', '')))}</td>"
                f"<td>{escape(str(source.get('table', '')))}</td></tr>"
            )

        if not source_rows:
            source_rows.append("<tr><td colspan='4'>No sources found</td></tr>")

        formula_fidelity = float(tr.get('formulaFidelity', 0.0))
        grade = 'A' if formula_fidelity >= 95 else 'B' if formula_fidelity >= 85 else 'C'

        html = f"""<!doctype html>
<html lang=\"en\"> 
<head>
    <meta charset=\"utf-8\"> 
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\"> 
    <title>Looker Studio Migration Dashboard</title>
    <style>
        body {{ font-family: Segoe UI, Arial, sans-serif; margin: 24px; background: #f6f8fb; color: #1f2937; }}
        h1 {{ margin: 0 0 6px; }}
        .muted {{ color: #6b7280; margin-bottom: 18px; }}
        .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 12px; margin: 16px 0 24px; }}
        .card {{ background: white; border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px; }}
        .label {{ color: #6b7280; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
        .value {{ font-size: 24px; font-weight: 700; margin-top: 4px; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border: 1px solid #e5e7eb; border-radius: 10px; overflow: hidden; }}
        th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #eef2f7; }}
        th {{ background: #f9fafb; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; color: #6b7280; }}
        .section-title {{ margin: 18px 0 10px; font-size: 16px; }}
        ul {{ background: white; border: 1px solid #e5e7eb; border-radius: 10px; padding: 14px 20px; }}
    </style>
</head>
<body>
    <h1>Looker Studio to Power BI Migration Dashboard</h1>
    <div class=\"muted\">Generated at {escape(str(report.get('migrationDate', '')))}</div>

    <div class=\"grid\">
        <div class=\"card\"><div class=\"label\">Total Sources</div><div class=\"value\">{int(ds.get('totalSources', 0))}</div></div>
        <div class=\"card\"><div class=\"label\">BigQuery Sources</div><div class=\"value\">{int(ds.get('bigQuerySources', 0))}</div></div>
        <div class=\"card\"><div class=\"label\">Google Sheets Sources</div><div class=\"value\">{int(ds.get('googleSheetsSources', 0))}</div></div>
        <div class=\"card\"><div class=\"label\">Controls</div><div class=\"value\">{int(tr.get('controls', 0))}</div></div>
        <div class=\"card\"><div class=\"label\">Formulas</div><div class=\"value\">{int(tr.get('formulas', 0))}</div></div>
        <div class=\"card\"><div class=\"label\">Fidelity</div><div class=\"value\">{formula_fidelity:.1f}% ({grade})</div></div>
    </div>

    <div class=\"section-title\">Sources</div>
    <table>
        <thead>
            <tr><th>Source Id</th><th>Type</th><th>Dataset</th><th>Table</th></tr>
        </thead>
        <tbody>
            {''.join(source_rows)}
        </tbody>
    </table>

    <div class=\"section-title\">Migration Notes</div>
    <ul>
        {''.join(f'<li>{escape(str(note))}</li>' for note in report.get('notes', []))}
    </ul>
</body>
</html>
"""

        output_file.write_text(html, encoding='utf-8')


# ── CLI argument parsing ─────────────────────────────────────────────

def parse_arguments() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Migrate Looker Studio reports to Power BI',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Migrate from JSON export
  python migrate.py report.json
  
  # Migrate from Looker Studio (requires auth)
  python migrate.py --report-id "abc123" --auth
  
  # Batch migration
  python migrate.py --batch --input-dir reports/ --output-dir output/
  
  # With assessment
  python migrate.py report.json --assess --verbose
        """
    )
    
    # Main input arguments
    parser.add_argument(
        'input',
        nargs='?',
        help='Path to Looker Studio JSON export or report file'
    )
    
    # Authentication & Source
    parser.add_argument(
        '--report-id',
        help='Looker Studio report ID (requires --auth)'
    )
    parser.add_argument(
        '--auth',
        nargs='?',
        const='interactive',
        choices=['interactive', 'service-account', 'oauth'],
        help='Setup Google API authentication (interactive, service-account, or oauth)'
    )
    parser.add_argument(
        '--credentials-file',
        help='Path to service account JSON for --auth service-account'
    )
    parser.add_argument(
        '--list-reports',
        action='store_true',
        help='List all accessible Looker Studio reports (requires --auth)'
    )
    
    # Batch operations
    parser.add_argument(
        '--batch',
        action='store_true',
        help='Batch migrate multiple reports'
    )
    parser.add_argument(
        '--input-dir',
        help='Input directory for batch migration'
    )
    
    # Output & Format
    parser.add_argument(
        '--output-dir',
        default='looker_migration_output',
        help='Output directory for .pbip projects (default: looker_migration_output)'
    )
    parser.add_argument(
        '--output-format',
        choices=['pbip', 'fabric'],
        default='pbip',
        help='Output format: pbip (Power BI) or fabric (Microsoft Fabric)'
    )
    
    # Assessment & Optimization
    parser.add_argument(
        '--assess',
        action='store_true',
        help='Run pre-migration assessment only (no generation)'
    )
    parser.add_argument(
        '--optimize-dax',
        action='store_true',
        help='Optimize generated DAX expressions'
    )
    
    # Deployment
    parser.add_argument(
        '--deploy',
        metavar='WORKSPACE_ID',
        help='Deploy to Power BI Service workspace'
    )
    parser.add_argument(
        '--tenant-id',
        help='Azure tenant ID (for deployment)'
    )
    parser.add_argument(
        '--client-id',
        help='Azure client/app ID (for deployment)'
    )
    parser.add_argument(
        '--client-secret',
        help='Azure client secret (for deployment)'
    )
    
    # Other options
    parser.add_argument(
        '--wizard',
        action='store_true',
        help='Interactive wizard mode'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Verbose logging output'
    )
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    return parser.parse_args()


# ── Main entry point ────────────────────────────────────────────────

def main() -> int:
    """Main entry point."""
    try:
        args = parse_arguments()
        logger_instance = setup_logging(args.verbose)
        
        # Handle authentication setup
        if args.auth:
            return _handle_auth_setup(args, logger_instance)
        
        # Handle listing reports
        if args.list_reports:
            return _handle_list_reports(args, logger_instance)
        
        # Handle Looker Studio API extraction
        if args.report_id:
            return _handle_looker_studio_extraction(args, logger_instance)
        
        # Validate arguments
        if not args.input and not args.batch and not args.wizard:
            print("Error: Provide input file, --report-id, --batch, or --wizard")
            return ExitCode.GENERAL_ERROR
        
        # Initialize migrator
        migrator = LookerStudioMigrator(
            output_dir=args.output_dir,
            verbose=args.verbose
        )
        
        # Handle batch migration
        if args.batch:
            if not args.input_dir:
                print("Error: --batch requires --input-dir")
                return ExitCode.GENERAL_ERROR
            
            input_path = Path(args.input_dir)
            json_files = list(input_path.glob('*.json'))
            
            logger_instance.info(f"Found {len(json_files)} reports to migrate")
            
            failed = 0
            for json_file in json_files:
                try:
                    migrator.migrate_from_json(str(json_file))
                except Exception as e:
                    logger_instance.error(f"Failed to migrate {json_file}: {e}")
                    failed += 1
            
            if failed > 0:
                return ExitCode.BATCH_PARTIAL_FAIL
            
            return ExitCode.SUCCESS
        
        # Handle single migration
        if args.input:
            try:
                output = migrator.migrate_from_json(args.input)
                print(f"\n✓ Migration complete!\nOutput: {output}")
                return ExitCode.SUCCESS
            except FileNotFoundError:
                return ExitCode.FILE_NOT_FOUND
            except Exception as e:
                logger_instance.error(f"Migration failed: {e}")
                return ExitCode.GENERATION_FAILED
        
        # Handle wizard
        if args.wizard:
            logger_instance.info("Interactive wizard not yet implemented")
            return ExitCode.GENERAL_ERROR
        
        return ExitCode.SUCCESS
        
    except KeyboardInterrupt:
        print("\n✗ Migration interrupted by user")
        return ExitCode.KEYBOARD_INTERRUPT
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return ExitCode.GENERAL_ERROR


def _handle_auth_setup(args, logger_instance) -> int:
    """Handle Google API authentication setup."""
    try:
        auth_handler = GoogleAuthHandler()
        
        # Check if already configured
        is_configured, auth_type = auth_handler.is_configured()
        if is_configured and args.auth == 'interactive':
            print(f"✓ Already configured with {auth_type} auth")
            return ExitCode.SUCCESS
        
        if args.auth == 'interactive':
            if auth_handler.interactive_setup():
                print("\n✓ Authentication setup complete!")
                return ExitCode.SUCCESS
            else:
                return ExitCode.AUTH_FAILED
        
        elif args.auth == 'service-account':
            if not args.credentials_file:
                print("Error: --credentials-file required for service-account auth")
                return ExitCode.GENERAL_ERROR
            
            if auth_handler.setup_service_account(args.credentials_file):
                print("\n✓ Service account authentication setup complete!")
                return ExitCode.SUCCESS
            else:
                return ExitCode.AUTH_FAILED
        
        else:
            print("Error: Invalid auth method")
            return ExitCode.GENERAL_ERROR
    
    except Exception as e:
        logger_instance.error(f"Authentication setup failed: {e}")
        return ExitCode.AUTH_FAILED


def _handle_list_reports(args, logger_instance) -> int:
    """Handle listing accessible Looker Studio reports."""
    try:
        auth_handler = GoogleAuthHandler()
        is_configured, auth_type = auth_handler.is_configured()
        
        if not is_configured:
            print("Error: No authentication configured. Run: python migrate.py --auth")
            return ExitCode.AUTH_FAILED
        
        creds_manager = CredentialsManager(auth_handler)
        credentials = creds_manager.get_credentials(auth_type)
        
        if credentials is None:
            return ExitCode.AUTH_FAILED
        
        logger_instance.info("Fetching accessible reports...")
        
        extractor = LookerStudioProgrammaticExtractor(credentials)
        reports = extractor.extract_all_accessible()
        
        if not reports:
            print("No accessible reports found")
            return ExitCode.SUCCESS
        
        print(f"\n✓ Found {len(reports)} reports:\n")
        for report_id, report in reports.items():
            preview = extractor.get_report_preview(report_id)
            print(f"  {report_id}")
            print(f"    Title: {preview.get('title', 'Unknown')}")
            print(f"    Sources: {preview.get('dataSources', 0)}, Pages: {preview.get('pages', 0)}")
        
        return ExitCode.SUCCESS
    
    except Exception as e:
        logger_instance.error(f"Failed to list reports: {e}")
        return ExitCode.GENERAL_ERROR


def _handle_looker_studio_extraction(args, logger_instance) -> int:
    """Handle extraction from Looker Studio API."""
    try:
        auth_handler = GoogleAuthHandler()
        is_configured, auth_type = auth_handler.is_configured()
        
        if not is_configured:
            print("Error: No authentication configured. Run: python migrate.py --auth")
            return ExitCode.AUTH_FAILED
        
        creds_manager = CredentialsManager(auth_handler)
        credentials = creds_manager.get_credentials(auth_type)
        
        if credentials is None:
            return ExitCode.AUTH_FAILED
        
        logger_instance.info(f"Extracting report: {args.report_id}")
        
        # Extract report from Looker Studio API
        extractor = LookerStudioProgrammaticExtractor(credentials)
        report = extractor.extract_report(args.report_id)
        
        if report is None:
            logger_instance.error(f"Failed to extract report: {args.report_id}")
            return ExitCode.EXTRACTION_FAILED
        
        # Save JSON export
        export_dir = Path(args.output_dir) / 'exports'
        export_dir.mkdir(parents=True, exist_ok=True)
        
        report_name = report.get('title', f'Report_{args.report_id}')
        report_name = report_name.replace(' ', '_')
        export_file = export_dir / f"{report_name}.json"
        
        if extractor.client.export_report_json(args.report_id, str(export_file)):
            logger_instance.info(f"Report exported to: {export_file}")
        else:
            logger_instance.warning("Export to JSON failed, using in-memory report")
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
        
        # Now migrate the extracted report
        migrator = LookerStudioMigrator(
            output_dir=args.output_dir,
            verbose=args.verbose
        )
        
        output = migrator.migrate_from_json(str(export_file))
        print(f"\n✓ Migration complete!\nOutput: {output}")
        
        return ExitCode.SUCCESS
    
    except Exception as e:
        logger_instance.error(f"Looker Studio extraction failed: {e}", exc_info=True)
        return ExitCode.EXTRACTION_FAILED


if __name__ == '__main__':
    sys.exit(main())
