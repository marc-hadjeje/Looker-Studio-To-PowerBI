#!/usr/bin/env python3
"""
Generate sample Looker Studio reports with realistic data structures.
These can be used for testing the migration pipeline.
"""

import argparse
import copy
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def load_json_file(file_path: str) -> Dict[str, Any]:
    with open(file_path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def slugify(value: str) -> str:
    value = re.sub(r'[^a-zA-Z0-9]+', '_', value.strip().lower())
    return value.strip('_') or 'report'


def normalize_columns(raw_columns: Any) -> List[Dict[str, Any]]:
    columns: List[Dict[str, Any]] = []

    if not raw_columns:
        return columns

    for column in raw_columns:
        if isinstance(column, str):
            columns.append({'name': column, 'type': ''})
            continue

        if isinstance(column, dict):
            columns.append(
                {
                    'name': column.get('name') or column.get('columnName') or column.get('field') or '',
                    'type': column.get('type') or column.get('dataType') or '',
                }
            )

    return [column for column in columns if column.get('name')]


def normalize_table_definitions(schema: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    schema_tables = schema.get('tables') or []
    if not schema_tables and schema.get('datasets'):
        for dataset in schema.get('datasets', []):
            for table in dataset.get('tables', []):
                table = copy.deepcopy(table)
                table.setdefault('datasetId', dataset.get('datasetId') or dataset.get('name') or '')
                table.setdefault('projectId', dataset.get('projectId') or schema.get('projectId') or '')
                schema_tables.append(table)

    if not schema_tables and schema.get('table'):
        schema_tables = [schema]

    normalized_tables: List[Dict[str, Any]] = []
    for table in schema_tables:
        normalized_tables.append(
            {
                'projectId': table.get('projectId') or schema.get('projectId') or '',
                'datasetId': table.get('datasetId') or table.get('dataset') or schema.get('defaultDatasetId') or schema.get('datasetId') or '',
                'table': table.get('table') or table.get('tableId') or table.get('name') or '',
                'name': table.get('name') or table.get('title') or table.get('table') or table.get('tableId') or 'Unknown Table',
                'query': table.get('query') or '',
                'columns': normalize_columns(table.get('columns') or table.get('schema') or table.get('fields')),
                'preferredReport': table.get('preferredReport') or table.get('reportType') or '',
            }
        )

    return schema, [table for table in normalized_tables if table.get('table')]


def infer_profile(table_name: str, columns: List[Dict[str, Any]], preferred_report: str = '') -> str:
    if preferred_report:
        return preferred_report.lower()

    tokens = ' '.join([table_name] + [column.get('name', '') for column in columns]).lower()

    if any(term in tokens for term in ['campaign', 'marketing', 'ads', 'ad_', 'click', 'impression', 'conversion']):
        return 'marketing'
    if any(term in tokens for term in ['customer', 'user', 'segment', 'retention', 'churn', 'lifetime']):
        return 'customer'
    if any(term in tokens for term in ['finance', 'budget', 'invoice', 'payment', 'expense', 'revenue', 'profit']):
        return 'finance'
    if any(term in tokens for term in ['sale', 'order', 'transaction', 'product', 'margin', 'amount']):
        return 'sales'
    return 'generic'


def infer_date_column(columns: List[Dict[str, Any]]) -> Optional[str]:
    candidates = ('date', 'time', 'timestamp', 'month', 'year', 'week')
    for column in columns:
        column_name = column.get('name', '').lower()
        if any(token in column_name for token in candidates):
            return column.get('name')
    return None


def infer_dimension_column(columns: List[Dict[str, Any]]) -> Optional[str]:
    excluded_tokens = ('date', 'time', 'amount', 'value', 'cost', 'revenue', 'price', 'budget', 'margin', 'count', 'qty', 'quantity')
    for column in columns:
        column_name = column.get('name', '')
        lower_name = column_name.lower()
        if not any(token in lower_name for token in excluded_tokens):
            return column_name
    return columns[0].get('name') if columns else None


def infer_metric_column(columns: List[Dict[str, Any]]) -> Optional[str]:
    preferred_tokens = ('amount', 'revenue', 'sales', 'value', 'cost', 'price', 'budget', 'profit', 'margin', 'score', 'click', 'impression', 'conversion', 'order')
    date_tokens = ('date', 'time', 'timestamp')
    numeric_types = ('int', 'float', 'numeric', 'bignumeric', 'number', 'decimal', 'double')

    def is_numeric(column: Dict[str, Any]) -> bool:
        column_type = (column.get('type') or '').lower()
        # When the type is unknown, don't exclude the column on type grounds.
        return any(token in column_type for token in numeric_types) if column_type else True

    # First pass: a preferred metric token on a numeric, non-date column.
    for column in columns:
        lower_name = column.get('name', '').lower()
        if any(token in lower_name for token in date_tokens):
            continue
        if not is_numeric(column):
            continue
        if any(token in lower_name for token in preferred_tokens):
            return column.get('name')

    # Fallback: first numeric, non-date column.
    for column in columns:
        lower_name = column.get('name', '').lower()
        if any(token in lower_name for token in date_tokens):
            continue
        if is_numeric(column):
            return column.get('name')

    return None


def generate_sample_report(report_template: dict, output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    report_template['generatedAt'] = datetime.now().isoformat()
    report_template['version'] = '2.0'

    with open(output_path, 'w', encoding='utf-8') as handle:
        json.dump(report_template, handle, indent=2, ensure_ascii=False)

    print(f"✓ Generated: {output_path}")


def get_sales_dashboard_template() -> dict:
    template_path = Path(__file__).parent / 'sample_looker_reports' / 'sales_dashboard.json'
    if template_path.exists():
        return load_json_file(str(template_path))
    return {}


def get_marketing_report_template() -> dict:
    template_path = Path(__file__).parent / 'sample_looker_reports' / 'marketing_report.json'
    if template_path.exists():
        return load_json_file(str(template_path))
    return {}


def get_customer_analytics_template() -> dict:
    template_path = Path(__file__).parent / 'sample_looker_reports' / 'customer_analytics.json'
    if template_path.exists():
        return load_json_file(str(template_path))
    return {}


def get_finance_summary_template() -> dict:
    template_path = Path(__file__).parent / 'sample_looker_reports' / 'finance_summary.json'
    if template_path.exists():
        return load_json_file(str(template_path))
    return {}


def customize_report(template: dict, project_id: str, dataset_id: str) -> dict:
    report = copy.deepcopy(template)

    if 'dataSources' in report:
        for data_source in report['dataSources']:
            if data_source.get('sourceType') == 'BigQuery':
                data_source.setdefault('configuration', {})['projectId'] = project_id
                if dataset_id:
                    data_source['configuration']['datasetId'] = dataset_id

    return report


def build_adaptive_report(table: Dict[str, Any], default_project_id: str, default_dataset_id: str) -> Dict[str, Any]:
    table_name = table['table']
    report_name = table.get('name') or table_name
    columns = table.get('columns', [])
    profile = infer_profile(table_name, columns, table.get('preferredReport', ''))
    date_column = infer_date_column(columns)
    dimension_column = infer_dimension_column(columns)
    metric_column = infer_metric_column(columns)

    source_id = f"ds_{slugify(table_name)}"
    dataset_id = table.get('datasetId') or default_dataset_id
    project_id = table.get('projectId') or default_project_id
    table_query = table.get('query') or (f"SELECT * FROM `{project_id}.{dataset_id}.{table_name}`" if project_id and dataset_id else f"SELECT * FROM `{table_name}`")

    scorecard_metric = f"SUM({metric_column})" if metric_column else 'COUNT(*)'
    table_metric = metric_column or 'COUNT(*)'
    trend_metric = f"SUM({metric_column})" if metric_column else 'COUNT(*)'

    visuals = [
        {
            'id': f'visual_{slugify(table_name)}_scorecard_1',
            'name': 'Total Records',
            'type': 'Scorecard',
            'position': {'row': 0, 'column': 0, 'width': 1, 'height': 1},
            'dataSourceId': source_id,
            'configuration': {'metric': 'COUNT(*)', 'dimensions': []},
        },
        {
            'id': f'visual_{slugify(table_name)}_scorecard_2',
            'name': 'Primary Metric',
            'type': 'Scorecard',
            'position': {'row': 0, 'column': 1, 'width': 1, 'height': 1},
            'dataSourceId': source_id,
            'configuration': {'metric': scorecard_metric, 'dimensions': []},
        },
    ]

    if date_column:
        visuals.append(
            {
                'id': f'visual_{slugify(table_name)}_trend',
                'name': f'{report_name} Trend',
                'type': 'LineChart',
                'position': {'row': 1, 'column': 0, 'width': 2, 'height': 1},
                'dataSourceId': source_id,
                'configuration': {'xAxis': f'DATE_TRUNC({date_column}, MONTH)', 'yAxis': trend_metric, 'legend': False},
            }
        )

    if dimension_column:
        visuals.append(
            {
                'id': f'visual_{slugify(table_name)}_breakdown',
                'name': f'{report_name} by {dimension_column}',
                'type': 'ColumnChart',
                'position': {'row': 1, 'column': 2, 'width': 2, 'height': 1},
                'dataSourceId': source_id,
                'configuration': {'xAxis': dimension_column, 'yAxis': trend_metric, 'sort': 'descending'},
            }
        )

    visuals.append(
        {
            'id': f'visual_{slugify(table_name)}_table',
            'name': f'{report_name} Details',
            'type': 'Table',
            'position': {'row': 2, 'column': 0, 'width': 4, 'height': 1},
            'dataSourceId': source_id,
            'configuration': {
                'dimensions': [value for value in [dimension_column, date_column] if value],
                'metrics': [table_metric],
                'sort': f'{table_metric} DESC',
                'limit': 20,
            },
        }
    )

    report = {
        'id': slugify(table_name),
        'title': f'{report_name} Looker Studio Example',
        'description': f'Adaptive Looker Studio sample generated from {table_name} ({profile} profile)',
        'dataSources': [
            {
                'id': source_id,
                'sourceType': 'BigQuery',
                'name': report_name,
                'query': table_query,
                'configuration': {
                    'projectId': project_id,
                    'datasetId': dataset_id,
                    'table': table_name,
                    'tableId': table_name,
                    'query': table_query,
                },
            }
        ],
        'parameterControls': [],
        'pages': [
            {
                'id': f'page_{slugify(table_name)}_overview',
                'name': 'Overview',
                'layout': {'rows': 3, 'columns': 4},
                'visuals': visuals,
            }
        ],
        'calculatedFields': [],
    }

    if date_column:
        report['parameterControls'].append(
            {
                'id': f'ctrl_{slugify(table_name)}_date_range',
                'name': 'Date Range',
                'type': 'DateRange',
                'defaultValue': {'startDate': '2024-01-01', 'endDate': '2024-12-31'},
                'linkedField': date_column,
            }
        )

    if dimension_column:
        report['parameterControls'].append(
            {
                'id': f'ctrl_{slugify(table_name)}_dimension',
                'name': dimension_column,
                'type': 'Dropdown',
                'options': [],
                'multiSelect': True,
                'linkedField': dimension_column,
            }
        )

    if metric_column:
        report['calculatedFields'].append(
            {
                'id': f'calc_{slugify(table_name)}_metric',
                'name': f'{metric_column} Total',
                'formula': f'SUM({metric_column})',
                'description': f'Aggregated metric for {metric_column}',
            }
        )

    report['generatedFromTableSchema'] = {
        'profile': profile,
        'dateColumn': date_column,
        'dimensionColumn': dimension_column,
        'metricColumn': metric_column,
        'columns': [column.get('name') for column in columns],
    }

    return report


def generate_reports_from_schema(schema_file: str, project_id: str, dataset_id: str, output_dir: Path) -> None:
    schema = load_json_file(schema_file)
    _, tables = normalize_table_definitions(schema)

    if not tables:
        print(f'No tables found in schema file: {schema_file}')
        return

    print(f"\n📊 Generating adaptive Looker Studio reports from schema")
    print(f"   Schema file: {schema_file}")
    print(f"   Tables found: {len(tables)}")
    print(f"   Output: {output_dir}\n")

    for table in tables:
        report = build_adaptive_report(table, project_id, dataset_id)
        output_path = output_dir / f"{slugify(table['table'])}.json"
        generate_sample_report(report, str(output_path))

    print(f"\n✅ Adaptive reports generated successfully!")
    print(f"\nNext steps:")
    print(f"1. Replace schema hints with your actual BigQuery tables and columns")
    print(f"2. Migrate reports: python migrate.py --batch --input-dir {output_dir}")
    print(f"3. Fine-tune visuals if a table needs a custom layout")


def generate_prebuilt_reports(project_id: str, dataset_id: str, output_dir: Path, selected_reports: List[str]) -> None:
    generate_all = not selected_reports or 'all' in selected_reports

    print(f"\n📊 Generating sample Looker Studio reports")
    print(f"   Project ID: {project_id}")
    print(f"   Output: {output_dir}\n")

    report_specs = [
        ('sales', get_sales_dashboard_template, 'sales_dashboard.json'),
        ('marketing', get_marketing_report_template, 'marketing_report.json'),
        ('customer', get_customer_analytics_template, 'customer_analytics.json'),
        ('finance', get_finance_summary_template, 'finance_summary.json'),
    ]

    for report_key, template_loader, file_name in report_specs:
        if generate_all or report_key in selected_reports:
            template = template_loader()
            if template:
                report = customize_report(template, project_id, dataset_id)
                generate_sample_report(report, str(output_dir / file_name))

    print(f"\n✅ All reports generated successfully!")
    print(f"\nNext steps:")
    print(f"1. Update data source configurations with your actual BigQuery tables")
    print(f"2. Migrate reports: python migrate.py --batch --input-dir {output_dir}")
    print(f"3. Open generated .pbip projects in Power BI Desktop")


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate sample Looker Studio reports')
    parser.add_argument('--project-id', default='your-gcp-project', help='GCP project ID (default: your-gcp-project)')
    parser.add_argument('--dataset-id', default='', help='BigQuery dataset ID (optional)')
    parser.add_argument('--output-dir', default='./looker_reports/', help='Output directory for reports (default: ./looker_reports/)')
    parser.add_argument('--schema-file', default='', help='Adaptive BigQuery schema file (JSON)')
    parser.add_argument('--all', action='store_true', help='Generate all sample reports (default: true if no specific report specified)')
    parser.add_argument('--sales', action='store_true', help='Generate sales dashboard')
    parser.add_argument('--marketing', action='store_true', help='Generate marketing report')
    parser.add_argument('--customer', action='store_true', help='Generate customer analytics')
    parser.add_argument('--finance', action='store_true', help='Generate finance summary')

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.schema_file:
        generate_reports_from_schema(args.schema_file, args.project_id, args.dataset_id, output_dir)
        return

    selected_reports: List[str] = []
    if args.sales:
        selected_reports.append('sales')
    if args.marketing:
        selected_reports.append('marketing')
    if args.customer:
        selected_reports.append('customer')
    if args.finance:
        selected_reports.append('finance')
    if args.all or not selected_reports:
        selected_reports.append('all')

    generate_prebuilt_reports(args.project_id, args.dataset_id, output_dir, selected_reports)


if __name__ == '__main__':
    main()
