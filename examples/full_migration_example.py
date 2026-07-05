#!/usr/bin/env python3
"""
Example: Complete Looker Studio to Power BI Migration Workflow

This script demonstrates the full migration process using the API extraction
and programmatic transformation capabilities.

Usage:
    python examples/full_migration_example.py
    python examples/full_migration_example.py --report-id "abc123"
"""

import sys
import json
import argparse
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from looker_import.auth_handler import GoogleAuthHandler, CredentialsManager
from looker_import.looker_api_extractor import LookerStudioProgrammaticExtractor
from looker_import.extractor import LookerStudioExtractor
from looker_import.transformer import LookerStudioTransformer
from looker_import.generator import PBIPGenerator
from looker_import.sheets_connector import CombinedDataSourceManager


def example_1_auth_setup():
    """Example 1: Setup Google API authentication."""
    print("\n" + "="*60)
    print("EXAMPLE 1: Setup Google API Authentication")
    print("="*60 + "\n")
    
    auth_handler = GoogleAuthHandler()
    
    # Check if already configured
    is_configured, auth_type = auth_handler.is_configured()
    
    if is_configured:
        print(f"✓ Already configured with {auth_type} authentication")
    else:
        print("Setting up authentication...")
        if auth_handler.interactive_setup():
            print("✓ Authentication setup complete!")
        else:
            print("✗ Authentication setup failed")


def example_2_list_reports():
    """Example 2: List accessible Looker Studio reports."""
    print("\n" + "="*60)
    print("EXAMPLE 2: List Accessible Reports")
    print("="*60 + "\n")
    
    try:
        auth_handler = GoogleAuthHandler()
        is_configured, auth_type = auth_handler.is_configured()
        
        if not is_configured:
            print("✗ No authentication configured")
            return
        
        creds_manager = CredentialsManager(auth_handler)
        credentials = creds_manager.get_credentials(auth_type)
        
        extractor = LookerStudioProgrammaticExtractor(credentials)
        reports = extractor.extract_all_accessible()
        
        print(f"Found {len(reports)} reports:\n")
        
        for report_id, report in reports.items():
            preview = extractor.get_report_preview(report_id)
            print(f"  {report_id}")
            print(f"    Title: {preview.get('title', 'Unknown')}")
            print(f"    Owner: {preview.get('owner', 'Unknown')}")
            print(f"    Data Sources: {preview.get('dataSources', 0)}")
            print(f"    Pages: {preview.get('pages', 0)}")
            print()
    
    except Exception as e:
        print(f"✗ Failed to list reports: {e}")


def example_3_extract_report(report_id: str):
    """Example 3: Extract a report from Looker Studio API."""
    print("\n" + "="*60)
    print(f"EXAMPLE 3: Extract Report {report_id}")
    print("="*60 + "\n")
    
    try:
        auth_handler = GoogleAuthHandler()
        is_configured, auth_type = auth_handler.is_configured()
        
        if not is_configured:
            print("✗ No authentication configured")
            return None
        
        creds_manager = CredentialsManager(auth_handler)
        credentials = creds_manager.get_credentials(auth_type)
        
        extractor = LookerStudioProgrammaticExtractor(credentials)
        report = extractor.extract_report(report_id)
        
        if report:
            # Save to file
            export_dir = Path("examples/exports")
            export_dir.mkdir(parents=True, exist_ok=True)
            
            report_name = report.get('title', f'report_{report_id}')
            report_name = report_name.replace(' ', '_')
            
            export_file = export_dir / f"{report_name}.json"
            
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(report, f, indent=2)
            
            print(f"✓ Report extracted and saved to: {export_file}")
            return str(export_file)
        else:
            print(f"✗ Failed to extract report {report_id}")
            return None
    
    except Exception as e:
        print(f"✗ Extraction failed: {e}")
        return None


def example_4_transform_report(json_path: str):
    """Example 4: Transform extracted report to Power BI format."""
    print("\n" + "="*60)
    print("EXAMPLE 4: Transform Report")
    print("="*60 + "\n")
    
    try:
        # Load extracted report
        with open(json_path, 'r', encoding='utf-8') as f:
            report_schema = json.load(f)
        
        print(f"Loaded report: {report_schema.get('title', 'Unknown')}")
        
        # Extract components
        extractor = LookerStudioExtractor()
        extractor.report_schema = report_schema
        
        data_sources = extractor.extract_data_sources()
        controls = extractor.extract_controls()
        pages = extractor.extract_pages()
        formulas = extractor.extract_formulas()
        
        print(f"\nExtracted:")
        print(f"  - {len(data_sources)} data sources")
        print(f"  - {len(controls)} controls")
        print(f"  - {len(pages)} pages")
        print(f"  - {len(formulas)} formulas")
        
        # Transform to Power BI
        transformer = LookerStudioTransformer()
        
        transformed_sources = transformer.transform_data_sources(data_sources)
        transformed_controls = transformer.transform_controls(controls)
        transformed_formulas = transformer.transform_formulas(formulas)
        transformed_pages = transformer.transform_pages(pages)
        
        summary = transformer.get_migration_summary()
        
        print(f"\nTransformed:")
        print(f"  - Average formula fidelity: {summary['formulaFidelity']:.1f}%")
        print(f"  - Ready for Power BI generation")
        
        return {
            'sources': transformed_sources,
            'controls': transformed_controls,
            'formulas': transformed_formulas,
            'pages': transformed_pages,
        }
    
    except Exception as e:
        print(f"✗ Transformation failed: {e}")
        return None


def example_5_generate_pbip(json_path: str):
    """Example 5: Generate Power BI .pbip project."""
    print("\n" + "="*60)
    print("EXAMPLE 5: Generate Power BI Project")
    print("="*60 + "\n")
    
    try:
        # Load report
        with open(json_path, 'r', encoding='utf-8') as f:
            report_schema = json.load(f)
        
        report_title = report_schema.get('title', 'Looker_Report')
        project_name = report_title.replace(' ', '_')
        
        print(f"Creating project: {project_name}")
        
        # Transform
        extractor = LookerStudioExtractor()
        extractor.report_schema = report_schema
        
        data_sources = extractor.extract_data_sources()
        controls = extractor.extract_controls()
        pages = extractor.extract_pages()
        
        transformer = LookerStudioTransformer()
        transformed_sources = transformer.transform_data_sources(data_sources)
        transformed_controls = transformer.transform_controls(controls)
        transformed_pages = transformer.transform_pages(pages)
        
        # Generate
        generator = PBIPGenerator('examples/output', project_name)
        project_dir = generator.create_project_structure()
        
        generator.generate_model(
            data_sources=transformed_sources,
            measures=[],
            relationships=[]
        )
        
        generator.generate_report(
            pages=transformed_pages,
            controls=transformed_controls
        )
        
        generator.create_config_file({
            'sourceReport': report_title,
            'dataSourcesCount': len(data_sources),
            'tablesCount': len(data_sources),
            'measuresCount': 0,
            'createdDate': json.dumps(None),  # Use timestamp
        })
        
        generator.create_readme()
        
        print(f"\n✓ Power BI project generated!")
        print(f"  Location: {project_dir}")
        print(f"\nNext steps:")
        print(f"  1. Open in Power BI Desktop (December 2025+)")
        print(f"  2. Configure BigQuery and Google Sheets connections")
        print(f"  3. Test data refresh")
        print(f"  4. Publish to Power BI Service")
        
        return str(project_dir)
    
    except Exception as e:
        print(f"✗ Generation failed: {e}")
        return None


def example_6_full_workflow():
    """Example 6: Complete workflow from extraction to generation."""
    print("\n" + "="*60)
    print("EXAMPLE 6: Complete Workflow")
    print("="*60 + "\n")
    
    try:
        # Step 1: Auth
        print("Step 1: Checking authentication...")
        auth_handler = GoogleAuthHandler()
        is_configured, auth_type = auth_handler.is_configured()
        
        if not is_configured:
            print("  → Run: python examples/full_migration_example.py --auth")
            return
        
        print(f"  ✓ Using {auth_type} authentication")
        
        # Step 2: Get credentials
        print("\nStep 2: Getting credentials...")
        creds_manager = CredentialsManager(auth_handler)
        credentials = creds_manager.get_credentials(auth_type)
        print("  ✓ Credentials obtained")
        
        # Step 3: List reports
        print("\nStep 3: Fetching reports...")
        extractor = LookerStudioProgrammaticExtractor(credentials)
        reports = extractor.extract_all_accessible()
        print(f"  ✓ Found {len(reports)} reports")
        
        if not reports:
            print("  ✗ No reports found")
            return
        
        # Step 4: Migrate first report
        print("\nStep 4: Migrating first report...")
        first_report_id = list(reports.keys())[0]
        
        # Extract
        report = extractor.extract_report(first_report_id)
        
        # Save
        export_dir = Path("examples/exports")
        export_dir.mkdir(parents=True, exist_ok=True)
        
        report_name = report.get('title', f'report_{first_report_id}')
        report_name = report_name.replace(' ', '_')
        export_file = export_dir / f"{report_name}.json"
        
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2)
        
        print(f"  ✓ Report saved: {export_file}")
        
        # Step 5: Generate Power BI
        print("\nStep 5: Generating Power BI project...")
        project_dir = example_5_generate_pbip(str(export_file))
        
        print("\n✓ Complete workflow finished!")
        if project_dir:
            print(f"  Output: {project_dir}")
    
    except Exception as e:
        print(f"✗ Workflow failed: {e}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Looker Studio to Power BI Migration Examples'
    )
    
    parser.add_argument(
        '--auth',
        action='store_true',
        help='Run authentication setup'
    )
    parser.add_argument(
        '--list',
        action='store_true',
        help='List accessible reports'
    )
    parser.add_argument(
        '--extract',
        metavar='REPORT_ID',
        help='Extract a specific report'
    )
    parser.add_argument(
        '--full',
        action='store_true',
        help='Run complete workflow'
    )
    
    args = parser.parse_args()
    
    if args.auth:
        example_1_auth_setup()
    elif args.list:
        example_2_list_reports()
    elif args.extract:
        example_3_extract_report(args.extract)
    elif args.full:
        example_6_full_workflow()
    else:
        # Show all examples
        print("\nLooker Studio to Power BI Migration - Examples\n")
        print("Usage:")
        print("  python examples/full_migration_example.py --auth      # Setup auth")
        print("  python examples/full_migration_example.py --list      # List reports")
        print("  python examples/full_migration_example.py --extract <ID>  # Extract report")
        print("  python examples/full_migration_example.py --full      # Run full workflow")
