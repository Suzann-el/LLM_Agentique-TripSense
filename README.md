# ✈️ TripSense — Agent LLM de voyage en temps réel

Auteure : SaoussanEL
---

## Contexte

Projet d'exploration de l'**IA agentique** : un LLM (Claude, Anthropic) qui
ne se contente pas de générer du texte, mais qui **décide seul** quels
outils externes appeler, dans quel ordre, pour répondre complètement à
une question — sans logique métier codée en dur.

## Concept

```
Question en langage naturel
        ↓
Claude analyse la demande et décide quels outils appeler
        ↓
Un ou plusieurs appels d'outils, en chaîne si nécessaire
        ↓
Claude combine les résultats et répond en langage naturel
```

**Exemple concret :**
> "Je pars à Tokyo avec 800 euros, quel temps y fait-il et ça représente combien en yens ?"

L'agent enchaîne automatiquement 3 appels d'outils : `geocode_city("Tokyo")`
→ `get_weather(lat, lon)` → `convert_currency(800, "EUR", "JPY")`, puis
formule une réponse unique et naturelle.

## Outils de l'agent

| Outil | Rôle | Source |
|-------|------|--------|
| `geocode_city` | Convertit un nom de ville en coordonnées | Open-Meteo Geocoding API (gratuite) |
| `get_weather` | Météo actuelle à des coordonnées | Open-Meteo Forecast API (gratuite) |
| `convert_currency` | Taux de change du jour | Frankfurter API (gratuite) |
| `get_distance` | Distance à vol d'oiseau entre 2 points | Calcul local (formule de Haversine) |

Toutes les API externes utilisées sont **publiques et gratuites**, sans
clé requise — seule une clé API Anthropic est nécessaire pour le LLM.

## Architecture du projet

```
tripsense/
├── agent.py        → cœur agentique : outils + boucle de raisonnement + mémoire
├── app.py           → interface de chat Streamlit (multi-tours)
├── main.py          → API FastAPI (endpoint /chat, déployable)
├── requirements.txt
├── Procfile          → déploiement Render
└── .env.example
```

`agent.py` est le seul module contenant la logique métier — `app.py` et
`main.py` ne sont que deux façons différentes de l'exposer (interface
graphique vs API REST), ce qui évite toute duplication de code.

## Installation

```bash
git clone https://github.com/Suzann-el/TripSense.git
cd TripSense
pip install -r requirements.txt
cp .env.example .env   # puis renseigner ta clé ANTHROPIC_API_KEY dedans
```

## Utilisation

**En ligne de commande :**
```bash
set ANTHROPIC_API_KEY=sk-ant-...     # Windows
python agent.py
```

**Interface de chat (Streamlit) :**
```bash
streamlit run app.py
```

**API REST (FastAPI) :**
```bash
uvicorn main:app --reload
# Documentation interactive : http://localhost:8000/docs
```

Exemple d'appel API :
```bash
curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "Quel temps fait-il à Lisbonne ?"}'
```

## Déploiement

- **Streamlit Community Cloud** (gratuit) pour l'interface de chat
- **Render** (gratuit) pour l'API, via le `Procfile` fourni

Dans les deux cas, penser à définir la variable d'environnement
`ANTHROPIC_API_KEY` dans les paramètres de la plateforme (jamais dans le code).

## Ce que ce projet démontre

- Utilisation du **tool use / function calling** de l'API Claude
- Orchestration de **plusieurs outils en chaîne** (raisonnement multi-étapes)
- **Mémoire de conversation** multi-tours
- Séparation propre entre logique métier (`agent.py`) et interfaces (`app.py`, `main.py`)
- Déploiement d'une application agentique en conditions réelles

---
*Saoussan Elhaouzi — Data Scientist · github.com/Suzann-el · 2026*
