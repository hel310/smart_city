"""
Tableau de Bord — Neo-Sousse 2030 Smart City
============================================
Streamlit frontend avec:
  - Compilateur NL → SQL interactif
  - Visualisation D3.js des automates FSM
  - Graphiques Plotly (pollution, séries temporelles)
  - Rapports IA
  - Gestion des états FSM en temps réel
"""

import streamlit as st
import httpx
import json
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
import time

# ── Config ──────────────────────────────────────────────────
st.set_page_config(
    page_title="Neo-Sousse 2030",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

API_BASE = "http://localhost:8000"


# ── Styling ─────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');

  html, body, [class*="css"] {
    font-family: 'Space Grotesk', sans-serif;
  }

  .main { background: #0a0f1e; color: #e2e8f0; }

  .metric-card {
    background: linear-gradient(135deg, #1e2a45 0%, #162236 100%);
    border: 1px solid #2d3f5e;
    border-radius: 12px;
    padding: 1.2rem;
    text-align: center;
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  }
  .metric-val {
    font-size: 2.2rem;
    font-weight: 700;
    color: #60a5fa;
    line-height: 1;
  }
  .metric-label {
    font-size: 0.8rem;
    color: #94a3b8;
    margin-top: 0.3rem;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .sql-block {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 1rem;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.85rem;
    color: #79c0ff;
    white-space: pre-wrap;
  }
  .token-badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    font-family: monospace;
    margin: 2px;
  }
  .ast-node {
    background: #1a2744;
    border-left: 3px solid #3b82f6;
    padding: 0.5rem 1rem;
    border-radius: 0 8px 8px 0;
    margin: 0.3rem 0;
    font-size: 0.85rem;
  }
  .alert-box {
    background: #1f1207;
    border: 1px solid #f59e0b;
    border-radius: 8px;
    padding: 0.8rem 1rem;
    color: #fcd34d;
  }
  .suggestion-card {
    background: #0f2a1a;
    border: 1px solid #22c55e;
    border-radius: 8px;
    padding: 0.8rem;
    margin: 0.4rem 0;
    font-size: 0.9rem;
  }
  .stButton > button {
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.2s;
  }
  .stButton > button:hover {
    background: linear-gradient(135deg, #3b82f6, #2563eb);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(59,130,246,0.4);
  }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: #0d1627;
    border-right: 1px solid #1e2d4a;
  }
  [data-testid="stSidebar"] .stSelectbox label,
  [data-testid="stSidebar"] p {
    color: #94a3b8 !important;
  }
</style>
""", unsafe_allow_html=True)


# ── API helpers ──────────────────────────────────────────────
@st.cache_data(ttl=10)
def api_get(path: str, params: dict = None) -> dict:
    try:
        r = httpx.get(f"{API_BASE}{path}", params=params, timeout=10)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


def api_post(path: str, data: dict) -> dict:
    try:
        r = httpx.post(f"{API_BASE}{path}", json=data, timeout=30)
        return r.json()
    except Exception as e:
        return {"error": str(e)}


# ── Token color map ──────────────────────────────────────────
TOKEN_COLORS = {
    "AFFICHE": "#3b82f6", "COMBIEN": "#3b82f6", "QUEL": "#3b82f6",
    "ZONES": "#22c55e", "CAPTEURS": "#22c55e", "CITOYENS": "#22c55e",
    "VEHICULES": "#22c55e", "TRAJETS": "#22c55e", "INTERVENTIONS": "#22c55e",
    "POLLUTION": "#f59e0b", "TEMPERATURE": "#f59e0b", "SCORE": "#f59e0b",
    "STATUT": "#f59e0b", "TAUX_ERREUR": "#f59e0b",
    "SUP": "#ef4444", "INF": "#ef4444", "EQ": "#ef4444",
    "NUMBER": "#a78bfa", "PREMIERS": "#6b7280", "LES": "#6b7280",
    "PLUS_POLLUEES": "#f97316", "EN_COURS": "#06b6d4",
}


# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🏙️ Neo-Sousse 2030")
    st.markdown("*Plateforme Smart City*")
    st.divider()

    page = st.radio(
        "Navigation",
        ["🏠 Tableau de Bord", "🔍 Compilateur NL→SQL", "⚙️ Automates FSM",
         "📊 Séries Temporelles", "🤖 Rapports IA", "🗄️ Données"],
        label_visibility="collapsed"
    )

    st.divider()
    # API status
    health = api_get("/api/health")
    if "error" not in health:
        st.success("✅ API connectée")
        if health.get("database") == "ok":
            st.success("✅ Base de données")
        else:
            st.error("❌ Base de données")
    else:
        st.error("❌ API hors ligne")
        st.caption(f"Démarrez: `uvicorn backend.main:app`")

    st.divider()
    st.caption("© 2026 Neo-Sousse Smart City")


# ══════════════════════════════════════════════════════════════
# PAGE 1: TABLEAU DE BORD
# ══════════════════════════════════════════════════════════════

if page == "🏠 Tableau de Bord":
    st.title("🏙️ Tableau de Bord — Neo-Sousse 2030")
    st.markdown("*Vue d'ensemble de la plateforme urbaine intelligente*")

    # KPIs
    stats = api_get("/api/stats/dashboard")
    if "error" not in stats:
        cols = st.columns(4)
        kpis = [
            ("total_capteurs",         "Total Capteurs",     "📡"),
            ("capteurs_actifs",        "Capteurs Actifs",    "✅"),
            ("capteurs_hors_service",  "Hors Service",       "🔴"),
            ("interventions_en_cours", "Interventions",      "🔧"),
        ]
        for col, (key, label, icon) in zip(cols, kpis):
            with col:
                st.markdown(f"""
                <div class="metric-card">
                  <div class="metric-val">{icon} {stats.get(key, 0)}</div>
                  <div class="metric-label">{label}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("")
        cols2 = st.columns(4)
        kpis2 = [
            ("citoyens_score_haut", "Score Écolo > 80", "🌿"),
            ("vehicules_en_route",  "Véhicules En Route", "🚗"),
            ("total_mesures",       "Mesures totales",    "📈"),
            ("zones_polluees",      "Zones > seuil",      "⚠️"),
        ]
        for col, (key, label, icon) in zip(cols2, kpis2):
            with col:
                val = stats.get(key, 0)
                if isinstance(val, int) and val > 1000:
                    val = f"{val:,}"
                st.markdown(f"""
                <div class="metric-card">
                  <div class="metric-val">{icon} {val}</div>
                  <div class="metric-label">{label}</div>
                </div>""", unsafe_allow_html=True)
    else:
        st.warning("Impossible de charger les statistiques. Vérifiez la connexion à l'API.")

    st.divider()

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("🌫️ Pollution par Zone")
        poll_data = api_get("/api/stats/pollution")
        if "data" in poll_data and poll_data["data"]:
            df = pd.DataFrame(poll_data["data"])
            fig = px.bar(
                df, x="zone", y="pollution_moy",
                color="pollution_moy",
                color_continuous_scale=["#22c55e", "#f59e0b", "#ef4444"],
                title="",
                labels={"pollution_moy": "Pollution moy. (µg/m³)", "zone": "Zone"},
                template="plotly_dark",
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                coloraxis_showscale=False,
                margin=dict(l=0, r=0, t=10, b=0),
                height=300,
            )
            fig.add_hline(y=50, line_dash="dash", line_color="#f59e0b",
                          annotation_text="Seuil OMS (50 µg/m³)")
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune donnée de pollution disponible.")

    with col_right:
        st.subheader("📡 État des Capteurs")
        cap_data = api_get("/api/stats/capteurs")
        if "data" in cap_data and cap_data["data"]:
            df_cap = pd.DataFrame(cap_data["data"])
            color_map = {
                "ACTIF": "#22c55e", "INACTIF": "#6b7280",
                "HORS_SERVICE": "#ef4444", "SIGNALE": "#f59e0b",
                "EN_MAINTENANCE": "#3b82f6",
            }
            colors = [color_map.get(s, "#94a3b8") for s in df_cap["statut"]]
            fig2 = go.Figure(go.Pie(
                labels=df_cap["statut"],
                values=df_cap["total"],
                marker_colors=colors,
                hole=0.5,
                textinfo="label+value",
                textfont_size=11,
            ))
            fig2.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=0, r=0, t=10, b=0),
                height=300,
                showlegend=False,
                template="plotly_dark",
            )
            st.plotly_chart(fig2, use_container_width=True)

    # Interventions
    st.subheader("🔧 Interventions par Statut")
    iv_data = api_get("/api/stats/interventions")
    if "data" in iv_data and iv_data["data"]:
        df_iv = pd.DataFrame(iv_data["data"])
        fig3 = px.bar(
            df_iv, x="statut", y="total",
            color="statut",
            color_discrete_map={
                "DEMANDE": "#6b7280", "TECH_ASSIGN": "#3b82f6",
                "TECH_VALID": "#8b5cf6", "IA_VALID": "#f59e0b", "TERMINE": "#22c55e"
            },
            template="plotly_dark",
        )
        fig3.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=10, b=0),
            height=250,
            showlegend=False,
        )
        st.plotly_chart(fig3, use_container_width=True)


# ══════════════════════════════════════════════════════════════
# PAGE 2: COMPILATEUR NL → SQL
# ══════════════════════════════════════════════════════════════

elif page == "🔍 Compilateur NL→SQL":
    st.title("🔍 Compilateur Langage Naturel → SQL")
    st.markdown("*Saisissez une requête en français — le compilateur la traduit en SQL et l'exécute.*")

    # Examples sidebar
    examples = api_get("/api/compiler/examples")
    example_list = [e["nl"] for e in examples.get("examples", [])]

    col_input, col_ex = st.columns([3, 1])

    with col_ex:
        st.markdown("**📝 Exemples**")
        for ex in example_list:
            if st.button(f"▶ {ex[:40]}…" if len(ex) > 40 else f"▶ {ex}",
                         key=ex, use_container_width=True):
                st.session_state["nl_input"] = ex

    with col_input:
        nl_text = st.text_area(
            "Requête en langage naturel",
            value=st.session_state.get("nl_input", ""),
            height=80,
            placeholder="Ex: Affiche les 5 zones les plus polluées",
        )
        execute_flag = st.checkbox("Exécuter sur la base de données", value=True)
        compile_btn = st.button("🚀 Compiler & Exécuter", type="primary")

    if compile_btn and nl_text.strip():
        with st.spinner("Compilation en cours…"):
            result = api_post("/api/compiler/compile", {
                "text": nl_text,
                "execute": execute_flag
            })

        # Ambiguity warning
        if result.get("ambiguous"):
            st.markdown(f"""
            <div class="alert-box">
              ⚠️ <strong>Requête ambiguë :</strong> {result.get('ambiguity_message','')}<br>
              <em>Clarifications possibles :</em>
            </div>""", unsafe_allow_html=True)
            for clari in result.get("clarifications", []):
                if st.button(f"→ {clari}", key=f"clari_{clari}"):
                    st.session_state["nl_input"] = clari
                    st.rerun()
            st.divider()

        # Error
        if result.get("error"):
            st.error(f"❌ {result['error']}")
            if result.get("suggestions"):
                st.markdown("**Suggestions :**")
                for s in result["suggestions"]:
                    st.markdown(f"- `{s}`")
        else:
            tabs = st.tabs(["🔤 Tokens", "🌳 AST", "💻 SQL", "📊 Résultats"])

            # Tokens tab
            with tabs[0]:
                st.markdown("**Flux de tokens (Lexer)**")
                token_html = ""
                for tok in result.get("tokens", []):
                    color = TOKEN_COLORS.get(tok["type"], "#64748b")
                    token_html += f'<span class="token-badge" style="background:{color}22;border:1px solid {color};color:{color}">{tok["type"]}<br><small>{tok["value"]}</small></span>'
                st.markdown(token_html, unsafe_allow_html=True)

            # AST tab
            with tabs[1]:
                st.markdown("**Arbre Syntaxique Abstrait (AST)**")
                ast = result.get("ast", {})
                if ast.get("type") == "SelectNode":
                    st.markdown(f"""
                    <div class="ast-node">🔷 <b>SelectNode</b></div>
                    <div class="ast-node" style="margin-left:1.5rem">📋 entity: <code>{ast.get('entity')}</code></div>
                    <div class="ast-node" style="margin-left:1.5rem">📌 columns: <code>{ast.get('columns')}</code></div>
                    <div class="ast-node" style="margin-left:1.5rem">🔢 limit: <code>{ast.get('limit')}</code></div>
                    <div class="ast-node" style="margin-left:1.5rem">📊 aggregate: <code>{ast.get('aggregate')}</code></div>
                    <div class="ast-node" style="margin-left:1.5rem">⬆️ order_by: <code>{ast.get('order_by')} {ast.get('order_dir')}</code></div>
                    """, unsafe_allow_html=True)
                    for cond in ast.get("conditions", []):
                        st.markdown(f"""
                        <div class="ast-node" style="margin-left:3rem">
                          🔍 ConditionNode: <code>{cond['column']} {cond['operator']} {cond['value']}</code>
                        </div>""", unsafe_allow_html=True)
                else:
                    st.json(ast)

            # SQL tab
            with tabs[2]:
                st.markdown("**SQL Généré**")
                st.markdown(
                    f'<div class="sql-block">{result.get("sql", "—")}</div>',
                    unsafe_allow_html=True
                )
                st.code(result.get("sql", ""), language="sql")

            # Results tab
            with tabs[3]:
                if "db_error" in result:
                    st.error(f"Erreur DB: {result['db_error']}")
                elif "rows" in result:
                    rows = result["rows"]
                    st.success(f"✅ {result.get('row_count', 0)} ligne(s) retournée(s)")
                    if rows:
                        df = pd.DataFrame(rows)
                        st.dataframe(df, use_container_width=True)

                        # Auto-chart if numeric columns
                        num_cols = df.select_dtypes("number").columns.tolist()
                        str_cols = df.select_dtypes("object").columns.tolist()
                        if num_cols and str_cols:
                            fig = px.bar(
                                df, x=str_cols[0], y=num_cols[0],
                                template="plotly_dark",
                                color=num_cols[0],
                                color_continuous_scale="blues",
                            )
                            fig.update_layout(
                                paper_bgcolor="rgba(0,0,0,0)",
                                height=300, margin=dict(l=0,r=0,t=20,b=0),
                            )
                            st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("Aucun résultat.")
                elif not execute_flag:
                    st.info("Cochez 'Exécuter' pour voir les résultats.")


# ══════════════════════════════════════════════════════════════
# PAGE 3: AUTOMATES FSM
# ══════════════════════════════════════════════════════════════

elif page == "⚙️ Automates FSM":
    st.title("⚙️ Automates à États Finis")
    st.markdown("*Visualisation et simulation des automates métier en temps réel*")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["🔵 Capteur", "🟢 Intervention", "🟠 Véhicule", "✅ Validateur"])

    graphs = api_get("/api/fsm/graphs")

    def render_fsm_d3(graph_data: dict, current_state: str = None, height: int = 350):
        """Render FSM graph using D3.js in Streamlit."""
        nodes_json = json.dumps(graph_data.get("nodes", []))
        links_json = json.dumps(graph_data.get("links", []))
        current_json = json.dumps(current_state or "")

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <script src="https://d3js.org/d3.v7.min.js"></script>
          <style>
            body {{ margin:0; background:#0a0f1e; font-family: monospace; }}
            svg {{ width:100%; height:{height}px; }}
            .link {{ stroke:#334155; stroke-width:2; fill:none; marker-end:url(#arrow); }}
            .link-label {{ fill:#94a3b8; font-size:10px; }}
            .node circle {{
              stroke-width: 2;
              cursor: pointer;
              transition: all 0.3s;
            }}
            .node text {{ fill:#e2e8f0; font-size:11px; font-weight:600; text-anchor:middle; }}
            .node.current circle {{
              stroke-width: 4 !important;
              filter: drop-shadow(0 0 8px currentColor);
            }}
            .legend {{ fill:#94a3b8; font-size:10px; }}
          </style>
        </head>
        <body>
        <svg id="fsm-svg"></svg>
        <script>
        const nodes = {nodes_json};
        const links = {links_json};
        const currentState = {current_json};

        const width = document.getElementById('fsm-svg').clientWidth || 700;
        const height = {height};

        const svg = d3.select('#fsm-svg')
          .attr('viewBox', `0 0 ${{width}} ${{height}}`);

        // Arrow marker
        svg.append('defs').append('marker')
          .attr('id', 'arrow')
          .attr('viewBox', '0 -5 10 10')
          .attr('refX', 28)
          .attr('refY', 0)
          .attr('markerWidth', 6)
          .attr('markerHeight', 6)
          .attr('orient', 'auto')
          .append('path')
          .attr('d', 'M0,-5L10,0L0,5')
          .attr('fill', '#475569');

        // Force simulation
        const simulation = d3.forceSimulation(nodes)
          .force('link', d3.forceLink(links).id(d => d.id).distance(160))
          .force('charge', d3.forceManyBody().strength(-600))
          .force('center', d3.forceCenter(width/2, height/2))
          .force('collision', d3.forceCollide(50));

        const link = svg.append('g')
          .selectAll('path')
          .data(links)
          .join('path')
          .attr('class', 'link');

        const linkLabel = svg.append('g')
          .selectAll('text')
          .data(links)
          .join('text')
          .attr('class', 'link-label')
          .text(d => d.label);

        const node = svg.append('g')
          .selectAll('g')
          .data(nodes)
          .join('g')
          .attr('class', d => 'node' + (d.id === currentState ? ' current' : ''))
          .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));

        node.append('circle')
          .attr('r', 28)
          .attr('fill', d => d.id === currentState ? d.color : d.color + '33')
          .attr('stroke', d => d.color)
          .style('stroke-dasharray', d => d.id === currentState ? '0' : '4,2');

        node.append('text')
          .attr('dy', 4)
          .text(d => d.label.length > 12 ? d.label.substring(0,10)+'…' : d.label);

        if (currentState) {{
          // Pulse animation for current state
          const currentNode = node.filter(d => d.id === currentState);
          function pulse() {{
            currentNode.select('circle')
              .transition().duration(800).attr('r', 32)
              .transition().duration(800).attr('r', 28)
              .on('end', pulse);
          }}
          pulse();
        }}

        simulation.on('tick', () => {{
          link.attr('d', d => {{
            const dx = d.target.x - d.source.x;
            const dy = d.target.y - d.source.y;
            const dr = Math.sqrt(dx*dx + dy*dy) * 1.5;
            return `M${{d.source.x}},${{d.source.y}} A${{dr}},${{dr}} 0 0,1 ${{d.target.x}},${{d.target.y}}`;
          }});

          linkLabel
            .attr('x', d => (d.source.x + d.target.x)/2)
            .attr('y', d => (d.source.y + d.target.y)/2 - 8)
            .attr('text-anchor', 'middle');

          node.attr('transform', d => `translate(${{d.x}},${{d.y}})`);
        }});

        function dragstarted(event, d) {{
          if (!event.active) simulation.alphaTarget(0.3).restart();
          d.fx = d.x; d.fy = d.y;
        }}
        function dragged(event, d) {{ d.fx = event.x; d.fy = event.y; }}
        function dragended(event, d) {{
          if (!event.active) simulation.alphaTarget(0);
          d.fx = null; d.fy = null;
        }}
        </script>
        </body></html>
        """
        st.components.v1.html(html, height=height + 10, scrolling=False)

    # ── Capteur Tab ──────────────────────────────────────────
    with tab1:
        st.markdown("### 📡 Cycle de vie d'un Capteur")
        col_vis, col_ctrl = st.columns([2, 1])

        with col_ctrl:
            capteur_id = st.text_input("ID Capteur", value="C-001", key="cap_id")
            state_info = api_get(f"/api/fsm/state/capteur/{capteur_id}")
            current_state_cap = state_info.get("state", "INACTIF")
            st.info(f"**État actuel:** {current_state_cap}")
            if state_info.get("alert"):
                st.warning(state_info["alert"])

            st.markdown("**Déclencher un événement:**")
            events_cap = {
                "installer": "⚙️ Installer",
                "detecter_anomalie": "⚠️ Détecter anomalie",
                "signaler": "🚨 Signaler",
                "mettre_en_maintenance": "🔧 Mise en maintenance",
                "reparer": "✅ Réparer",
                "panne": "💥 Panne",
                "remettre_en_service": "🔄 Remettre en service",
            }
            selected_event = st.selectbox("Événement", list(events_cap.keys()),
                                          format_func=lambda x: events_cap[x])
            triggered_by = st.text_input("Déclenché par", value="gestionnaire", key="cap_by")

            if st.button("▶️ Appliquer", key="cap_apply", type="primary"):
                res = api_post("/api/fsm/event", {
                    "entity_type": "capteur",
                    "entity_id": capteur_id,
                    "event": selected_event,
                    "initial_state": current_state_cap,
                    "triggered_by": triggered_by,
                })
                if res.get("success"):
                    st.success(f"✅ {res['from']} → {res['to']}")
                    st.cache_data.clear()
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(f"❌ {res.get('error','Erreur')}")
                    valid = res.get("valid_events", [])
                    if valid:
                        st.caption(f"Événements valides: {', '.join(valid)}")

        with col_vis:
            if "capteur" in graphs:
                render_fsm_d3(graphs["capteur"], current_state_cap)
            st.markdown("""
            **Table de transition:**
            | État Source | Événement | État Cible |
            |---|---|---|
            | INACTIF | installer | ACTIF |
            | ACTIF | détecter_anomalie | SIGNALÉ |
            | ACTIF | panne | HORS_SERVICE |
            | SIGNALÉ | mettre_en_maintenance | EN_MAINTENANCE |
            | SIGNALÉ/EN_MAINT | réparer | ACTIF |
            | EN_MAINTENANCE | panne | HORS_SERVICE |
            | HORS_SERVICE | remettre_en_service | INACTIF |
            """)

    # ── Intervention Tab ─────────────────────────────────────
    with tab2:
        st.markdown("### 🔧 Processus de Validation d'Intervention")
        col_vis2, col_ctrl2 = st.columns([2, 1])

        with col_ctrl2:
            iv_id = st.number_input("ID Intervention", min_value=1, value=1, key="iv_id")
            state_info2 = api_get(f"/api/fsm/state/intervention/{iv_id}")
            current_state_iv = state_info2.get("state", "DEMANDE")
            st.info(f"**État actuel:** {current_state_iv}")

            events_iv = {
                "assigner_tech1": "👷 Assigner Tech 1",
                "valider_tech2": "👷 Valider Tech 2",
                "valider_ia": "🤖 Valider IA",
                "rejeter_ia": "❌ Rejeter IA",
                "terminer": "✅ Terminer",
                "annuler": "🚫 Annuler",
            }
            sel_ev2 = st.selectbox("Événement", list(events_iv.keys()),
                                   format_func=lambda x: events_iv[x], key="iv_ev")

            if st.button("▶️ Appliquer", key="iv_apply", type="primary"):
                res2 = api_post("/api/fsm/event", {
                    "entity_type": "intervention",
                    "entity_id": str(iv_id),
                    "event": sel_ev2,
                    "initial_state": current_state_iv,
                    "triggered_by": "gestionnaire",
                })
                if res2.get("success"):
                    st.success(f"✅ {res2['from']} → {res2['to']}")
                    st.cache_data.clear()
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(f"❌ {res2.get('error','Erreur')}")

        with col_vis2:
            if "intervention" in graphs:
                render_fsm_d3(graphs["intervention"], current_state_iv)

    # ── Véhicule Tab ─────────────────────────────────────────
    with tab3:
        st.markdown("### 🚗 Trajet d'un Véhicule Autonome")
        col_vis3, col_ctrl3 = st.columns([2, 1])

        with col_ctrl3:
            v_id = st.text_input("ID Véhicule", value="V-001", key="v_id")
            state_info3 = api_get(f"/api/fsm/state/vehicule/{v_id}")
            current_state_v = state_info3.get("state", "STATIONNE")
            st.info(f"**État actuel:** {current_state_v}")

            events_v = {
                "demarrer": "🚀 Démarrer",
                "arriver": "🏁 Arriver",
                "panne": "💥 Panne",
                "reparer": "🔧 Réparer",
                "stationner": "🅿️ Stationner",
            }
            sel_ev3 = st.selectbox("Événement", list(events_v.keys()),
                                   format_func=lambda x: events_v[x], key="v_ev")

            if st.button("▶️ Appliquer", key="v_apply", type="primary"):
                res3 = api_post("/api/fsm/event", {
                    "entity_type": "vehicule",
                    "entity_id": v_id,
                    "event": sel_ev3,
                    "initial_state": current_state_v,
                })
                if res3.get("success"):
                    st.success(f"✅ {res3['from']} → {res3['to']}")
                    st.cache_data.clear()
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error(f"❌ {res3.get('error','Erreur')}")

        with col_vis3:
            if "vehicule" in graphs:
                render_fsm_d3(graphs["vehicule"], current_state_v)

    # ── Sequence Validator Tab ───────────────────────────────
    with tab4:
        st.markdown("### ✅ Validateur de Séquence d'Événements")
        col_l, col_r = st.columns(2)
        with col_l:
            v_entity = st.selectbox("Type d'entité", ["capteur","intervention","vehicule"])
            v_initial = st.text_input("État initial (optionnel)", placeholder="Ex: INACTIF")
        with col_r:
            v_events_raw = st.text_area(
                "Séquence d'événements (un par ligne)",
                height=120,
                placeholder="installer\ndetect_anomalie\nmettre_en_maintenance\nreparer"
            )

        if st.button("✅ Valider la séquence", type="primary"):
            events_list = [e.strip() for e in v_events_raw.strip().split("\n") if e.strip()]
            payload = {"entity_type": v_entity, "events": events_list}
            if v_initial:
                payload["initial_state"] = v_initial
            result = api_post("/api/fsm/validate", payload)

            if result.get("valid"):
                st.success(f"✅ Séquence valide — État final: **{result['final_state']}**")
            else:
                st.error(f"❌ Séquence invalide — {result.get('error','')}")

            for step in result.get("steps", []):
                icon = "✅" if step["ok"] else "❌"
                st.markdown(f"`{step['from']}` --[**{step['event']}**]--> `{step['to']}` {icon}")


# ══════════════════════════════════════════════════════════════
# PAGE 4: SÉRIES TEMPORELLES
# ══════════════════════════════════════════════════════════════

elif page == "📊 Séries Temporelles":
    st.title("📊 Séries Temporelles (TimescaleDB)")
    st.markdown("*Analyse temporelle des mesures des capteurs*")

    col1, col2, col3 = st.columns(3)
    with col1:
        metric = st.selectbox("Métrique",
            ["pollution","temperature","humidite","bruit","co2_ppm"],
            format_func=lambda x: {
                "pollution": "🌫️ Pollution (µg/m³)",
                "temperature": "🌡️ Température (°C)",
                "humidite": "💧 Humidité (%)",
                "bruit": "🔊 Bruit (dB)",
                "co2_ppm": "💨 CO2 (ppm)",
            }.get(x, x)
        )
    with col2:
        zone_sel = st.selectbox("Zone", ["Toutes"] + [f"Zone {i}" for i in range(1,9)])
        zone_id = None if zone_sel == "Toutes" else int(zone_sel.split()[-1])
    with col3:
        hours = st.slider("Période (heures)", 1, 168, 24)

    ts_data = api_get("/api/stats/timeseries", {
        "metric": metric, "hours": hours,
        **({"zone_id": zone_id} if zone_id else {})
    })

    if "data" in ts_data and ts_data["data"]:
        df_ts = pd.DataFrame(ts_data["data"])
        df_ts["bucket"] = pd.to_datetime(df_ts["bucket"])
        df_ts = df_ts.sort_values("bucket")

        # Group by zone
        zones_available = df_ts["zone_id"].unique()
        if len(zones_available) > 1 and not zone_id:
            fig = px.line(
                df_ts, x="bucket", y="valeur_moy", color="zone_id",
                title=f"Évolution de {metric} par zone",
                template="plotly_dark",
                labels={"valeur_moy": metric, "bucket": "Heure", "zone_id": "Zone"},
            )
        else:
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=df_ts["bucket"], y=df_ts["valeur_max"],
                fill=None, mode='lines', line_color='rgba(239,68,68,0.3)',
                name="Max"
            ))
            fig.add_trace(go.Scatter(
                x=df_ts["bucket"], y=df_ts["valeur_min"],
                fill='tonexty', mode='lines',
                fillcolor='rgba(59,130,246,0.1)', line_color='rgba(59,130,246,0.3)',
                name="Min"
            ))
            fig.add_trace(go.Scatter(
                x=df_ts["bucket"], y=df_ts["valeur_moy"],
                mode='lines+markers', line_color='#3b82f6',
                name="Moyenne", line_width=2,
            ))
            fig.update_layout(
                title=f"Série temporelle — {metric} ({hours}h)",
                template="plotly_dark",
            )

        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(13,17,23,0.8)",
            height=400,
            margin=dict(l=0, r=0, t=40, b=0),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Stats
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            st.metric("Moyenne", f"{df_ts['valeur_moy'].mean():.2f}")
        with col_b:
            st.metric("Maximum", f"{df_ts['valeur_max'].max():.2f}")
        with col_c:
            st.metric("Minimum", f"{df_ts['valeur_min'].min():.2f}")
        with col_d:
            st.metric("Mesures", f"{df_ts['nb_mesures'].sum():,}")
    else:
        st.info("Aucune donnée disponible pour la période sélectionnée.")


# ══════════════════════════════════════════════════════════════
# PAGE 5: RAPPORTS IA
# ══════════════════════════════════════════════════════════════

elif page == "🤖 Rapports IA":
    st.title("🤖 Module d'IA Générative")
    st.markdown("*Rapports automatiques et suggestions intelligentes*")

    tab_rep, tab_sug = st.tabs(["📄 Générer un Rapport", "💡 Suggestions d'Actions"])

    with tab_rep:
        col_type, col_zone = st.columns(2)
        with col_type:
            rtype = st.selectbox("Type de rapport", [
                ("global", "🏙️ Rapport Global"),
                ("air_quality", "🌫️ Qualité de l'air"),
                ("interventions", "🔧 Interventions"),
                ("vehicles", "🚗 Véhicules"),
            ], format_func=lambda x: x[1])
        with col_zone:
            zone_rep = st.selectbox("Zone (optionnel)", ["Toutes"] + [f"Zone {i}" for i in range(1,9)])
            zone_id_rep = None if zone_rep == "Toutes" else int(zone_rep.split()[-1])

        if st.button("📄 Générer le rapport", type="primary"):
            with st.spinner("L'IA génère le rapport…"):
                report = api_post("/api/reports/generate", {
                    "report_type": rtype[0],
                    "zone_id": zone_id_rep,
                })

            if "content" in report:
                st.markdown("---")
                st.markdown(f"### 📋 {rtype[1]}")
                st.markdown(f"*Généré le {datetime.now().strftime('%d/%m/%Y à %H:%M')}*")
                st.markdown("---")
                st.markdown(report["content"])
                st.download_button(
                    "⬇️ Télécharger le rapport",
                    data=report["content"],
                    file_name=f"rapport_{rtype[0]}_{datetime.now().strftime('%Y%m%d_%H%M')}.txt",
                    mime="text/plain",
                )
            else:
                st.error("Erreur lors de la génération du rapport.")

    with tab_sug:
        st.markdown("*L'IA analyse l'état du système et suggère des actions prioritaires.*")

        if st.button("💡 Obtenir des suggestions", type="primary"):
            with st.spinner("Analyse en cours…"):
                suggestions = api_get("/api/reports/suggestions")

            if "suggestions" in suggestions:
                urgence_colors = {
                    "haute": "#ef4444", "moyenne": "#f59e0b", "basse": "#22c55e"
                }
                for sug in suggestions.get("suggestions", []):
                    color = urgence_colors.get(sug.get("urgence", "basse"), "#6b7280")
                    st.markdown(f"""
                    <div class="suggestion-card" style="border-color:{color}">
                      <b>#{sug['priorite']} — {sug['titre']}</b>
                      <span style="float:right;color:{color};font-size:0.8rem">
                        ● {sug.get('urgence','?').upper()}
                      </span><br>
                      <span style="color:#94a3b8">{sug['description']}</span>
                      {f'<br><small>Entité: <code>{sug["entite_id"]}</code></small>' if sug.get("entite_id") else ''}
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.error("Impossible d'obtenir les suggestions.")


# ══════════════════════════════════════════════════════════════
# PAGE 6: DONNÉES
# ══════════════════════════════════════════════════════════════

elif page == "🗄️ Données":
    st.title("🗄️ Explorateur de Données")

    table = st.selectbox("Table", [
        "capteurs","zones","citoyens","vehicules",
        "trajets","interventions","techniciens","mesures","fsm_events"
    ])
    limit = st.slider("Nombre de lignes", 10, 200, 50)

    if st.button("🔄 Charger", type="primary"):
        data = api_get(f"/api/data/{table}", {"limit": limit})
        if "rows" in data:
            df = pd.DataFrame(data["rows"])
            st.success(f"✅ {len(df)} lignes")
            st.dataframe(df, use_container_width=True)
        else:
            st.error(data.get("error", "Erreur"))

    # FSM Events history
    st.divider()
    st.subheader("📋 Historique des Événements FSM")
    ev_data = api_get("/api/fsm/events", {"limit": 20})
    if "events" in ev_data and ev_data["events"]:
        df_ev = pd.DataFrame(ev_data["events"])
        st.dataframe(df_ev, use_container_width=True)
    else:
        st.info("Aucun événement FSM enregistré.")
