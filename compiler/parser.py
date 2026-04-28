"""
Parser — NL → SQL Compiler
Consumes tokens produced by the Lexer and constructs an AST.

Supports all query types: SELECT, INSERT, UPDATE, DELETE.
Handles negation patterns: "ne sont pas actifs" → statut != 'actif'
Handles ambiguous queries with hints.

Grammar (BNF):
  query      → intent entity [filter] [ordering] [limit]
  intent     → SHOW | COUNT | AVG | MAX | MIN | SUM | SELECT | DELETE | UPDATE | INSERT
  entity     → CAPTEURS | INTERVENTIONS | CITOYENS | VEHICULES | MESURES | ZONES | TRAJETS
  filter     → (WHERE | NEG) condition (AND condition)*
  condition  → [NEG] column_ref comparator value
  column_ref → STATUT | POLLUTION | SCORE_ECOLO | NOM | TYPE | ECO_CO2 | TAUX_ERREUR | ZONE
  comparator → GT | LT | GTE | LTE | EQ | NEQ
  value      → NUMBER | STRING | STATUS_VAL
  ordering   → (ORDER | DESC_ORDER | ASC_ORDER) [column_ref]
  limit      → NUMBER (LIMIT)?
"""
from typing import List, Optional
from .lexer import Token, TokenType, Lexer
from .ast_nodes import (
    ASTNode, ColumnRef, Literal, AggregateExpr, BinaryOp, LogicalOp,
    SelectClause, FromClause, WhereClause, GroupByClause, OrderByClause,
    LimitClause, SetClause, SelectStatement, QueryType,
)


class ParseError(Exception):
    """Raised when the parser cannot understand the token stream."""
    def __init__(self, message: str, token: Token, query: str = "",
                 expected: str = ""):
        self.token = token
        self.query = query
        self.expected = expected
        self.detail = message
        arrow = self._build_arrow(query, token.pos) if query else ""
        hint = f" (attendu: {expected})" if expected else ""
        super().__init__(
            f"Erreur de syntaxe à la position {token.pos}: {message}{hint}\n{arrow}"
        )

    @staticmethod
    def _build_arrow(query: str, pos: int) -> str:
        safe_pos = min(pos, len(query))
        return f"  {query}\n  {' ' * safe_pos}^--- erreur ici"


# ── Column / table mapping ────────────────────────────────────────────────────

TABLE_MAP = {
    TokenType.CAPTEURS:      "capteurs",
    TokenType.INTERVENTIONS: "interventions",
    TokenType.CITOYENS:      "citoyens",
    TokenType.VEHICULES:     "vehicules",
    TokenType.MESURES:       "mesures",
    TokenType.ZONES:         "zones",
    TokenType.TRAJETS:       "trajets",
}

# For each entity, what columns make sense to SELECT by default
DEFAULT_COLUMNS = {
    "capteurs":       [ColumnRef(None, "id"), ColumnRef(None, "nom"),
                       ColumnRef(None, "statut"), ColumnRef(None, "zone_id")],
    "interventions":  [ColumnRef(None, "id"), ColumnRef(None, "statut"),
                       ColumnRef(None, "date_demande"), ColumnRef(None, "zone_id")],
    "citoyens":       [ColumnRef(None, "nom"), ColumnRef(None, "score_ecolo")],
    "vehicules":      [ColumnRef(None, "id"), ColumnRef(None, "statut"),
                       ColumnRef(None, "zone_id")],
    "mesures":        [ColumnRef(None, "zone_id"), ColumnRef(None, "pollution"),
                       ColumnRef(None, "timestamp")],
    "zones":          [ColumnRef(None, "id"), ColumnRef(None, "nom"),
                       ColumnRef(None, "surface_km2"), ColumnRef(None, "population")],
    "trajets":        [ColumnRef(None, "trajet_id"),
                       ColumnRef(None, "economie_co2")],
}

COL_INTENT_MAP = {
    TokenType.POLLUTION:    ("mesures",  "pollution",    "AVG"),
    TokenType.SCORE_ECOLO:  ("citoyens", "score_ecolo",  None),
    TokenType.STATUT:       (None,       "statut",       None),
    TokenType.NOM:          (None,       "nom",          None),
    TokenType.ECO_CO2:      ("trajets",  "economie_co2", None),
    TokenType.TAUX_ERREUR:  ("capteurs", "taux_erreur",  None),
    TokenType.ZONE:         (None,       "zone_id",      None),
}

# When these column tokens appear, they OVERRIDE the entity token for table
COL_TABLE_OVERRIDE = {
    TokenType.POLLUTION:   "mesures",
    TokenType.SCORE_ECOLO: "citoyens",
    TokenType.ECO_CO2:     "trajets",
    TokenType.TAUX_ERREUR: "capteurs",
}

COMPARATOR_MAP = {
    TokenType.GT:  ">",
    TokenType.LT:  "<",
    TokenType.GTE: ">=",
    TokenType.LTE: "<=",
    TokenType.EQ:  "=",
    TokenType.NEQ: "!=",
}

ENTITY_TYPES = set(TABLE_MAP.keys())
COMPARATOR_TYPES = set(COMPARATOR_MAP.keys())

INTENT_TYPES = {
    TokenType.SHOW, TokenType.SELECT, TokenType.COUNT,
    TokenType.AVG, TokenType.MAX, TokenType.MIN, TokenType.SUM,
    TokenType.DELETE, TokenType.UPDATE, TokenType.INSERT,
}


class Parser:
    def __init__(self, tokens: List[Token], query: str = ""):
        self.tokens = tokens
        self.query = query
        self.pos = 0
        self.ambiguous = False
        self.ambiguity_hint = ""

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _current(self) -> Token:
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return self.tokens[-1]  # EOF

    def _peek(self, offset=1) -> Token:
        idx = self.pos + offset
        return self.tokens[idx] if idx < len(self.tokens) else self.tokens[-1]

    def _advance(self) -> Token:
        tok = self.tokens[self.pos]
        if tok.type != TokenType.EOF:
            self.pos += 1
        return tok

    def _match(self, *types: TokenType) -> bool:
        return self._current().type in types

    def _error(self, message: str, expected: str = "") -> ParseError:
        return ParseError(message, self._current(), self.query, expected)

    # ── Main parse entry point ───────────────────────────────────────────────

    def parse(self) -> SelectStatement:
        """
        Two-pass parser:
          Pass 1 — Full lookahead scan: collect intent, entity, columns,
                   filters, negation, ordering, limit from ALL tokens.
          Pass 2 — Build the AST from collected information.
        """
        stmt = SelectStatement()

        # ── Pass 1: Full lookahead scan ──────────────────────────────────────
        intent = "show"
        query_type = QueryType.SELECT
        entity_table = None
        col_override_table = None
        column_hint = None
        filter_col = None
        filter_op = "="
        filter_val = None
        order_direction = None
        limit_n = None
        has_negation = False         # Tracks "ne sont pas" / "sauf" / "sans"
        has_explicit_where = False
        set_column = None
        set_value = None

        # Track positions of negation tokens for context
        neg_positions = []

        for i, tok in enumerate(self.tokens):
            tt = tok.type

            # ── Intent (first meaningful token) ──────────────────────────────
            if tt in INTENT_TYPES and i == 0:
                if tt == TokenType.COUNT:
                    intent = "count"
                    query_type = QueryType.SELECT
                elif tt == TokenType.AVG:
                    intent = "avg"
                    query_type = QueryType.SELECT
                elif tt == TokenType.MAX:
                    intent = "max"
                    query_type = QueryType.SELECT
                elif tt == TokenType.MIN:
                    intent = "min"
                    query_type = QueryType.SELECT
                elif tt == TokenType.SUM:
                    intent = "sum"
                    query_type = QueryType.SELECT
                elif tt == TokenType.DELETE:
                    intent = "delete"
                    query_type = QueryType.DELETE
                elif tt == TokenType.UPDATE:
                    intent = "update"
                    query_type = QueryType.UPDATE
                elif tt == TokenType.INSERT:
                    intent = "insert"
                    query_type = QueryType.INSERT
                else:
                    intent = "show"
                    query_type = QueryType.SELECT
                continue

            # ── Entity table ─────────────────────────────────────────────────
            if tt in ENTITY_TYPES and entity_table is None:
                entity_table = TABLE_MAP[tt]
                continue

            # ── Negation ─────────────────────────────────────────────────────
            if tt == TokenType.NEG:
                has_negation = True
                neg_positions.append(i)
                continue

            # ── Column hint ──────────────────────────────────────────────────
            if tt in COL_INTENT_MAP and column_hint is None and not has_explicit_where:
                _, col, agg = COL_INTENT_MAP[tt]
                column_hint = ColumnRef(None, col)
                if tt in COL_TABLE_OVERRIDE:
                    col_override_table = COL_TABLE_OVERRIDE[tt]
                continue

            # ── WHERE keyword ────────────────────────────────────────────────
            if tt == TokenType.WHERE:
                has_explicit_where = True
                continue

            # ── Comparator ───────────────────────────────────────────────────
            if tt in COMPARATOR_TYPES:
                filter_op = COMPARATOR_MAP[tt]
                continue

            # ── Filter column (after WHERE) ──────────────────────────────────
            if tt in COL_INTENT_MAP and has_explicit_where and filter_col is None:
                _, col2, _ = COL_INTENT_MAP[tt]
                filter_col = ColumnRef(None, col2)
                continue

            # ── Number — could be limit or filter value ──────────────────────
            if tt == TokenType.NUMBER:
                # If preceded by a comparator or there's already a filter column
                if filter_op != "=" or filter_col is not None or any(
                    t.type in COMPARATOR_TYPES
                    for t in self.tokens[max(0, i-3):i]
                ):
                    filter_val = Literal(
                        int(float(tok.value)) if "." not in tok.value
                        else float(tok.value), "number"
                    )
                else:
                    limit_n = int(tok.value)
                continue

            # ── Status value ─────────────────────────────────────────────────
            if tt == TokenType.STATUS_VAL:
                filter_val = Literal(tok.value, "string")
                if filter_col is None:
                    filter_col = ColumnRef(None, "statut")
                continue

            # ── String literal ───────────────────────────────────────────────
            if tt == TokenType.STRING:
                filter_val = Literal(tok.value, "string")
                continue

            # ── Order direction ──────────────────────────────────────────────
            if tt == TokenType.DESC_ORDER:
                if order_direction is None:
                    order_direction = "DESC"
                continue
            if tt == TokenType.ASC_ORDER:
                order_direction = "ASC"
                continue

            # ── AND / OR connectors ──────────────────────────────────────────
            if tt == TokenType.AND:
                continue
            if tt == TokenType.OR:
                continue

        # ── Apply negation to filter operator ────────────────────────────────
        if has_negation and filter_val:
            # "ne sont pas actifs" → statut != 'actif'
            # "sauf actif" → statut != 'actif'
            if filter_op == "=":
                filter_op = "!="

        # ── Resolve table ────────────────────────────────────────────────────
        if col_override_table:
            table = col_override_table
        elif entity_table:
            table = entity_table
        elif column_hint and column_hint.column in ("pollution",):
            table = "mesures"
        elif column_hint and column_hint.column in ("score_ecolo",):
            table = "citoyens"
        elif column_hint and column_hint.column in ("economie_co2",):
            table = "trajets"
        else:
            table = "capteurs"
            if entity_table is None and query_type == QueryType.SELECT:
                self.ambiguous = True
                self.ambiguity_hint = (
                    "Table cible non identifiée, 'capteurs' utilisée par défaut."
                )

        # ── Pass 2: Build AST ────────────────────────────────────────────────
        stmt.query_type = query_type
        stmt.from_ = FromClause(table=table)
        stmt.select = self._build_select(intent, table, column_hint, None)

        # SET clause (for UPDATE) — must be resolved BEFORE WHERE
        # to avoid using the same value for both SET and WHERE
        if query_type == QueryType.UPDATE and filter_val:
            if filter_col and filter_col.column == "statut":
                stmt.set_clause = SetClause(
                    column="statut", value=filter_val.value
                )
                # Don't also create a WHERE from the same value
                filter_col = None
                filter_val = None

        # WHERE clause
        if filter_col and filter_val:
            stmt.where = WhereClause(
                condition=BinaryOp(
                    left=filter_col, op=filter_op, right=filter_val
                )
            )
        elif filter_val and filter_col is None:
            if column_hint:
                stmt.where = WhereClause(
                    condition=BinaryOp(
                        left=ColumnRef(None, column_hint.column),
                        op=filter_op, right=filter_val
                    )
                )
            elif table == "capteurs":
                stmt.where = WhereClause(
                    condition=BinaryOp(
                        left=ColumnRef(None, "statut"),
                        op=filter_op, right=filter_val
                    )
                )

        # ORDER BY
        if order_direction:
            stmt.order_by = self._build_order(stmt.select, table,
                                               order_direction)

        # LIMIT
        if limit_n:
            stmt.limit = LimitClause(count=limit_n)
        elif (order_direction and entity_table in ("trajets",)
              and not limit_n):
            stmt.limit = LimitClause(count=1)

        stmt.ambiguous = self.ambiguous
        stmt.ambiguity_hint = self.ambiguity_hint
        return stmt

    # ── SELECT clause builder ────────────────────────────────────────────────

    def _build_select(self, intent, table, column_hint, agg_hint
                      ) -> SelectClause:
        clause = SelectClause()

        if intent == "count":
            clause.columns = [AggregateExpr("COUNT", None)]

        elif intent in ("avg", "max", "min", "sum"):
            func_map = {"avg": "AVG", "max": "MAX", "min": "MIN",
                        "sum": "SUM"}
            col = column_hint or ColumnRef(None, "valeur")
            clause.columns = [AggregateExpr(func_map[intent], col)]

        elif intent == "delete":
            # DELETE doesn't need columns — use * for display purposes
            clause.columns = [ColumnRef(None, "*")]

        elif intent == "update":
            clause.columns = [ColumnRef(None, "*")]

        elif intent == "insert":
            clause.columns = [ColumnRef(None, "*")]

        else:  # show / select
            if column_hint:
                metric_agg_map = {
                    "pollution":    ("zone_id", "AVG"),
                    "score_ecolo":  ("nom",     None),
                    "economie_co2": ("trajet_id", None),
                    "taux_erreur":  ("nom",     None),
                }
                col_name = column_hint.column
                if col_name in metric_agg_map:
                    group_col, agg_func = metric_agg_map[col_name]
                    group_ref = ColumnRef(None, group_col)
                    if agg_func:
                        agg_ref = AggregateExpr(agg_func, column_hint)
                        clause.columns = [group_ref, agg_ref]
                    else:
                        clause.columns = [group_ref, column_hint]
                else:
                    clause.columns = [column_hint]
            else:
                clause.columns = DEFAULT_COLUMNS.get(
                    table, [ColumnRef(None, "*")]
                )

        return clause

    # ── ORDER BY builder ─────────────────────────────────────────────────────

    def _build_order(self, select: SelectClause, table: str,
                     direction: str) -> OrderByClause:
        """Build ORDER BY using the best available column."""
        agg_cols = [c for c in select.columns if isinstance(c, AggregateExpr)]
        if agg_cols:
            return OrderByClause(column=agg_cols[0], direction=direction)

        non_agg = [c for c in select.columns if isinstance(c, ColumnRef)]
        # Only wrap in AVG if there are already aggregates (GROUP BY context)
        # Otherwise use the raw column for ORDER BY
        if agg_cols:  # There are aggregates → GROUP BY context
            metric_cols = {"pollution", "score_ecolo", "economie_co2",
                           "taux_erreur"}
            for col in non_agg:
                if col.column in metric_cols:
                    return OrderByClause(
                        column=AggregateExpr("AVG", col),
                        direction=direction
                    )

        if non_agg:
            return OrderByClause(column=non_agg[-1], direction=direction)

        return OrderByClause(column=ColumnRef(None, "id"),
                             direction=direction)


# ── Convenience function ──────────────────────────────────────────────────────

def parse_query(nl_query: str) -> SelectStatement:
    """Tokenize and parse a NL query, return AST."""
    tokens = Lexer(nl_query).tokenize()
    return Parser(tokens, nl_query).parse()


if __name__ == "__main__":
    queries = [
        "Affiche les 5 zones les plus polluées",
        "Combien de capteurs sont hors service ?",
        "Quels citoyens ont un score écologique > 80 ?",
        "Donne-moi le trajet le plus économique en CO2",
        "Quelles interventions sont en cours ?",
        "Capteurs qui ne sont pas actifs",
        "Supprimer les capteurs hors service",
        "Modifier le statut des capteurs signalé",
        "Capteurs signale",
        "Affiche les capteurs",
    ]
    for q in queries:
        print(f"\nQuery: {q}")
        ast = parse_query(q)
        print(f"  Type:    {ast.query_type.value}")
        print(f"  Table:   {ast.from_.table}")
        print(f"  SELECT:  {[str(c) for c in ast.select.columns]}")
        print(f"  WHERE:   {ast.where.condition if ast.where else None}")
        print(f"  ORDER:   {ast.order_by}")
        print(f"  LIMIT:   {ast.limit}")
        if ast.ambiguous:
            print(f"  ⚠ Ambiguous: {ast.ambiguity_hint}")