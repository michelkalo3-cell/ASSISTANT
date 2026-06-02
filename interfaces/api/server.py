"""
CHARAMOU AI - API REST & WebSockets
Permet l'accès via mobile ou interface web.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import json
import threading

app = FastAPI(title="CHARAMOU AI API")
engine = None  # Sera injecté

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"status": "online", "assistant": "CHARAMOU AI v3"}

@app.get("/status")
def get_status():
    if engine:
        return engine.get_status()
    return {"error": "Engine not initialized"}

@app.post("/chat")
async def chat(query: dict):
    if not engine: return {"error": "Engine offline"}
    text = query.get("text", "")
    response = engine.process_input(text)
    return {"response": response}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            if engine:
                # Traitement asynchrone pour ne pas bloquer le WS
                response = engine.process_input(data)
                await websocket.send_text(json.dumps({"response": response}))
    except WebSocketDisconnect:
        pass

def start_api(assistant_engine, port=8000):
    global engine
    engine = assistant_engine
    config = uvicorn.Config(app, host="0.0.0.0", port=port, log_level="info")
    server = uvicorn.Server(config)
    threading.Thread(target=server.run, daemon=True).start()
