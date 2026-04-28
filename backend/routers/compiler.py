"""
Router: /compiler
POST /compiler/compile  — compile NL query to SQL, return SQL + AST + tokens
POST /compiler/query    — compile NL → SQL then execute (SELECT only)
GET  /compiler/examples — return example queries for the UI
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any

from ..db import fetch_all

router = APIRouter(prefix="/compiler", tags=["Compiler NL→SQL"])


class QueryIn(BaseModel):
    query: str


class TokenOut(BaseModel):
    type: str
    value: str
    pos: int


class CompileResult(BaseModel):
    sql: str
    warnings: list[str]
    ambiguous: bool
    ambiguity_hint: str
    query_type: str          # SELECT, INSERT, UPDATE, DELETE
    ast: dict
    tokens: list[TokenOut]
    error: Optional[str] = None
    error_pos: Optional[int] = None
    error_arrow: Optional[str] = None


class QueryResult(BaseModel):
    sql: str
    warnings: list[str]
    ambiguous: bool
    ambiguity_hint: str
    query_type: str
    ast: dict
    tokens: list[TokenOut]
    rows: list[dict]
    row_count: int
    executed: bool            # True if actually executed on DB
    error: Optional[str] = None
    error_pos: Optional[int] = None
    error_arrow: Optional[str] = None


class ExampleQuery(BaseModel):
    nl: str
    description: str
    query_type: str


def _build_error_arrow(query: str, pos: int) -> str:
    """Build a visual arrow pointing to the error position."""
    safe_pos = min(pos, len(query))
    return f"  {query}\n  {' ' * safe_pos}^--- erreur ici"


def _compile(nl_query: str):
    """Import and run the compiler pipeline."""
    try:
        from compiler import compile_query, ParseError, CompilationError
        from compiler.lexer import Lexer
    except ImportError:
        raise HTTPException(500, "Module compiler non disponible")

    # Tokenize first (we always want tokens for the UI)
    lexer = Lexer(nl_query)
    tokens = lexer.tokenize()
    token_list = [
        TokenOut(type=t.type.name, value=t.value, pos=t.pos)
        for t in tokens if t.type.name != "EOF"
    ]

    try:
        sql, warnings, ast = compile_query(nl_query)
    except (ParseError, CompilationError) as exc:
        pos = getattr(exc, 'pos', getattr(getattr(exc, 'token', None), 'pos', 0))
        arrow = _build_error_arrow(nl_query, pos)
        expected = getattr(exc, 'expected', '')
        detail = getattr(exc, 'detail', str(exc))
        raise HTTPException(422, detail={
            "error": detail,
            "error_pos": pos,
            "error_arrow": arrow,
            "expected": expected,
            "tokens": [t.dict() for t in token_list],
        })
    except Exception as exc:
        raise HTTPException(400, detail={
            "error": str(exc),
            "error_pos": 0,
            "error_arrow": _build_error_arrow(nl_query, 0),
            "expected": "",
            "tokens": [t.dict() for t in token_list],
        })

    return sql, warnings, ast, token_list


def _ast_to_dict(ast) -> dict:
    """Convert AST to a JSON-serializable dict for the frontend."""
    result = {
        "type": "SelectStatement",
        "query_type": ast.query_type.value,
        "table": ast.from_.table if ast.from_ else None,
        "columns": [str(c) for c in ast.select.columns],
        "where": str(ast.where.condition) if ast.where and ast.where.condition else None,
        "order_by": (f"{ast.order_by.column} {ast.order_by.direction}"
                     if ast.order_by else None),
        "limit": ast.limit.count if ast.limit else None,
        "ambiguous": ast.ambiguous,
        "ambiguity_hint": ast.ambiguity_hint,
    }
    if ast.set_clause:
        result["set_clause"] = str(ast.set_clause)
    if ast.group_by:
        result["group_by"] = [str(c) for c in ast.group_by.columns]
    return result


@router.post("/compile", response_model=CompileResult)
def compile_only(body: QueryIn):
    """Compile NL → SQL without executing. Returns SQL + AST + tokens."""
    sql, warnings, ast, token_list = _compile(body.query)
    return CompileResult(
        sql=sql,
        warnings=warnings or [],
        ambiguous=ast.ambiguous,
        ambiguity_hint=ast.ambiguity_hint,
        query_type=ast.query_type.value,
        ast=_ast_to_dict(ast),
        tokens=token_list,
    )


@router.post("/query", response_model=QueryResult)
def compile_and_execute(body: QueryIn):
    """
    Compile NL → SQL then execute against PostgreSQL.
    ONLY SELECT queries are executed. DELETE/UPDATE/INSERT are compiled only.
    """
    sql, warnings, ast, token_list = _compile(body.query)

    # Only execute SELECT queries
    if ast.query_type.value != "SELECT":
        warnings.append(
            f"ℹ Requête {ast.query_type.value} compilée avec succès "
            f"mais non exécutée (seules les requêtes SELECT sont exécutées)"
        )
        return QueryResult(
            sql=sql,
            warnings=warnings or [],
            ambiguous=ast.ambiguous,
            ambiguity_hint=ast.ambiguity_hint,
            query_type=ast.query_type.value,
            ast=_ast_to_dict(ast),
            tokens=token_list,
            rows=[],
            row_count=0,
            executed=False,
        )

    # Execute SELECT
    try:
        rows = fetch_all(sql)
    except Exception as e:
        raise HTTPException(422, detail={
            "error": f"Erreur SQL lors de l'exécution: {e}",
            "sql": sql,
            "error_pos": 0,
            "error_arrow": "",
            "tokens": [t.dict() for t in token_list],
        })

    return QueryResult(
        sql=sql,
        warnings=warnings or [],
        ambiguous=ast.ambiguous,
        ambiguity_hint=ast.ambiguity_hint,
        query_type=ast.query_type.value,
        ast=_ast_to_dict(ast),
        tokens=token_list,
        rows=rows,
        row_count=len(rows),
        executed=True,
    )


@router.get("/examples")
def get_examples():
    """Return example queries for the compiler UI."""
    return {
        "examples": [
            {"nl": "Affiche les capteurs",
             "description": "Liste tous les capteurs", "query_type": "SELECT"},
            {"nl": "Affiche les 5 zones les plus polluées",
             "description": "Top 5 zones par pollution", "query_type": "SELECT"},
            {"nl": "Combien de capteurs sont hors service ?",
             "description": "Compte les capteurs HS", "query_type": "SELECT"},
            {"nl": "Quels citoyens ont un score écologique > 80 ?",
             "description": "Citoyens éco-responsables", "query_type": "SELECT"},
            {"nl": "Donne-moi le trajet le plus économique en CO2",
             "description": "Trajet optimal CO2", "query_type": "SELECT"},
            {"nl": "Quelles interventions sont en cours ?",
             "description": "Interventions actives", "query_type": "SELECT"},
            {"nl": "Capteurs qui ne sont pas actifs",
             "description": "Capteurs hors état actif (négation)", "query_type": "SELECT"},
            {"nl": "Capteurs signalé",
             "description": "Capteurs en état signalé", "query_type": "SELECT"},
            {"nl": "Supprimer les capteurs hors service",
             "description": "Suppression (compilée seulement)", "query_type": "DELETE"},
            {"nl": "Modifier le statut des capteurs signalé",
             "description": "Mise à jour (compilée seulement)", "query_type": "UPDATE"},
        ]
    }
