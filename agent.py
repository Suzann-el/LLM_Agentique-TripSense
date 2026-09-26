"""
TripSense — Agent — cœur de la logique agentique
===================================================

Module réutilisable par le CLI, l'interface Streamlit et l'API FastAPI.

L'agent dispose de 4 outils, tous branchés sur de vraies API publiques
et gratuites (aucune clé requise à part celle d'Anthropic) :

  1. geocode_city      → transforme un nom de ville en coordonnées (Open-Meteo Geocoding)
  2. get_weather        → météo actuelle à partir de coordonnées (Open-Meteo Forecast)
  3. convert_currency   → taux de change du jour (Frankfurter)
  4. get_distance       → distance à vol d'oiseau entre deux villes (calcul local, formule de Haversine)

Le fait de séparer geocode_city de get_weather force l'agent à enchaîner
plusieurs appels d'outils pour une seule question — ce qui illustre bien
le raisonnement "agentique" multi-étapes.
"""

import os
import json
import math
import requests
from anthropic import Anthropic

MODEL = "claude-sonnet-4-5"

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


# ─────────────────────────────────────────────────────────────────────────
# Outils — chacun est une fonction Python normale, testable isolément
# ─────────────────────────────────────────────────────────────────────────

def geocode_city(city: str) -> dict:
    """Convertit un nom de ville en coordonnées géographiques (API gratuite, sans clé)."""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    r = requests.get(url, params={"name": city, "count": 1, "language": "fr"}, timeout=10)
    results = r.json().get("results")
    if not results:
        return {"erreur": f"Ville introuvable : {city}"}
    top = results[0]
    return {
        "ville": top["name"],
        "pays": top.get("country", ""),
        "latitude": top["latitude"],
        "longitude": top["longitude"],
    }


def get_weather(latitude: float, longitude: float, city_name: str = "") -> dict:
    """Météo actuelle pour des coordonnées données (API gratuite, sans clé)."""
    url = "https://api.open-meteo.com/v1/forecast"
    r = requests.get(url, params={
        "latitude": latitude, "longitude": longitude, "current_weather": True
    }, timeout=10)
    current = r.json().get("current_weather", {})
    return {
        "ville": city_name,
        "temperature_c": current.get("temperature"),
        "vent_kmh": current.get("windspeed"),
    }


def convert_currency(amount: float, from_currency: str, to_currency: str) -> dict:
    """Conversion de devise au taux du jour (API gratuite, sans clé)."""
    url = "https://api.frankfurter.app/latest"
    r = requests.get(url, params={
        "amount": amount, "from": from_currency.upper(), "to": to_currency.upper()
    }, timeout=10)
    data = r.json()
    converted = data.get("rates", {}).get(to_currency.upper())
    return {
        "montant_origine": amount,
        "devise_origine": from_currency.upper(),
        "montant_converti": converted,
        "devise_cible": to_currency.upper(),
    }


def get_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> dict:
    """Distance à vol d'oiseau entre deux points (formule de Haversine, calcul local)."""
    R = 6371  # rayon terrestre en km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    distance_km = 2 * R * math.asin(math.sqrt(a))
    return {"distance_km": round(distance_km, 1)}


TOOL_FUNCTIONS = {
    "geocode_city": geocode_city,
    "get_weather": get_weather,
    "convert_currency": convert_currency,
    "get_distance": get_distance,
}

TOOLS = [
    {
        "name": "geocode_city",
        "description": "Trouve les coordonnées géographiques (latitude, longitude) d'une ville à partir de son nom. À utiliser avant get_weather ou get_distance si tu ne connais pas déjà les coordonnées.",
        "input_schema": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "Nom de la ville"}},
            "required": ["city"],
        },
    },
    {
        "name": "get_weather",
        "description": "Donne la météo actuelle (température, vent) à partir de coordonnées géographiques.",
        "input_schema": {
            "type": "object",
            "properties": {
                "latitude": {"type": "number"},
                "longitude": {"type": "number"},
                "city_name": {"type": "string", "description": "Nom de la ville, pour l'affichage"},
            },
            "required": ["latitude", "longitude"],
        },
    },
    {
        "name": "convert_currency",
        "description": "Convertit un montant d'une devise vers une autre, au taux de change du jour.",
        "input_schema": {
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "from_currency": {"type": "string", "description": "Code devise source, ex: EUR"},
                "to_currency": {"type": "string", "description": "Code devise cible, ex: USD"},
            },
            "required": ["amount", "from_currency", "to_currency"],
        },
    },
    {
        "name": "get_distance",
        "description": "Calcule la distance à vol d'oiseau en kilomètres entre deux points géographiques.",
        "input_schema": {
            "type": "object",
            "properties": {
                "lat1": {"type": "number"}, "lon1": {"type": "number"},
                "lat2": {"type": "number"}, "lon2": {"type": "number"},
            },
            "required": ["lat1", "lon1", "lat2", "lon2"],
        },
    },
]

SYSTEM_PROMPT = (
    "Tu es TripSense, un assistant de voyage. Tu as accès à des outils pour "
    "géocoder des villes, consulter la météo, convertir des devises et "
    "calculer des distances. Utilise-les autant de fois que nécessaire, "
    "dans l'ordre logique, pour répondre complètement à la demande de "
    "l'utilisateur — par exemple géocoder une ville avant de demander sa "
    "météo. Réponds ensuite de façon claire, chaleureuse et synthétique, "
    "sans jargon technique, comme le ferait un bon conseiller voyage. "
    "Si une information manque pour répondre, pose une question de "
    "clarification plutôt que de deviner."
)


# ─────────────────────────────────────────────────────────────────────────
# Boucle agentique avec mémoire de conversation (multi-tour)
# ─────────────────────────────────────────────────────────────────────────
class TripSenseAgent:
    """
    Garde l'historique de conversation en mémoire pour permettre des
    échanges multi-tours ("et à Tokyo ?" après avoir parlé de Paris).
    """

    def __init__(self):
        self.messages = []

    def reset(self):
        self.messages = []

    def ask(self, user_message: str, verbose: bool = True) -> str:
        self.messages.append({"role": "user", "content": user_message})

        response = client.messages.create(
            model=MODEL, max_tokens=1200,
            system=SYSTEM_PROMPT, tools=TOOLS, messages=self.messages,
        )

        while response.stop_reason == "tool_use":
            self.messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    fn = TOOL_FUNCTIONS.get(block.name)
                    if verbose:
                        print(f"🔧 {block.name}({block.input})")
                    result = fn(**block.input) if fn else {"erreur": "outil inconnu"}
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })

            self.messages.append({"role": "user", "content": tool_results})

            response = client.messages.create(
                model=MODEL, max_tokens=1200,
                system=SYSTEM_PROMPT, tools=TOOLS, messages=self.messages,
            )

        final_text = "".join(b.text for b in response.content if b.type == "text")
        self.messages.append({"role": "assistant", "content": final_text})
        return final_text


if __name__ == "__main__":
    agent = TripSenseAgent()
    print("TripSense — tape 'quit' pour arrêter\n")
    while True:
        q = input("Toi : ")
        if q.lower() in ("quit", "exit"):
            break
        print(f"\nTripSense : {agent.ask(q)}\n")
