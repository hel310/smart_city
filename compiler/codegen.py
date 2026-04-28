"""
Code Generator — NL → SQL Compiler
Smart City Platform — Neo-Sousse 2030

Converts an AST (SelectStatement) into a valid SQL string.
Supports: SELECT, INSERT, UPDATE, DELETE generation.
Only SELECT queries are executed; others are compiled only.
"""
from typing import Tuple, List
from .ast_nodes import (
    ASTNode, ColumnRef, Literal, AggregateExpr, BinaryOp, LogicalOp,
    SelectClause, FromClause, WhereClause, GroupByClause, OrderByClause,
    LimitClause, SetClause, SelectStatement, QueryType,
)


class CompilationError(Exception):
    """Raised when SQL generation encounters a semantic issue."""
    def __init__(self, message: str, query: str = "", pos: int = 0,
                 expected: str = ""):
        self.query = query
        self.pos = pos
        self.expected = expected
        self.detail = message
        arrow = self._build_arrow(query, pos) if query else ""
        hint = f" (attendu: {expected})" if expected else ""
        super().__init__(
            f"Erreur de compilation: {message}{hint}\n{arrow}"
        )

    @staticmethod
    def _build_arrow(query: str, pos: int) -> str:
        safe_pos = min(pos, len(query))
        return f"  {query}\n  {' ' * safe_pos}^--- erreur ici"


# ── Expression emitter ────────────────────────────────────────────────────────

def emit_expr(node: ASTNode, table: str = "") -> str:
    """Convert an AST expression node into a SQL fragment string."""
    if isinstance(node, ColumnRef):
        if node.table and node.table != table:
            return f"{node.table}.{node.column}"
        return node.column

    if isinstance(node, Literal):
        if node.dtype == "string":
            # Uppercase status values for PostgreSQL enum matching
            val = node.value
            if val in ("hors_service", "en_route", "en_panne", "en_cours",
                       "en_maintenance", "signale", "actif", "inactif",
                       "termine", "arrive", "stationne", "demande",
                       "assigne", "valide"):
                val = val.upper()
            return f"'{val}'"
        return str(node.value)

    if isinstance(node, AggregateExpr):
        if node.arg is None:
            return f"{node.func}(*)"
        arg_str = emit_expr(node.arg, table)
        return f"{node.func}({arg_str})"

    if isinstance(node, BinaryOp):
        left = emit_expr(node.left, table)
        right = emit_expr(node.right, table)
        return f"{left} {node.op} {right}"

    if isinstance(node, LogicalOp):
        left = emit_expr(node.left, table)
        right = emit_expr(node.right, table)
        return f"({left} {node.op} {right})"

    return str(node)


# ── Main code generator ──────────────────────────────────────────────────────

class CodeGenerator:
    """
    Converts a SelectStatement AST into a SQL string.
    Returns (sql, warnings) where warnings is a list of hint strings.
    """

    def generate(self, stmt: SelectStatement) -> Tuple[str, list]:
        warnings = []
        if stmt.ambiguous:
            warnings.append(f"⚠ Requête ambiguë : {stmt.ambiguity_hint}")

        table = stmt.from_.table if stmt.from_ else "capteurs"

        if stmt.query_type == QueryType.DELETE:
            return self._generate_delete(stmt, table, warnings)
        elif stmt.query_type == QueryType.UPDATE:
            return self._generate_update(stmt, table, warnings)
        elif stmt.query_type == QueryType.INSERT:
            return self._generate_insert(stmt, table, warnings)
        else:
            return self._generate_select(stmt, table, warnings)

    def _generate_select(self, stmt: SelectStatement, table: str,
                         warnings: list) -> Tuple[str, list]:
        parts = []

        # SELECT
        select_exprs = [emit_expr(col, table) for col in stmt.select.columns]

        # Auto-inject GROUP BY when mixing aggregates with non-aggregates
        has_agg = any(isinstance(c, AggregateExpr)
                      for c in stmt.select.columns)
        non_agg = [c for c in stmt.select.columns
                   if not isinstance(c, AggregateExpr)]

        if has_agg and non_agg:
            stmt.group_by = GroupByClause(columns=non_agg)

        parts.append(f"SELECT {', '.join(select_exprs)}")

        # FROM
        parts.append(f"FROM {table}")

        # WHERE
        if stmt.where and stmt.where.condition:
            cond = emit_expr(stmt.where.condition, table)
            parts.append(f"WHERE {cond}")

        # GROUP BY
        if stmt.group_by:
            gb_cols = [emit_expr(c, table) for c in stmt.group_by.columns]
            parts.append(f"GROUP BY {', '.join(gb_cols)}")

        # ORDER BY
        if stmt.order_by:
            order_expr = emit_expr(stmt.order_by.column, table)
            parts.append(f"ORDER BY {order_expr} {stmt.order_by.direction}")

        # LIMIT
        if stmt.limit:
            parts.append(f"LIMIT {stmt.limit.count}")

        sql = "\n".join(parts)
        return sql, warnings

    def _generate_delete(self, stmt: SelectStatement, table: str,
                         warnings: list) -> Tuple[str, list]:
        parts = [f"DELETE FROM {table}"]

        if stmt.where and stmt.where.condition:
            cond = emit_expr(stmt.where.condition, table)
            parts.append(f"WHERE {cond}")
        else:
            warnings.append(
                "⚠ DELETE sans clause WHERE — supprime TOUTES les lignes!"
            )

        warnings.append("ℹ Requête DELETE compilée (non exécutée par sécurité)")
        sql = "\n".join(parts)
        return sql, warnings

    def _generate_update(self, stmt: SelectStatement, table: str,
                         warnings: list) -> Tuple[str, list]:
        parts = [f"UPDATE {table}"]

        if stmt.set_clause:
            val = stmt.set_clause.value
            if isinstance(val, str):
                val_upper = val.upper()
                parts.append(f"SET {stmt.set_clause.column} = '{val_upper}'")
            else:
                parts.append(f"SET {stmt.set_clause.column} = {val}")
        else:
            warnings.append("⚠ UPDATE sans clause SET — aucune valeur à modifier")

        if stmt.where and stmt.where.condition:
            cond = emit_expr(stmt.where.condition, table)
            parts.append(f"WHERE {cond}")
        else:
            warnings.append(
                "⚠ UPDATE sans clause WHERE — modifie TOUTES les lignes!"
            )

        warnings.append("ℹ Requête UPDATE compilée (non exécutée par sécurité)")
        sql = "\n".join(parts)
        return sql, warnings

    def _generate_insert(self, stmt: SelectStatement, table: str,
                         warnings: list) -> Tuple[str, list]:
        parts = [f"INSERT INTO {table}"]
        parts.append("VALUES (...)")
        warnings.append(
            "⚠ INSERT nécessite des valeurs explicites — "
            "veuillez préciser les données à insérer"
        )
        warnings.append("ℹ Requête INSERT compilée (non exécutée par sécurité)")
        sql = "\n".join(parts)
        return sql, warnings


# ── Full pipeline convenience function ───────────────────────────────────────

def compile_query(nl_query: str) -> Tuple[str, list, SelectStatement]:
    """
    Full NL → SQL pipeline.
    Returns (sql_string, warnings_list, ast).
    Raises ParseError or CompilationError on failure.
    """
    from .parser import parse_query
    ast = parse_query(nl_query)
    sql, warnings = CodeGenerator().generate(ast)
    return sql, warnings, ast


# ── Smoke test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_cases = [
        ("Affiche les 5 zones les plus polluées",
         "SELECT zone_id, AVG(pollution)\nFROM mesures\nGROUP BY zone_id\nORDER BY AVG(pollution) DESC\nLIMIT 5"),

        ("Combien de capteurs sont hors service ?",
         "SELECT COUNT(*)\nFROM capteurs\nWHERE statut = 'HORS_SERVICE'"),

        ("Quels citoyens ont un score écologique > 80 ?",
         "SELECT nom, score_ecolo\nFROM citoyens\nWHERE score_ecolo > 80"),

        ("Donne-moi le trajet le plus économique en CO2",
         "SELECT trajet_id, economie_co2\nFROM trajets\nORDER BY economie_co2 ASC\nLIMIT 1"),

        ("Quelles interventions sont en cours ?",
         "SELECT id, statut, date_demande, zone_id\nFROM interventions\nWHERE statut = 'EN_COURS'"),

        ("Capteurs qui ne sont pas actifs",
         "SELECT id, nom, statut, zone_id\nFROM capteurs\nWHERE statut != 'ACTIF'"),

        ("Supprimer les capteurs hors service",
         "DELETE FROM capteurs\nWHERE statut = 'HORS_SERVICE'"),

        ("Modifier le statut des capteurs signalé",
         "UPDATE capteurs\nSET statut = 'SIGNALE'"),

        ("Capteurs signale",
         "SELECT id, nom, statut, zone_id\nFROM capteurs\nWHERE statut = 'SIGNALE'"),

        ("Affiche les capteurs",
         "SELECT id, nom, statut, zone_id\nFROM capteurs"),
    ]

    print("=" * 70)
    print("NL -> SQL Compiler -- Smoke Test")
    print("=" * 70)
    passed = 0
    failed = 0
    for nl, expected in test_cases:
        print(f"\n{'─' * 70}")
        print(f"Input : {nl}")
        try:
            sql, warnings, ast = compile_query(nl)
            print(f"Output: {sql}")
            print(f"Type:   {ast.query_type.value}")
            if warnings:
                for w in warnings:
                    print(f"  ⚠ {w}")
            # Simple check
            if sql.strip() == expected.strip():
                print("✅ PASS")
                passed += 1
            else:
                print(f"❌ FAIL — expected:\n{expected}")
                failed += 1
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1

    print(f"\n{'=' * 70}")
    print(f"Results: {passed} passed, {failed} failed out of {len(test_cases)}")