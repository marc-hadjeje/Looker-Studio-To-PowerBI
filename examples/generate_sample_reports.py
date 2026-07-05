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
import struct
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def load_json_file(file_path: str) -> Dict[str, Any]:
    with open(file_path, 'r', encoding='utf-8') as handle:
        return json.load(handle)


def slugify(value: str) -> str:
    value = re.sub(r'[^a-zA-Z0-9]+', '_', value.strip().lower())
    return value.strip('_') or 'report'


def get_image_size(image_path: str) -> Optional[Tuple[int, int]]:
    """Get image dimensions from common formats (PNG/JPEG) without extra dependencies."""
    path = Path(image_path)
    if not path.exists() or not path.is_file():
        return None

    with open(path, 'rb') as handle:
        header = handle.read(24)

    # PNG: width/height in IHDR (bytes 16..24)
    if header.startswith(b'\x89PNG\r\n\x1a\n') and len(header) >= 24:
        width, height = struct.unpack('>II', header[16:24])
        return int(width), int(height)

    # JPEG fallback: use Pillow if available
    if path.suffix.lower() in {'.jpg', '.jpeg'}:
        try:
            from PIL import Image  # type: ignore
            with Image.open(path) as image:
                return int(image.width), int(image.height)
        except Exception:
            return None

    return None


def infer_layout_profile_from_screenshot(screenshot_file: str) -> Tuple[str, Optional[Tuple[int, int]]]:
    """Infer a coarse layout profile from screenshot dimensions."""
    size = get_image_size(screenshot_file)
    if not size:
        return 'desktop', None

    width, height = size
    if width <= 0 or height <= 0:
        return 'desktop', None

    ratio = width / height
    if ratio < 0.9:
        return 'mobile', size
    if ratio < 1.5:
        return 'tablet', size
    return 'desktop', size


def detect_visual_blocks_from_screenshot(
    screenshot_file: str,
    max_blocks: int = 5,
) -> List[Dict[str, float]]:
    """
    Detect likely visual blocks in a dashboard screenshot.

    Returns a list of normalized rectangles: [{x,y,w,h}] where values are in [0,1].
    Falls back to empty list if Pillow is unavailable or analysis fails.
    """
    try:
        from PIL import Image  # type: ignore
    except Exception:
        return []


def export_detection_debug_artifacts(
    screenshot_file: str,
    blocks: List[Dict[str, float]],
    output_dir: Path,
) -> Optional[Path]:
    """Export debug artifacts for visual block detection.

    Creates:
    - Annotated image with detected blocks
    - JSON metadata with normalized block coordinates
    """
    try:
        from PIL import Image, ImageDraw  # type: ignore
    except Exception:
        return None

    try:
        source = Path(screenshot_file)
        if not source.exists() or not source.is_file():
            return None

        debug_dir = output_dir / '_debug'
        debug_dir.mkdir(parents=True, exist_ok=True)

        with Image.open(source) as image:
            canvas = image.convert('RGB')
            draw = ImageDraw.Draw(canvas)
            width, height = canvas.size

            for index, block in enumerate(blocks):
                x0 = int(block['x'] * width)
                y0 = int(block['y'] * height)
                x1 = int((block['x'] + block['w']) * width)
                y1 = int((block['y'] + block['h']) * height)
                draw.rectangle([(x0, y0), (x1, y1)], outline=(255, 64, 64), width=3)
                draw.text((x0 + 4, max(0, y0 - 16)), f"#{index + 1}", fill=(255, 64, 64))

            annotated_path = debug_dir / f"{source.stem}.annotated{source.suffix}"
            canvas.save(annotated_path)

        metadata_path = debug_dir / f"{source.stem}.blocks.json"
        with open(metadata_path, 'w', encoding='utf-8') as handle:
            json.dump({'screenshot': str(source), 'blocks': blocks}, handle, indent=2)

        return annotated_path

    except Exception:
        return None

    try:
        with Image.open(screenshot_file) as image:
            gray = image.convert('L')
            width, height = gray.size
            if width < 40 or height < 40:
                return []

            # Downscale for cheap connected-component analysis.
            max_dim = 320
            scale = min(1.0, max_dim / float(max(width, height)))
            if scale < 1.0:
                small_w = max(40, int(width * scale))
                small_h = max(40, int(height * scale))
                gray = gray.resize((small_w, small_h))

            w, h = gray.size
            pix = list(gray.getdata())

            # Estimate background luminance from borders.
            border_values: List[int] = []
            for x in range(w):
                border_values.append(pix[x])
                border_values.append(pix[(h - 1) * w + x])
            for y in range(h):
                border_values.append(pix[y * w])
                border_values.append(pix[y * w + (w - 1)])

            border_values.sort()
            bg = border_values[len(border_values) // 2]

            # Create foreground mask where luminance differs enough from background.
            delta = 18
            fg = [abs(v - bg) > delta for v in pix]

            visited = [False] * (w * h)
            components: List[Tuple[int, int, int, int, int]] = []  # x0,y0,x1,y1,area
            min_area = max(35, int((w * h) * 0.006))

            # 4-neighbor flood fill.
            for y in range(h):
                row_offset = y * w
                for x in range(w):
                    idx = row_offset + x
                    if visited[idx] or not fg[idx]:
                        continue

                    stack = [idx]
                    visited[idx] = True
                    x0 = x1 = x
                    y0 = y1 = y
                    area = 0

                    while stack:
                        cur = stack.pop()
                        cx = cur % w
                        cy = cur // w
                        area += 1
                        if cx < x0:
                            x0 = cx
                        if cx > x1:
                            x1 = cx
                        if cy < y0:
                            y0 = cy
                        if cy > y1:
                            y1 = cy

                        # left
                        if cx > 0:
                            n = cur - 1
                            if not visited[n] and fg[n]:
                                visited[n] = True
                                stack.append(n)
                        # right
                        if cx < w - 1:
                            n = cur + 1
                            if not visited[n] and fg[n]:
                                visited[n] = True
                                stack.append(n)
                        # up
                        if cy > 0:
                            n = cur - w
                            if not visited[n] and fg[n]:
                                visited[n] = True
                                stack.append(n)
                        # down
                        if cy < h - 1:
                            n = cur + w
                            if not visited[n] and fg[n]:
                                visited[n] = True
                                stack.append(n)

                    box_w = x1 - x0 + 1
                    box_h = y1 - y0 + 1
                    if area >= min_area and box_w >= 16 and box_h >= 10:
                        components.append((x0, y0, x1, y1, area))

            if not components:
                return []

            # Keep larger components and order like dashboard reading flow.
            components.sort(key=lambda c: c[4], reverse=True)
            components = components[: max_blocks * 2]
            components.sort(key=lambda c: (c[1], c[0]))
            components = components[:max_blocks]

            blocks: List[Dict[str, float]] = []
            for x0, y0, x1, y1, _ in components:
                blocks.append(
                    {
                        'x': max(0.0, min(1.0, x0 / float(w))),
                        'y': max(0.0, min(1.0, y0 / float(h))),
                        'w': max(0.02, min(1.0, (x1 - x0 + 1) / float(w))),
                        'h': max(0.02, min(1.0, (y1 - y0 + 1) / float(h))),
                    }
                )

            return blocks

    except Exception:
        return []


def apply_layout_from_blocks(visuals: List[Dict[str, Any]], blocks: List[Dict[str, float]]) -> bool:
    """Apply a layout inferred from screenshot blocks. Returns True if applied."""
    if not blocks:
        return False

    # Map normalized coordinates to an integer dashboard grid.
    grid_cols = 4
    grid_rows = 6

    for index, visual in enumerate(visuals):
        if index >= len(blocks):
            break
        b = blocks[index]
        col = int(round(b['x'] * (grid_cols - 1)))
        row = int(round(b['y'] * (grid_rows - 1)))
        width = max(1, int(round(b['w'] * grid_cols)))
        height = max(1, int(round(b['h'] * grid_rows)))

        if col + width > grid_cols:
            width = max(1, grid_cols - col)
        if row + height > grid_rows:
            height = max(1, grid_rows - row)

        visual['position'] = {
            'row': row,
            'column': col,
            'width': width,
            'height': height,
        }

    return True


def apply_layout_profile(visuals: List[Dict[str, Any]], profile: str) -> None:
    """Apply layout coordinates based on profile inferred from screenshot."""
    if profile == 'mobile':
        positions = [
            {'row': 0, 'column': 0, 'width': 1, 'height': 1},
            {'row': 1, 'column': 0, 'width': 1, 'height': 1},
            {'row': 2, 'column': 0, 'width': 1, 'height': 1},
            {'row': 3, 'column': 0, 'width': 1, 'height': 1},
            {'row': 4, 'column': 0, 'width': 1, 'height': 1},
        ]
    elif profile == 'tablet':
        positions = [
            {'row': 0, 'column': 0, 'width': 1, 'height': 1},
            {'row': 0, 'column': 1, 'width': 1, 'height': 1},
            {'row': 1, 'column': 0, 'width': 2, 'height': 1},
            {'row': 2, 'column': 0, 'width': 2, 'height': 1},
            {'row': 3, 'column': 0, 'width': 2, 'height': 1},
        ]
    else:
        # Desktop-wide default
        positions = [
            {'row': 0, 'column': 0, 'width': 1, 'height': 1},
            {'row': 0, 'column': 1, 'width': 1, 'height': 1},
            {'row': 1, 'column': 0, 'width': 2, 'height': 1},
            {'row': 1, 'column': 2, 'width': 2, 'height': 1},
            {'row': 2, 'column': 0, 'width': 4, 'height': 1},
        ]

    for index, visual in enumerate(visuals):
        if index >= len(positions):
            break
        visual['position'] = positions[index]


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
    for column in columns:
        lower_name = column.get('name', '').lower()
        if any(token in lower_name for token in preferred_tokens):
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


def build_adaptive_report(
    table: Dict[str, Any],
    default_project_id: str,
    default_dataset_id: str,
    layout_profile: str = 'desktop',
    screenshot_size: Optional[Tuple[int, int]] = None,
    detected_blocks: Optional[List[Dict[str, float]]] = None,
) -> Dict[str, Any]:
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

    blocks_used = apply_layout_from_blocks(visuals, detected_blocks or [])
    if not blocks_used:
        apply_layout_profile(visuals, layout_profile)

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
        'layoutProfile': layout_profile,
        'screenshotSize': list(screenshot_size) if screenshot_size else None,
        'detectedBlocks': detected_blocks or [],
        'layoutSource': 'screenshot-blocks' if blocks_used else 'profile-ratio',
    }

    return report


def generate_reports_from_schema(
    schema_file: str,
    project_id: str,
    dataset_id: str,
    output_dir: Path,
    screenshot_file: str = '',
    layout_mode: str = 'auto',
    debug_visual_detection: bool = False,
) -> None:
    schema = load_json_file(schema_file)
    _, tables = normalize_table_definitions(schema)

    if not tables:
        print(f'No tables found in schema file: {schema_file}')
        return

    print(f"\n📊 Generating adaptive Looker Studio reports from schema")
    print(f"   Schema file: {schema_file}")
    print(f"   Tables found: {len(tables)}")
    print(f"   Output: {output_dir}\n")

    layout_profile = 'desktop'
    screenshot_size: Optional[Tuple[int, int]] = None
    detected_blocks: List[Dict[str, float]] = []
    if screenshot_file:
        layout_profile, screenshot_size = infer_layout_profile_from_screenshot(screenshot_file)
        if layout_mode in {'auto', 'blocks'}:
            detected_blocks = detect_visual_blocks_from_screenshot(screenshot_file)
        if screenshot_size:
            print(
                f"   Screenshot: {screenshot_file} "
                f"({screenshot_size[0]}x{screenshot_size[1]}) -> layout={layout_profile}"
            )
        else:
            print(f"   Screenshot unreadable: {screenshot_file} -> fallback layout=desktop")

        if detected_blocks:
            print(f"   Visual blocks detected: {len(detected_blocks)}")
        elif layout_mode == 'blocks':
            print("   No visual blocks detected -> fallback profile layout")

        if debug_visual_detection:
            artifact = export_detection_debug_artifacts(screenshot_file, detected_blocks, output_dir)
            if artifact:
                print(f"   Debug artifact: {artifact}")
            else:
                print("   Debug artifact: unavailable (Pillow missing or screenshot not readable)")
        print()

    for table in tables:
        report = build_adaptive_report(
            table,
            project_id,
            dataset_id,
            layout_profile=layout_profile,
            screenshot_size=screenshot_size,
            detected_blocks=detected_blocks,
        )
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
    parser.add_argument(
        '--screenshot-file',
        default='',
        help='Optional Looker Studio screenshot used to infer layout profile (desktop/tablet/mobile)',
    )
    parser.add_argument(
        '--layout-mode',
        choices=['auto', 'ratio', 'blocks'],
        default='auto',
        help='Layout strategy with screenshot: auto (blocks then ratio), ratio only, or blocks preferred',
    )
    parser.add_argument(
        '--debug-visual-detection',
        action='store_true',
        help='Export screenshot debug artifacts (annotated image + blocks JSON) when --screenshot-file is provided',
    )
    parser.add_argument('--all', action='store_true', help='Generate all sample reports (default: true if no specific report specified)')
    parser.add_argument('--sales', action='store_true', help='Generate sales dashboard')
    parser.add_argument('--marketing', action='store_true', help='Generate marketing report')
    parser.add_argument('--customer', action='store_true', help='Generate customer analytics')
    parser.add_argument('--finance', action='store_true', help='Generate finance summary')

    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.schema_file:
        generate_reports_from_schema(
            args.schema_file,
            args.project_id,
            args.dataset_id,
            output_dir,
            screenshot_file=args.screenshot_file,
            layout_mode=args.layout_mode,
            debug_visual_detection=args.debug_visual_detection,
        )
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
