"""
AST (Abstract Syntax Tree) node definitions.
Each node represents a structural element of the SQL query being built.

Supports: SELECT, INSERT, UPDATE, DELETE statements.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Any


class QueryType(Enum):
    """Type of SQL query being compiled."""
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"


@dataclass
class ASTNode:
    """Base class for all AST nodes."""
    pass


# ── Expressions ──────────────────────────────────────────────────────────────

@dataclass
class ColumnRef(ASTNode):
    """Reference to a table column. e.g.  mesures.pollution"""
    table: Optional[str]
    column: str

    def __str__(self):
        return f"{self.table}.{self.column}" if self.table else self.column


@dataclass
class Literal(ASTNode):
    """A literal value: number or string."""
    value: Any
    dtype: str  # 'number' | 'string'

    def __str__(self):
        if self.dtype == "string":
            return f"'{self.value}'"
        return str(self.value)


@dataclass
class AggregateExpr(ASTNode):
    """Aggregate function call: COUNT(*), AVG(col), …"""
    func: str          # COUNT | AVG | MAX | MIN | SUM
    arg: Optional[ColumnRef]  # None means *

    def __str__(self):
        arg_str = str(self.arg) if self.arg else "*"
        return f"{self.func}({arg_str})"


@dataclass
class BinaryOp(ASTNode):
    """Binary comparison: col > value, col = 'actif', …"""
    left: ASTNode
    op: str        # '>', '<', '>=', '<=', '=', '!='
    right: ASTNode

    def __str__(self):
        return f"{self.left} {self.op} {self.right}"


@dataclass
class LogicalOp(ASTNode):
    """AND / OR joining two conditions."""
    left: ASTNode
    op: str   # 'AND' | 'OR'
    right: ASTNode

    def __str__(self):
        return f"({self.left} {self.op} {self.right})"


# ── Clauses ──────────────────────────────────────────────────────────────────

@dataclass
class SelectClause(ASTNode):
    columns: List[ASTNode] = field(default_factory=list)
    # e.g. [ColumnRef(None, 'zone'), AggregateExpr('AVG', ColumnRef(None,'pollution'))]


@dataclass
class FromClause(ASTNode):
    table: str   # e.g. 'mesures'
    alias: Optional[str] = None


@dataclass
class WhereClause(ASTNode):
    condition: Optional[ASTNode] = None


@dataclass
class GroupByClause(ASTNode):
    columns: List[ColumnRef] = field(default_factory=list)


@dataclass
class OrderByClause(ASTNode):
    column: ASTNode
    direction: str = "DESC"   # 'ASC' | 'DESC'


@dataclass
class LimitClause(ASTNode):
    count: int


@dataclass
class SetClause(ASTNode):
    """SET column = value (for UPDATE statements)."""
    column: str
    value: Any

    def __str__(self):
        if isinstance(self.value, str):
            return f"{self.column} = '{self.value}'"
        return f"{self.column} = {self.value}"


# ── Root Statements ─────────────────────────────────────────────────────────

@dataclass
class SelectStatement(ASTNode):
    """Root node representing a complete SELECT statement."""
    query_type: QueryType = QueryType.SELECT
    select: SelectClause = field(default_factory=SelectClause)
    from_: Optional[FromClause] = None
    where: Optional[WhereClause] = None
    group_by: Optional[GroupByClause] = None
    order_by: Optional[OrderByClause] = None
    limit: Optional[LimitClause] = None
    # For UPDATE statements
    set_clause: Optional[SetClause] = None
    # Metadata
    ambiguous: bool = False
    ambiguity_hint: str = ""