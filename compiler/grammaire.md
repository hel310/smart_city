# Grammaire Formelle — Compilateur NL → SQL

## Neo-Sousse 2030 — Smart City Platform

> Ce document décrit la grammaire formelle du compilateur de langage naturel français
> vers SQL, utilisé dans la plateforme Smart City Neo-Sousse 2030.

---

## 1. Grammaire BNF (Backus-Naur Form)

```bnf
<requête>        ::= <intention> <entité> [<filtre>] [<tri>] [<limite>]
                   | <entité> [<filtre>] [<tri>] [<limite>]

<intention>      ::= <intention_select>
                   | <intention_count>
                   | <intention_aggregat>
                   | <intention_delete>
                   | <intention_update>
                   | <intention_insert>

<intention_select>   ::= "affiche" | "afficher" | "montre" | "montrer"
                       | "donne" | "donner" | "donne-moi" | "donne moi"
                       | "liste" | "lister"
                       | "quels" | "quelles" | "quel" | "quelle"
                       | "retourne" | "cherche" | "trouve"
                       | "sélectionne" | "selectionne"
                       | "sélectionner" | "selectionner"

<intention_count>    ::= "combien" | "nombre" | "compte" | "compter"

<intention_aggregat> ::= "moyenne" | "moyen"
                       | "maximum" | "max"
                       | "minimum" | "min"
                       | "somme" | "total"

<intention_delete>   ::= "supprimer" | "supprime"
                       | "effacer" | "efface"
                       | "retirer" | "retire"

<intention_update>   ::= "modifier" | "modifie"
                       | "changer" | "change"
                       | "mettre à jour" | "mettre a jour"
                       | "mise à jour" | "mise a jour"

<intention_insert>   ::= "ajouter" | "ajoute"
                       | "insérer" | "inserer"
                       | "créer" | "creer"

<entité>         ::= <entité_capteurs>
                   | <entité_interventions>
                   | <entité_citoyens>
                   | <entité_véhicules>
                   | <entité_mesures>
                   | <entité_zones>
                   | <entité_trajets>

<entité_capteurs>       ::= "capteur" | "capteurs" | "sensor" | "sensors"
<entité_interventions>  ::= "intervention" | "interventions"
<entité_citoyens>       ::= "citoyen" | "citoyens"
<entité_véhicules>      ::= "véhicule" | "vehicule" | "véhicules" | "vehicules"
<entité_mesures>        ::= "mesure" | "mesures"
<entité_zones>          ::= "zone" | "zones"
<entité_trajets>        ::= "trajet" | "trajets"

<filtre>         ::= [<mot_filtre>] [<négation>] <condition> {<connecteur> <condition>}

<mot_filtre>     ::= "où" | "avec" | "dont" | "ayant" | "qui" | "ont" | "sont"

<négation>       ::= "ne sont pas" | "n'est pas" | "n'ont pas"
                   | "ne sont plus" | "ne pas"
                   | "ne" | "pas" | "non" | "sauf" | "sans" | "ni"

<condition>      ::= [<négation>] <colonne> <comparateur> <valeur>
                   | [<négation>] <valeur_statut>

<colonne>        ::= <col_statut> | <col_pollution> | <col_score>
                   | <col_nom> | <col_type> | <col_co2>
                   | <col_erreur> | <col_zone>

<col_statut>     ::= "statut" | "état" | "etat" | "status"
<col_pollution>  ::= "pollution" | "polluées" | "polluée" | "pollués" | "pollué" | "polluant"
<col_score>      ::= "score" | "écologique" | "ecologique" | "écolo" | "ecolo"
<col_nom>        ::= "nom"
<col_type>       ::= "type"
<col_co2>        ::= "co2"
<col_erreur>     ::= "erreur" | "taux"
<col_zone>       ::= "zone"

<comparateur>    ::= <comp_sup> | <comp_inf> | <comp_supeq>
                   | <comp_infeq> | <comp_egal> | <comp_diff>
                   | <comp_symbole>

<comp_sup>       ::= "supérieur" | "superieur" | "plus grand"
<comp_inf>       ::= "inférieur" | "inferieur" | "moins grand"
<comp_egal>      ::= "égal" | "egal" | "est"
<comp_diff>      ::= "différent" | "different"
<comp_symbole>   ::= ">" | "<" | ">=" | "<=" | "=" | "!="

<valeur>         ::= <nombre> | <chaîne> | <valeur_statut>

<nombre>         ::= [0-9]+ ("." [0-9]+)?

<chaîne>         ::= "'" [^']+ "'" | '"' [^"]+ '"'

<valeur_statut>  ::= "actif" | "actifs" | "active" | "actives"
                   | "inactif" | "inactifs" | "inactive" | "inactives"
                   | "signalé" | "signale" | "signalés" | "signales"
                   | "hors service" | "hors_service"
                   | "en route" | "en_route"
                   | "en panne" | "en_panne"
                   | "en cours" | "en_cours"
                   | "maintenance" | "en_maintenance"
                   | "arrivé" | "arrive"
                   | "terminé" | "termine" | "terminée" | "terminées"
                   | "stationné" | "stationne"
                   | "demande"

<connecteur>     ::= "et" | "ou"

<tri>            ::= [<mot_tri>] <direction> [<colonne>]

<mot_tri>        ::= "trie" | "triés" | "triées" | "classe" | "ordonne" | "order"

<direction>      ::= <ascendant> | <descendant>

<ascendant>      ::= "ascendant" | "croissant"
                   | "économique" | "economique"
                   | "économiques" | "economiques"

<descendant>     ::= "descendant" | "décroissant"
                   | "plus" | "les plus"

<limite>         ::= <nombre> [<mot_limite>]
                   | <mot_limite> <nombre>

<mot_limite>     ::= "premiers" | "derniers" | "premières" | "dernières"
                   | "limite" | "top"
```

---

## 2. Architecture du Compilateur

```
┌─────────────────────────────────────────────────────┐
│                  Requête Utilisateur                │
│         "Capteurs qui ne sont pas actifs"           │
└──────────────────────┬──────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│                    LEXER (Tokenizer)                 │
│  Analyse lexicale : texte → flux de tokens           │
│                                                      │
│  Entrée : "Capteurs qui ne sont pas actifs"          │
│  Sortie : [CAPTEURS, WHERE, NEG, STATUS_VAL("actif")]│
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│                    PARSER (Analyseur)                 │
│  Analyse syntaxique : tokens → AST                   │
│                                                      │
│  Passe 1 : Balayage complet (intention, entité,      │
│            colonnes, filtres, négation, tri, limite)  │
│  Passe 2 : Construction de l'AST                     │
│                                                      │
│  Sortie : SelectStatement {                          │
│    query_type: SELECT,                               │
│    from: "capteurs",                                 │
│    where: statut != 'actif'                          │
│  }                                                   │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│              CODE GENERATOR (Générateur)              │
│  Génération de code : AST → SQL                      │
│                                                      │
│  Sortie : SELECT id, nom, statut, zone_id            │
│           FROM capteurs                              │
│           WHERE statut != 'ACTIF'                    │
└──────────────────────┬───────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────┐
│                    EXÉCUTION                          │
│  SELECT → Exécuté sur PostgreSQL                     │
│  DELETE / UPDATE / INSERT → Compilé seulement        │
└──────────────────────────────────────────────────────┘
```

---

## 3. Schéma de la Base de Données

| Table            | Colonnes principales                                    |
|------------------|---------------------------------------------------------|
| `capteurs`       | id, nom, type, statut, zone_id, taux_erreur             |
| `interventions`  | id, capteur_id, statut, date_demande, zone_id           |
| `citoyens`       | id, nom, email, score_ecolo, zone_id                    |
| `vehicules`      | id, modele, statut, zone_id, batterie_pct               |
| `mesures`        | id, capteur_id, zone_id, pollution, temperature, ...    |
| `zones`          | id, nom, surface_km2, population                        |
| `trajets`        | trajet_id, vehicule_id, economie_co2, distance_km       |

---

## 4. Exemples de Compilation

### 4.1 Requêtes SELECT

| Requête en français | SQL généré |
|---|---|
| `Affiche les capteurs` | `SELECT id, nom, statut, zone_id FROM capteurs` |
| `Affiche les 5 zones les plus polluées` | `SELECT zone_id, AVG(pollution) FROM mesures GROUP BY zone_id ORDER BY AVG(pollution) DESC LIMIT 5` |
| `Combien de capteurs sont hors service ?` | `SELECT COUNT(*) FROM capteurs WHERE statut = 'HORS_SERVICE'` |
| `Quels citoyens ont un score écologique > 80 ?` | `SELECT nom, score_ecolo FROM citoyens WHERE score_ecolo > 80` |
| `Donne-moi le trajet le plus économique en CO2` | `SELECT trajet_id, economie_co2 FROM trajets ORDER BY economie_co2 ASC LIMIT 1` |
| `Quelles interventions sont en cours ?` | `SELECT id, statut, date_demande, zone_id FROM interventions WHERE statut = 'EN_COURS'` |
| `Capteurs signalé` | `SELECT id, nom, statut, zone_id FROM capteurs WHERE statut = 'SIGNALÉ'` |
| `Capteurs signale` | `SELECT id, nom, statut, zone_id FROM capteurs WHERE statut = 'SIGNALÉ'` |

### 4.2 Requêtes avec Négation

| Requête en français | SQL généré |
|---|---|
| `Capteurs qui ne sont pas actifs` | `SELECT id, nom, statut, zone_id FROM capteurs WHERE statut != 'ACTIF'` |
| `Capteurs sauf actif` | `SELECT id, nom, statut, zone_id FROM capteurs WHERE statut != 'ACTIF'` |
| `Interventions qui ne sont pas terminées` | `SELECT id, statut, date_demande, zone_id FROM interventions WHERE statut != 'TERMINÉ'` |

### 4.3 Requêtes DELETE (compilées, non exécutées)

| Requête en français | SQL généré |
|---|---|
| `Supprimer les capteurs hors service` | `DELETE FROM capteurs WHERE statut = 'HORS_SERVICE'` |
| `Effacer les interventions terminées` | `DELETE FROM interventions WHERE statut = 'TERMINÉ'` |

### 4.4 Requêtes UPDATE (compilées, non exécutées)

| Requête en français | SQL généré |
|---|---|
| `Modifier le statut des capteurs signalé` | `UPDATE capteurs SET statut = 'SIGNALÉ'` |

### 4.5 Requêtes INSERT (compilées, non exécutées)

| Requête en français | SQL généré |
|---|---|
| `Ajouter un capteur` | `INSERT INTO capteurs VALUES (...)` |

---

## 5. Gestion des Erreurs

Le compilateur fournit des diagnostics détaillés en cas d'erreur :

### 5.1 Erreur Lexicale
Quand le tokenizer rencontre un caractère ou une séquence non reconnu.

```
Erreur lexicale à la position 15: caractère inattendu
  Affiche les @#$ capteurs
                ^--- ici
```

### 5.2 Erreur Syntaxique
Quand le parser ne peut pas construire un AST valide.

```
Erreur de syntaxe à la position 22: token inattendu (attendu: valeur numérique ou statut)
  Affiche les capteurs avec statut
                            ^--- erreur ici
```

### 5.3 Erreur Sémantique
Quand la requête est syntaxiquement correcte mais sémantiquement incohérente.

```
Erreur de compilation: UPDATE sans clause SET — aucune valeur à modifier
```

### 5.4 Requêtes Ambiguës
Le compilateur détecte les ambiguïtés et utilise des heuristiques :

```
⚠ Requête ambiguë : Table cible non identifiée, 'capteurs' utilisée par défaut.
```

---

## 6. Normalisation des Valeurs de Statut

Le compilateur normalise automatiquement les variantes orthographiques :

| Entrée utilisateur | Valeur normalisée | Valeur SQL |
|---|---|---|
| `signale`, `signalé`, `signalés`, `signales` | `signalé` | `'SIGNALÉ'` |
| `actif`, `actifs`, `active`, `actives` | `actif` | `'ACTIF'` |
| `inactif`, `inactifs`, `inactive`, `inactives` | `inactif` | `'INACTIF'` |
| `hors service`, `hors_service` | `hors_service` | `'HORS_SERVICE'` |
| `en cours`, `en_cours` | `en_cours` | `'EN_COURS'` |
| `en route`, `en_route` | `en_route` | `'EN_ROUTE'` |
| `en panne`, `en_panne` | `en_panne` | `'EN_PANNE'` |
| `terminé`, `termine`, `terminée`, `terminées` | `terminé` | `'TERMINÉ'` |
| `arrivé`, `arrive` | `arrivé` | `'ARRIVÉ'` |
| `maintenance` | `en_maintenance` | `'EN_MAINTENANCE'` |

---

## 7. Règles de Priorité

1. **Intention** : Le premier token détermine le type de requête (SELECT, DELETE, UPDATE, INSERT)
2. **Entité** : Le premier nom d'entité rencontré détermine la table cible
3. **Colonne dominante** : Certaines colonnes forcent un changement de table
   - `pollution`, `polluées` → table `mesures`
   - `score`, `écologique` → table `citoyens`
   - `co2` → table `trajets`
   - `taux`, `erreur` → table `capteurs`
4. **Négation** : Tout token de négation (`ne`, `pas`, `sauf`, `sans`) inverse le comparateur
5. **Valeur de statut implicite** : Si une valeur de statut apparaît sans colonne, `statut` est inférée
6. **Nombre** : Un nombre est interprété comme LIMIT sauf s'il suit un comparateur

---

## 8. Politique d'Exécution

| Type de requête | Compilé | Exécuté sur la BD |
|---|---|---|
| `SELECT` | ✅ Oui | ✅ Oui |
| `DELETE` | ✅ Oui | ❌ Non (sécurité) |
| `UPDATE` | ✅ Oui | ❌ Non (sécurité) |
| `INSERT` | ✅ Oui | ❌ Non (sécurité) |
