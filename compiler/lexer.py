"""
Lexer (Tokenizer) — NL → SQL Compiler
Smart City Platform — Neo-Sousse 2030

Tokenizes French natural-language queries into a stream of typed tokens.
Supports: SELECT, INSERT, UPDATE, DELETE query verbs.
Handles: negation (ne…pas, sauf, sans), multi-word phrases, status values.
"""
import re
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional


class TokenType(Enum):
    # ── Query intent verbs ───────────────────────────────────────
    SHOW       = auto()   # affiche, montre, donne, liste, quels
    COUNT      = auto()   # combien, nombre
    SELECT     = auto()   # sélectionne
    DELETE     = auto()   # supprimer, effacer, retirer
    UPDATE     = auto()   # modifier, mettre à jour, mise à jour
    INSERT     = auto()   # ajouter, insérer, créer

    # ── Filter keywords ──────────────────────────────────────────
    WHERE      = auto()   # où, avec, dont, qui, ayant
    ORDER      = auto()   # trie, classe, ordonne
    LIMIT      = auto()   # les N premiers/dernières, limite
    GROUP      = auto()   # par, groupé

    # ── Aggregation ──────────────────────────────────────────────
    AVG        = auto()   # moyenne
    MAX        = auto()   # maximum, le plus
    MIN        = auto()   # minimum, le moins
    SUM        = auto()   # somme, total
    COUNT_KW   = auto()   # (alias for COUNT when not at position 0)

    # ── Entities (tables) ────────────────────────────────────────
    CAPTEURS   = auto()
    INTERVENTIONS = auto()
    CITOYENS   = auto()
    VEHICULES  = auto()
    MESURES    = auto()
    ZONES      = auto()
    TRAJETS    = auto()

    # ── Columns / attributes ─────────────────────────────────────
    STATUT     = auto()   # statut, état, status
    ZONE       = auto()
    POLLUTION  = auto()
    SCORE_ECOLO = auto()  # score, écologique, écolo
    NOM        = auto()
    TYPE       = auto()
    TRAJET_ID  = auto()
    ECO_CO2    = auto()   # co2, economie_co2
    TAUX_ERREUR = auto()

    # ── Comparators ──────────────────────────────────────────────
    GT         = auto()   # >, supérieur, plus grand
    LT         = auto()   # <, inférieur, moins grand
    GTE        = auto()   # >=
    LTE        = auto()   # <=
    EQ         = auto()   # =, égal, est
    NEQ        = auto()   # !=, différent

    # ── Negation ─────────────────────────────────────────────────
    NEG        = auto()   # ne, n', pas, non, sauf, sans, ni

    # ── Values & literals ────────────────────────────────────────
    NUMBER     = auto()
    STRING     = auto()
    STATUS_VAL = auto()   # hors_service, actif, inactif, signalé, …

    # ── Connectors / misc ────────────────────────────────────────
    AND        = auto()
    OR         = auto()
    DESC_ORDER = auto()   # descendant, les plus polluées
    ASC_ORDER  = auto()

    EOF        = auto()
    UNKNOWN    = auto()


@dataclass
class Token:
    type: TokenType
    value: str
    pos: int          # character position in original query

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, pos={self.pos})"


# ── Multi-word phrases (checked FIRST, longest match wins) ─────────────────
# Order matters: longer phrases must come before shorter sub-phrases.
MULTI_WORD_KEYWORDS: dict[str, TokenType] = {
    # CRUD
    "mettre à jour":   TokenType.UPDATE,
    "mettre a jour":   TokenType.UPDATE,
    "mise à jour":     TokenType.UPDATE,
    "mise a jour":     TokenType.UPDATE,
    # Status values (multi-word)
    "hors service":    TokenType.STATUS_VAL,
    "hors_service":    TokenType.STATUS_VAL,
    "en route":        TokenType.STATUS_VAL,
    "en_route":        TokenType.STATUS_VAL,
    "en panne":        TokenType.STATUS_VAL,
    "en_panne":        TokenType.STATUS_VAL,
    "en cours":        TokenType.STATUS_VAL,
    "en_cours":        TokenType.STATUS_VAL,
    # Negation patterns
    "ne sont pas":     TokenType.NEG,
    "n'est pas":       TokenType.NEG,
    "n'ont pas":       TokenType.NEG,
    "ne sont plus":    TokenType.NEG,
    "ne pas":          TokenType.NEG,
    # Comparators
    "plus grand":      TokenType.GT,
    "moins grand":     TokenType.LT,
    "les plus":        TokenType.DESC_ORDER,
    # Ordering
    "donne-moi":       TokenType.SHOW,
    "donne moi":       TokenType.SHOW,
}

# ── Single-word keyword mapping (French NL → TokenType) ────────────────────
KEYWORDS: dict[str, TokenType] = {
    # ── Query intent verbs ───────────────────────────────────────
    "affiche":      TokenType.SHOW,
    "afficher":     TokenType.SHOW,
    "montre":       TokenType.SHOW,
    "montrer":      TokenType.SHOW,
    "donne":        TokenType.SHOW,
    "donner":       TokenType.SHOW,
    "liste":        TokenType.SHOW,
    "lister":       TokenType.SHOW,
    "quels":        TokenType.SHOW,
    "quelles":      TokenType.SHOW,
    "quel":         TokenType.SHOW,
    "quelle":       TokenType.SHOW,
    "retourne":     TokenType.SHOW,
    "cherche":      TokenType.SHOW,
    "trouve":       TokenType.SHOW,
    "sélectionne":  TokenType.SELECT,
    "selectionne":  TokenType.SELECT,
    "sélectionner": TokenType.SELECT,
    "selectionner": TokenType.SELECT,

    # ── Count ────────────────────────────────────────────────────
    "combien":      TokenType.COUNT,
    "nombre":       TokenType.COUNT,
    "compte":       TokenType.COUNT,
    "compter":      TokenType.COUNT,

    # ── CRUD verbs ───────────────────────────────────────────────
    "supprimer":    TokenType.DELETE,
    "supprime":     TokenType.DELETE,
    "effacer":      TokenType.DELETE,
    "efface":       TokenType.DELETE,
    "retirer":      TokenType.DELETE,
    "retire":       TokenType.DELETE,
    "modifier":     TokenType.UPDATE,
    "modifie":      TokenType.UPDATE,
    "changer":      TokenType.UPDATE,
    "change":       TokenType.UPDATE,
    "ajouter":      TokenType.INSERT,
    "ajoute":       TokenType.INSERT,
    "insérer":      TokenType.INSERT,
    "inserer":      TokenType.INSERT,
    "créer":        TokenType.INSERT,
    "creer":        TokenType.INSERT,

    # ── Aggregations ─────────────────────────────────────────────
    "moyenne":      TokenType.AVG,
    "moyen":        TokenType.AVG,
    "maximum":      TokenType.MAX,
    "max":          TokenType.MAX,
    "minimum":      TokenType.MIN,
    "min":          TokenType.MIN,
    "somme":        TokenType.SUM,
    "total":        TokenType.SUM,

    # ── Filter keywords ──────────────────────────────────────────
    "où":           TokenType.WHERE,
    "avec":         TokenType.WHERE,
    "dont":         TokenType.WHERE,
    "ayant":        TokenType.WHERE,
    "qui":          TokenType.WHERE,
    "ont":          TokenType.WHERE,
    "sont":         TokenType.WHERE,

    # ── Negation ─────────────────────────────────────────────────
    "ne":           TokenType.NEG,
    "pas":          TokenType.NEG,
    "non":          TokenType.NEG,
    "sauf":         TokenType.NEG,
    "sans":         TokenType.NEG,
    "ni":           TokenType.NEG,

    # ── Ordering ─────────────────────────────────────────────────
    "trie":         TokenType.ORDER,
    "triés":        TokenType.ORDER,
    "triées":       TokenType.ORDER,
    "classe":       TokenType.ORDER,
    "ordonne":      TokenType.ORDER,
    "order":        TokenType.ORDER,
    "plus":         TokenType.DESC_ORDER,
    "économique":   TokenType.ASC_ORDER,
    "économiques":  TokenType.ASC_ORDER,
    "economique":   TokenType.ASC_ORDER,
    "economiques":  TokenType.ASC_ORDER,
    "ascendant":    TokenType.ASC_ORDER,
    "descendant":   TokenType.DESC_ORDER,
    "décroissant":  TokenType.DESC_ORDER,
    "croissant":    TokenType.ASC_ORDER,

    # ── Limit ────────────────────────────────────────────────────
    "premiers":     TokenType.LIMIT,
    "derniers":     TokenType.LIMIT,
    "premières":    TokenType.LIMIT,
    "dernières":    TokenType.LIMIT,
    "limite":       TokenType.LIMIT,
    "top":          TokenType.LIMIT,

    # ── Grouping ─────────────────────────────────────────────────
    "par":          TokenType.GROUP,
    "groupé":       TokenType.GROUP,
    "groupés":      TokenType.GROUP,
    "groupées":     TokenType.GROUP,

    # ── Entities (tables) ────────────────────────────────────────
    "capteur":      TokenType.CAPTEURS,
    "capteurs":     TokenType.CAPTEURS,
    "sensor":       TokenType.CAPTEURS,
    "sensors":      TokenType.CAPTEURS,
    "intervention": TokenType.INTERVENTIONS,
    "interventions": TokenType.INTERVENTIONS,
    "citoyen":      TokenType.CITOYENS,
    "citoyens":     TokenType.CITOYENS,
    "véhicule":     TokenType.VEHICULES,
    "vehicule":     TokenType.VEHICULES,
    "véhicules":    TokenType.VEHICULES,
    "vehicules":    TokenType.VEHICULES,
    "mesure":       TokenType.MESURES,
    "mesures":      TokenType.MESURES,
    "zone":         TokenType.ZONES,
    "zones":        TokenType.ZONES,
    "trajet":       TokenType.TRAJETS,
    "trajets":      TokenType.TRAJETS,

    # ── Columns / attributes ─────────────────────────────────────
    "statut":       TokenType.STATUT,
    "état":         TokenType.STATUT,
    "etat":         TokenType.STATUT,
    "status":       TokenType.STATUT,
    "pollution":    TokenType.POLLUTION,
    "polluées":     TokenType.POLLUTION,
    "polluée":      TokenType.POLLUTION,
    "pollués":      TokenType.POLLUTION,
    "pollué":       TokenType.POLLUTION,
    "polluant":     TokenType.POLLUTION,
    "score":        TokenType.SCORE_ECOLO,
    "écologique":   TokenType.SCORE_ECOLO,
    "ecologique":   TokenType.SCORE_ECOLO,
    "écolo":        TokenType.SCORE_ECOLO,
    "ecolo":        TokenType.SCORE_ECOLO,
    "nom":          TokenType.NOM,
    "type":         TokenType.TYPE,
    "co2":          TokenType.ECO_CO2,
    "erreur":       TokenType.TAUX_ERREUR,
    "taux":         TokenType.TAUX_ERREUR,

    # ── Comparators ──────────────────────────────────────────────
    "supérieur":    TokenType.GT,
    "superieur":    TokenType.GT,
    "inférieur":    TokenType.LT,
    "inferieur":    TokenType.LT,
    "égal":         TokenType.EQ,
    "egal":         TokenType.EQ,
    "est":          TokenType.EQ,
    "différent":    TokenType.NEQ,
    "different":    TokenType.NEQ,

    # ── Logical connectors ───────────────────────────────────────
    "et":           TokenType.AND,
    "ou":           TokenType.OR,

    # ── Status values ────────────────────────────────────────────
    "actif":        TokenType.STATUS_VAL,
    "actifs":       TokenType.STATUS_VAL,
    "active":       TokenType.STATUS_VAL,
    "actives":      TokenType.STATUS_VAL,
    "inactif":      TokenType.STATUS_VAL,
    "inactifs":     TokenType.STATUS_VAL,
    "inactive":     TokenType.STATUS_VAL,
    "inactives":    TokenType.STATUS_VAL,
    "signalé":      TokenType.STATUS_VAL,
    "signale":      TokenType.STATUS_VAL,
    "signalés":     TokenType.STATUS_VAL,
    "signales":     TokenType.STATUS_VAL,
    "maintenance":  TokenType.STATUS_VAL,
    "arrivé":       TokenType.STATUS_VAL,
    "arrive":       TokenType.STATUS_VAL,
    "terminé":      TokenType.STATUS_VAL,
    "termine":      TokenType.STATUS_VAL,
    "terminée":     TokenType.STATUS_VAL,
    "terminées":    TokenType.STATUS_VAL,
    "stationné":    TokenType.STATUS_VAL,
    "stationne":    TokenType.STATUS_VAL,
    "assigné":      TokenType.STATUS_VAL,
    "assigne":      TokenType.STATUS_VAL,
    "validé":       TokenType.STATUS_VAL,
    "valide":       TokenType.STATUS_VAL,
    "demande":      TokenType.STATUS_VAL,
}

# ── Status value normalization ─────────────────────────────────────────────
STATUS_NORMALIZE = {
    "hors service":  "hors_service",
    "hors_service":  "hors_service",
    "en route":      "en_route",
    "en_route":      "en_route",
    "en panne":      "en_panne",
    "en_panne":      "en_panne",
    "en cours":      "en_cours",
    "en_cours":      "en_cours",
    "signalé":       "signale",
    "signale":       "signale",
    "signalés":      "signale",
    "signales":      "signale",
    "actifs":        "actif",
    "actif":         "actif",
    "active":        "actif",
    "actives":       "actif",
    "inactif":       "inactif",
    "inactifs":      "inactif",
    "inactive":      "inactif",
    "inactives":     "inactif",
    "terminé":       "termine",
    "termine":       "termine",
    "terminée":      "termine",
    "terminées":     "termine",
    "arrivé":        "arrive",
    "arrive":        "arrive",
    "maintenance":   "en_maintenance",
    "stationné":     "stationne",
    "stationne":     "stationne",
    "assigné":       "assigne",
    "assigne":       "assigne",
    "validé":        "valide",
    "valide":        "valide",
    "demande":       "demande",
}


class LexerError(Exception):
    """Raised when the lexer encounters an unrecoverable issue."""
    def __init__(self, message: str, pos: int, query: str = ""):
        self.pos = pos
        self.query = query
        self.detail = message
        arrow = self._build_arrow(query, pos) if query else ""
        super().__init__(f"Erreur lexicale à la position {pos}: {message}\n{arrow}")

    @staticmethod
    def _build_arrow(query: str, pos: int) -> str:
        """Build an error arrow pointing to the problematic position."""
        safe_pos = min(pos, len(query))
        return f"  {query}\n  {' ' * safe_pos}^--- ici"


class Lexer:
    """
    Tokenize a French natural-language query into a list of Token objects.

    Strategy:
      1. Try multi-word phrases first (longest match).
      2. Try comparator symbols (>, <, >=, <=, !=, =).
      3. Try numbers.
      4. Try quoted strings.
      5. Fall back to single-word keyword lookup.
      6. Unknown words are kept for context.
    """

    def __init__(self, text: str):
        self.text = text.strip()
        self.original = text.strip()
        self.pos = 0
        self.tokens: List[Token] = []

    def _remaining(self) -> str:
        return self.text[self.pos:]

    def _skip_whitespace(self):
        while self.pos < len(self.text) and self.text[self.pos] in (" ", "\t", "\n"):
            self.pos += 1

    def _try_comparator_symbol(self) -> Optional[Token]:
        """Match >=, <=, !=, >, <, = symbols."""
        remaining = self._remaining()
        for symbol, ttype in [(">=", TokenType.GTE), ("<=", TokenType.LTE),
                               ("!=", TokenType.NEQ), (">", TokenType.GT),
                               ("<", TokenType.LT), ("=", TokenType.EQ)]:
            if remaining.startswith(symbol):
                tok = Token(ttype, symbol, self.pos)
                self.pos += len(symbol)
                return tok
        return None

    def _try_number(self) -> Optional[Token]:
        m = re.match(r"\d+(?:\.\d+)?", self._remaining())
        if m:
            tok = Token(TokenType.NUMBER, m.group(), self.pos)
            self.pos += len(m.group())
            return tok
        return None

    def _try_string(self) -> Optional[Token]:
        m = re.match(r"""['"](([^'"]+))['"]""", self._remaining())
        if m:
            tok = Token(TokenType.STRING, m.group(1), self.pos)
            self.pos += len(m.group())
            return tok
        return None

    def _try_multi_word(self) -> Optional[Token]:
        """Try matching multi-word phrases (longest first)."""
        remaining_lower = self._remaining().lower()

        # Sort by phrase length (longest first) for greedy matching
        for phrase, ttype in sorted(MULTI_WORD_KEYWORDS.items(),
                                      key=lambda x: len(x[0]), reverse=True):
            if remaining_lower.startswith(phrase):
                # Verify word boundary after the phrase
                end_pos = len(phrase)
                if end_pos < len(remaining_lower) and remaining_lower[end_pos].isalpha():
                    continue  # Not a word boundary, skip
                raw = self._remaining()[:end_pos]
                norm = STATUS_NORMALIZE.get(phrase, phrase)
                tok = Token(ttype, norm, self.pos)
                self.pos += len(raw)
                return tok
        return None

    def _try_word(self) -> Optional[Token]:
        """Match a single word and look it up in keywords."""
        m = re.match(r"[^\s,?!;:«»\"'>=<]+", self._remaining())
        if not m:
            return None
        raw = m.group()
        word_lower = raw.lower().rstrip(".,?!")
        if word_lower in KEYWORDS:
            ttype = KEYWORDS[word_lower]
            val = STATUS_NORMALIZE.get(word_lower, word_lower)
            tok = Token(ttype, val, self.pos)
        else:
            tok = Token(TokenType.UNKNOWN, raw, self.pos)
        self.pos += len(raw)
        return tok

    def tokenize(self) -> List[Token]:
        """Tokenize the input text into a list of tokens."""
        while self.pos < len(self.text):
            self._skip_whitespace()
            if self.pos >= len(self.text):
                break

            # Skip punctuation characters (but NOT comparison operators)
            if self.text[self.pos] in "?,!;:«»()":
                self.pos += 1
                continue

            tok = (
                self._try_multi_word()
                or self._try_comparator_symbol()
                or self._try_number()
                or self._try_string()
                or self._try_word()
            )
            if tok:
                self.tokens.append(tok)
            else:
                # Skip unknown single character
                self.pos += 1

        self.tokens.append(Token(TokenType.EOF, "", self.pos))
        return self.tokens


# ── Quick smoke-test ───────────────────────────────────────────────────────────
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
        "Capteurs signalé",
    ]
    for q in queries:
        print(f"\nQuery: {q}")
        lexer = Lexer(q)
        for tok in lexer.tokenize():
            if tok.type != TokenType.EOF:
                print(f"  {tok}")