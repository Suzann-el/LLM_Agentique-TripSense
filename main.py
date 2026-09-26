"""
TripSense API — FastAPI
==========================
Lancer en local : uvicorn main:app --reload
Docs            : http://localhost:8000/docs

Chaque appel à /chat crée un agent neuf (sans mémoire entre appels HTTP).
Pour une conversation multi-tours via l'API, le client doit renvoyer
l'historique complet à chaque requête (voir le champ `history`).
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional

from agent import TripSenseAgent

app = FastAPI(
    title="TripSense API",
    description="Agent de voyage agentique — météo, devises, distances en temps réel",
    version="1.0.0",
)


class ChatTurn(BaseModel):
    role: str  # "user" ou "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., example="Quel temps fait-il à Marrakech ?")
    history: Optional[List[ChatTurn]] = Field(
        default=None,
        description="Historique de conversation optionnel, pour un échange multi-tours"
    )


class ChatResponse(BaseModel):
    reply: str
    history: List[ChatTurn]


@app.get("/")
def root():
    return {"service": "TripSense API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    """
    Envoie un message à l'agent et reçoit sa réponse.
    Passe le champ `history` reçu dans la réponse précédente pour
    poursuivre la même conversation.
    """
    try:
        agent = TripSenseAgent()
        if req.history:
            agent.messages = [{"role": h.role, "content": h.content} for h in req.history]

        reply = agent.ask(req.message, verbose=False)

        new_history = [
            ChatTurn(role=m["role"], content=m["content"])
            for m in agent.messages
            if isinstance(m["content"], str)  # on ne renvoie pas les blocs tool_use bruts
        ]
        return ChatResponse(reply=reply, history=new_history)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
