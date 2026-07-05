"""
Looker Studio to Power BI migration package.

Main components:
- extraction: Parse Looker Studio report schemas
- transformation: Convert formulas, controls, and data sources
- generation: Generate Power BI .pbip projects
- deployment: Deploy to Power BI Service
"""

__version__ = '1.0.0'
__author__ = 'Looker Studio to Power BI Migration Team'

from .extractor import LookerStudioExtractor
from .transformer import LookerStudioTransformer
from .generator import PBIPGenerator

__all__ = [
    'LookerStudioExtractor',
    'LookerStudioTransformer',
    'PBIPGenerator',
]
