"""
AI Generative Report Module — Smart City Platform
Uses Groq API (OpenAI-compatible) to:
  1. Generate textual reports from database query results
  2. Suggest actions to urban managers
  3. Validate FSM automata transitions (advanced bonus)
"""
import os
import json
import datetime
from typing import Any, Dict, List, Optional, Tuple

from openai import OpenAI

# ── Client setup ──────────────────────────────────────────────────────────────
# API key is injected via GROQ_API_KEY env var — do NOT hardcode here.
_client: Optional[OpenAI] = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. "
                "Get a free key at https://console.groq.com and add it to your .env file."
            )
        _client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
    return _client


MODEL = "llama-3.3-70b-versatile"

SYSTEM_PROMPT = """Tu es un assistant expert en gestion urbaine intelligente pour la métropole Neo-Sousse 2030.
Tu analyses des données urbaines (capteurs, interventions, citoyens, véhicules, mesures de pollution)
et génères des rapports professionnels clairs, des alertes prioritaires, et des recommandations d'action.
Réponds toujours en français. Sois précis, factuel, et concis. Utilise des sections claires avec des titres courts.
Utilise du markdown pour structurer tes réponses (titres ##, listes -, gras **texte**)."""


def _chat(prompt: str, max_tokens: int = 1500) -> str:
    """Send a chat completion request to Groq and return the text."""
    response = _get_client().chat.completions.create(
        model=MODEL,
        max_tokens=max_tokens,
        temperature=0.7,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content or ""


# ── Report generation ─────────────────────────────────────────────────────────

def generate_report(
    report_type: str,
    data: List[Dict[str, Any]],
    context: Optional[str] = None,
    date: Optional[str] = None,
) -> str:
    """
    Generate a professional urban management report.

    Parameters
    ----------
    report_type : one of 'air_quality' | 'sensors' | 'interventions' | 'citizens' | 'vehicles' | 'general'
    data        : list of dicts from DB query
    context     : optional additional context string
    date        : report date string (default: today)
    """
    date = date or datetime.date.today().strftime("%d/%m/%Y")

    # Serialize data (limit to 50 rows for prompt size)
    data_str = json.dumps(data[:50], ensure_ascii=False, indent=2, default=str)

    type_labels = {
        "air_quality":    "Qualité de l'air",
        "sensors":        "État des capteurs",
        "interventions":  "Interventions en cours",
        "citizens":       "Scores écologiques citoyens",
        "vehicles":       "Trajets véhicules autonomes",
        "general":        "Tableau de bord général",
    }
    label = type_labels.get(report_type, "Rapport urbain")

    prompt = f"""Génère un rapport professionnel de type "{label}" pour la date du {date}.

Données disponibles :
{data_str}

{"Contexte additionnel : " + context if context else ""}

Structure attendue :
1. **Résumé exécutif** (2-3 phrases)
2. **Points clés** (liste à puces avec les observations importantes)
3. **Alertes** (si des seuils sont dépassés ou des anomalies détectées)
4. **Recommandations** (actions concrètes pour les gestionnaires)

Sois factuel et base-toi uniquement sur les données fournies."""

    return _chat(prompt)


# ── Action suggestions ────────────────────────────────────────────────────────

def suggest_actions(
    entity_type: str,
    entity_id: str,
    current_state: str,
    metrics: Dict[str, Any],
) -> str:
    """
    Suggest concrete actions for a given entity based on its current state and metrics.

    Example: suggest_actions('capteur', 'C-452', 'SIGNALÉ', {'taux_erreur': 0.15})
    → "Intervention recommandée sur le capteur C-452 : taux d'erreur de 15%"
    """
    metrics_str = json.dumps(metrics, ensure_ascii=False, default=str)

    prompt = f"""Analyse la situation suivante et suggère des actions concrètes pour les gestionnaires urbains :

Entité : {entity_type} (ID: {entity_id})
État actuel : {current_state}
Métriques : {metrics_str}

Fournis :
1. Une alerte claire si nécessaire (ex: "⚠ Intervention urgente requise")
2. Les actions recommandées (liste numérotée, ordonnée par priorité)
3. Le délai d'intervention suggéré

Sois direct et pratique."""

    return _chat(prompt)


# ── FSM transition validation (advanced bonus) ────────────────────────────────

def validate_fsm_transition(
    entity_type: str,
    entity_id: str,
    from_state: str,
    event: str,
    to_state: str,
    context: Optional[str] = None,
    is_formally_valid: bool = True,
) -> Tuple[bool, str]:
    """
    Use AI to validate whether a FSM transition is semantically reasonable,
    even if it is technically valid in the DFA.
    Returns (approved: bool, reasoning: str).
    """
    prompt = f"""Tu es un validateur intelligent expert pour des automates d'états finis (DFA) dans le contexte d'une plateforme Smart City (Neo-Sousse 2030).

Entité : {entity_type} (ID: {entity_id})
Transition demandée : {from_state} --[{event}]--> {to_state}
Validité formelle selon le moteur d'automate (DFA) : {"VALIDE" if is_formally_valid else "INVALIDE (Cette transition n'existe pas dans les règles strictes de l'automate)"}

{"--- CONTEXTE ET DONNÉES ---" + chr(10) + context if context else ""}

Tu dois analyser cette transition sous QUATRE angles :

### 1. Cohérence formelle
- La transition est-elle techniquement valide dans l'automate ? 
- IMPORTANT: Puisque le moteur d'automate a évalué la validité formelle à {"VALIDE" if is_formally_valid else "INVALIDE"}, tu DOIS {"l'accepter sur le plan formel" if is_formally_valid else "la REJETER catégoriquement (approved: false)"}.
- L'événement "{event}" est-il approprié pour déclencher le passage de "{from_state}" à "{to_state}" ?

### 2. Logique métier
- Cette transition a-t-elle du sens dans le contexte opérationnel urbain ?
- Les données disponibles (taux d'erreur, mesures, historique) justifient-elles cette transition ?

### 3. Sécurité et risques
- Cette transition pose-t-elle un risque pour les citoyens ou l'infrastructure ?

### 4. Recommandations
- Si la transition est valide : confirme et indique les prochaines étapes recommandées
- Si la transition est invalide (formellement ou métier) : explique pourquoi et suggère des actions correctives ou des transitions alternatives

Réponds UNIQUEMENT avec ce format JSON strict, rien d'autre avant ni après :
{{"approved": true/false, "confidence": 0.0-1.0, "reasoning": "Ton analyse détaillée en markdown avec sections claires"}}"""

    text = _chat(prompt, max_tokens=1500).strip()

    # Extract JSON part using regex to remove any prefix/suffix
    import re
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        json_str = match.group(0)
    else:
        json_str = text

    try:
        result = json.loads(json_str)
        return result.get("approved", is_formally_valid), result.get("reasoning", "")
    except json.JSONDecodeError:
        # Fallback if JSON parsing fails
        approved = "true" in text.lower() or "approuvé" in text.lower()
        if not is_formally_valid:
            approved = False
            
        reasoning = text
        if '"reasoning":' in text:
            try:
                reasoning = text.split('"reasoning":')[1].strip()
                if reasoning.startswith('"') or reasoning.startswith("'"):
                    reasoning = reasoning[1:-1]
                reasoning = reasoning.rstrip('}')
            except Exception:
                pass
                
        return approved, reasoning


# ── Quick summary for dashboard ───────────────────────────────────────────────

def quick_summary(data_snapshot: Dict[str, Any]) -> str:
    """
    Generate a one-paragraph executive summary from a dashboard data snapshot.
    Used for the real-time dashboard header.
    """
    prompt = f"""Génère un résumé exécutif en 3 phrases maximum pour ce tableau de bord Smart City :

{json.dumps(data_snapshot, ensure_ascii=False, indent=2, default=str)}

Format : paragraphe court, style professionnel, commence par la date/heure."""

    return _chat(prompt, max_tokens=500)


# ── Status report (full dashboard) ────────────────────────────────────────────

def generate_status_report(data: Dict[str, Any]) -> str:
    """
    Generate a comprehensive status report from aggregated dashboard data.
    Includes sensors, interventions, air quality, vehicles summary.
    """
    data_str = json.dumps(data, ensure_ascii=False, indent=2, default=str)
    date = datetime.date.today().strftime("%d/%m/%Y")

    prompt = f"""Génère un rapport de statut complet pour la plateforme Smart City Neo-Sousse en date du {date}.

Données agrégées du tableau de bord :
{data_str}

Structure du rapport :
1. **📊 Résumé Exécutif** — Vue d'ensemble en 3-4 phrases
2. **🔧 État des Capteurs** — Analyse du parc de capteurs (actifs, en panne, signalés)
3. **🚨 Alertes & Anomalies** — Points critiques nécessitant attention immédiate
4. **🌿 Qualité Environnementale** — Pollution, température, bruit
5. **🚗 Mobilité** — État de la flotte véhicules autonomes
6. **📋 Interventions** — État des interventions en cours
7. **✅ Recommandations Prioritaires** — Top 5 actions à entreprendre

Sois factuel, précis, utilise des chiffres concrets issus des données."""

    return _chat(prompt, max_tokens=2000)


# ── Smoke test ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # Test with mock data (no real DB needed)
    mock_sensor_data = [
        {"id": "C-001", "zone": "Zone A", "statut": "SIGNALÉ", "taux_erreur": 0.15},
        {"id": "C-002", "zone": "Zone B", "statut": "ACTIF",   "taux_erreur": 0.02},
        {"id": "C-003", "zone": "Zone C", "statut": "HORS_SERVICE", "taux_erreur": 0.42},
    ]

    print("=== Rapport capteurs ===")
    report = generate_report("sensors", mock_sensor_data)
    print(report)

    print("\n=== Action suggérée ===")
    suggestion = suggest_actions(
        "capteur", "C-452", "SIGNALÉ",
        {"taux_erreur": 0.15, "derniere_mesure": "2026-03-15T10:30:00", "zone": "Zone Nord"}
    )
    print(suggestion)

    print("\n=== Validation FSM ===")
    approved, reason = validate_fsm_transition(
        "capteur", "C-001", "ACTIF", "panne", "HORS_SERVICE",
        "Capteur dans une zone critique avec 3 alertes consécutives"
    )
    print(f"Approved: {approved}, Reason: {reason}")
