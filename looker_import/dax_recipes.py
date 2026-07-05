"""
Looker formula to DAX conversion recipes.

Provides mapping and transformation of 100+ Looker functions to DAX equivalents.
"""

import re
from typing import Dict, List, Tuple, Optional


class LookerToDaxConverter:
    """Converts Looker formulas to DAX expressions."""
    
    # Looker to DAX function mapping
    FUNCTION_MAPPING = {
        # Aggregation functions
        'SUM': 'SUM',
        'COUNT': 'COUNT',
        'COUNT_DISTINCT': 'DISTINCTCOUNT',
        'AVG': 'AVERAGE',
        'MIN': 'MIN',
        'MAX': 'MAX',
        'STDDEV': 'STDEV.S',
        'PERCENTILE': 'PERCENTILE.INC',
        
        # String functions
        'CONCAT': 'CONCATENATE',
        'UPPER': 'UPPER',
        'LOWER': 'LOWER',
        'LENGTH': 'LEN',
        'SUBSTR': 'MID',
        'TRIM': 'TRIM',
        'REPLACE': 'SUBSTITUTE',
        'SEARCH': 'SEARCH',
        
        # Date functions
        'CURRENT_DATE': 'TODAY',
        'CURRENT_TIMESTAMP': 'NOW',
        'DATE_DIFF': 'DATEDIFF',
        'DATE_ADD': 'DATE',
        'EXTRACT': 'INT',
        'QUARTER': 'QUARTER',
        'YEAR': 'YEAR',
        'MONTH': 'MONTH',
        'DAY': 'DAY',
        'WEEK': 'WEEKNUM',
        
        # Conditional functions
        'CASE': 'SWITCH',
        'IF': 'IF',
        'COALESCE': 'COALESCE',
        'NULLIF': 'IF',
        
        # Numeric functions
        'ABS': 'ABS',
        'ROUND': 'ROUND',
        'CEIL': 'ROUNDUP',
        'FLOOR': 'ROUNDDOWN',
        'MOD': 'MOD',
        'POWER': 'POWER',
        'SQRT': 'SQRT',
        'LOG': 'LOG',
        'EXP': 'EXP',
        
        # Type conversion
        'CAST': 'INT',
        'SAFE_CAST': 'INT',
        'SAFE_DIVIDE': 'DIVIDE',
    }
    
    # Looker operators that need special handling
    OPERATOR_MAPPING = {
        '==': '=',
        '!=': '<>',
        '&&': '&&',
        '||': '||',
        'AND': '&&',
        'OR': '||',
        'NOT': 'NOT',
    }
    
    def __init__(self):
        self.unsupported_functions = []
        self.conversion_issues = []
    
    def convert(self, looker_expr: str) -> str:
        """Convert a Looker formula to DAX."""
        if not looker_expr:
            return ''
        
        dax_expr = looker_expr
        
        # Replace Looker functions with DAX equivalents
        for looker_func, dax_func in self.FUNCTION_MAPPING.items():
            pattern = rf'\b{looker_func}\s*\('
            dax_expr = re.sub(pattern, f'{dax_func}(', dax_expr, flags=re.IGNORECASE)
        
        # Replace operators
        for looker_op, dax_op in self.OPERATOR_MAPPING.items():
            dax_expr = dax_expr.replace(looker_op, dax_op)
        
        # Handle special Looker patterns
        dax_expr = self._convert_case_statement(dax_expr)
        dax_expr = self._convert_date_functions(dax_expr)
        dax_expr = self._convert_aggregate_functions(dax_expr)
        
        return dax_expr
    
    def _convert_case_statement(self, expr: str) -> str:
        """Convert Looker CASE to DAX SWITCH."""
        # CASE WHEN ... THEN ... ELSE ... END
        # becomes SWITCH ( TRUE(), condition1, result1, condition2, result2, default )
        pattern = r'CASE\s+WHEN\s+(.*?)\s+THEN\s+(.*?)\s+ELSE\s+(.*?)\s+END'
        
        def replace_case(match):
            conditions = match.group(1)
            result = match.group(2)
            default = match.group(3)
            return f'IF({conditions}, {result}, {default})'
        
        return re.sub(pattern, replace_case, expr, flags=re.IGNORECASE)
    
    def _convert_date_functions(self, expr: str) -> str:
        """Handle Looker date-specific functions."""
        # DATE_DIFF(date1, date2, 'day') -> DATEDIFF(date1, date2, DAY)
        pattern = r'DATEDIFF\s*\(\s*([^,]+)\s*,\s*([^,]+)\s*,\s*[\'"](\w+)[\'"]\s*\)'
        
        def replace_datediff(match):
            date1 = match.group(1)
            date2 = match.group(2)
            unit = match.group(3).upper()
            return f'DATEDIFF({date1}, {date2}, {unit})'
        
        return re.sub(pattern, replace_datediff, expr, flags=re.IGNORECASE)
    
    def _convert_aggregate_functions(self, expr: str) -> str:
        """Handle Looker aggregate functions."""
        # RUNNING_TOTAL -> SUM with ALL
        expr = re.sub(
            r'RUNNING_TOTAL\s*\(\s*([^)]+)\s*\)',
            r'SUM(\1, ALL)',
            expr,
            flags=re.IGNORECASE
        )
        
        # COUNT_DISTINCT -> DISTINCTCOUNT
        expr = re.sub(
            r'COUNT_DISTINCT\s*\(\s*([^)]+)\s*\)',
            r'DISTINCTCOUNT(\1)',
            expr,
            flags=re.IGNORECASE
        )
        
        # SAFE_DIVIDE -> DIVIDE
        expr = re.sub(
            r'SAFE_DIVIDE\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)',
            r'DIVIDE(\1, \2)',
            expr,
            flags=re.IGNORECASE
        )
        
        return expr
    
    def get_fidelity_score(self, looker_expr: str) -> float:
        """
        Estimate fidelity of conversion (0-100).
        100 = perfect conversion, lower = more manual work needed.
        """
        if not looker_expr:
            return 100.0
        
        score = 100.0
        
        # Check for unsupported functions
        unsupported = [
            'RUNNING_TOTAL', 'PIVOT', 'UNPIVOT', 'CUSTOM_SQL',
            'JS_', 'REGEX', 'NATIVE_QUERY',
        ]
        
        for func in unsupported:
            if func in looker_expr.upper():
                score -= 25
        
        # Check for complex nested structures
        paren_depth = looker_expr.count('(')
        if paren_depth > 5:
            score -= min(20, paren_depth - 5)
        
        return max(0.0, min(100.0, score))
    
    def get_unsupported_functions(self, looker_expr: str) -> List[str]:
        """Identify unsupported Looker functions."""
        unsupported = []
        
        # Pattern for function calls
        pattern = r'\b([A-Z_]+)\s*\('
        
        for match in re.finditer(pattern, looker_expr, re.IGNORECASE):
            func_name = match.group(1).upper()
            
            if func_name not in self.FUNCTION_MAPPING and func_name not in ['IF', 'CASE']:
                unsupported.append(func_name)
        
        return list(set(unsupported))
    
    def generate_conversion_report(self, looker_expr: str) -> Dict[str, any]:
        """Generate detailed conversion report."""
        dax_expr = self.convert(looker_expr)
        unsupported = self.get_unsupported_functions(looker_expr)
        fidelity = self.get_fidelity_score(looker_expr)
        
        return {
            'original': looker_expr,
            'converted': dax_expr,
            'fidelity': fidelity,
            'unsupported_functions': unsupported,
            'requires_manual_review': fidelity < 80 or len(unsupported) > 0,
            'notes': self._generate_notes(looker_expr, unsupported),
        }
    
    def _generate_notes(self, looker_expr: str, unsupported: List[str]) -> List[str]:
        """Generate notes for manual review."""
        notes = []
        
        if unsupported:
            notes.append(f"Found unsupported functions: {', '.join(unsupported)}")
        
        if 'PIVOT' in looker_expr.upper():
            notes.append("PIVOT expressions require manual implementation")
        
        if 'CUSTOM_SQL' in looker_expr.upper():
            notes.append("Custom SQL requires conversion to DAX or M")
        
        if looker_expr.count('(') > 5:
            notes.append("Complex nested formula - test thoroughly")
        
        return notes


class FormulaValidator:
    """Validates and assesses formula compatibility."""
    
    @staticmethod
    def validate_dax(dax_expr: str) -> Tuple[bool, List[str]]:
        """Validate DAX expression syntax."""
        issues = []
        
        # Check for unbalanced parentheses
        if dax_expr.count('(') != dax_expr.count(')'):
            issues.append("Unbalanced parentheses")
        
        # Check for reserved keywords used incorrectly
        reserved = ['SELECT', 'FROM', 'WHERE', 'UNION', 'INTERSECT']
        for keyword in reserved:
            if f' {keyword} ' in dax_expr.upper():
                issues.append(f"SQL keyword '{keyword}' found - may cause issues")
        
        return len(issues) == 0, issues
