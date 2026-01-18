from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from typing import List
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# --- DATABASE FUNCTIONS ---
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME")
    )

def save_message(client_id, message):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO chat_messages (client_id, message) VALUES (%s, %s)"
        cursor.execute(query, (str(client_id), message))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"DB Error: {e}")

def get_recent_messages():
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        # Fetch last 20 messages
        cursor.execute("SELECT client_id, message FROM chat_messages ORDER BY timestamp DESC LIMIT 20")
        messages = cursor.fetchall()
        conn.close()
        return messages[::-1] # Reverse to show oldest first
    except Exception as e:
        return []

# --- WEBSOCKET MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

# --- FRONTEND UI ---
html = """
<!DOCTYPE html>
<html>
    <head>
        <title>ScaleChat</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f0f2f5; }
            h1 { text-align: center; color: #333; }
            #chat-box { background: white; border-radius: 10px; height: 400px; overflow-y: scroll; padding: 15px; border: 1px solid #ddd; box-shadow: 0 2px 5px rgba(0,0,0,0.1); display: flex; flex-direction: column; }
            .message { margin-bottom: 10px; padding: 8px 12px; border-radius: 15px; max-width: 80%; display: inline-block; }
            .my-message { background-color: #0084ff; color: white; align-self: flex-end; }
            .other-message { background-color: #e4e6eb; color: black; align-self: flex-start; }
            .system-message { text-align: center; font-size: 0.8em; color: #888; margin: 5px 0; align-self: center; }
            form { display: flex; margin-top: 15px; }
            input { flex-grow: 1; padding: 10px; border: 1px solid #ddd; border-radius: 20px; outline: none; }
            button { background-color: #0084ff; color: white; border: none; padding: 10px 20px; margin-left: 10px; border-radius: 20px; cursor: pointer; }
            button:hover { background-color: #0073e6; }
        </style>
    </head>
    <body>
        <h1>💬 ScaleChat</h1>
        <div id="chat-box"></div>
        <form action="" onsubmit="sendMessage(event)">
            <input type="text" id="messageText" placeholder="Type a message..." autocomplete="off"/>
            <button>Send</button>
        </form>
        <script>
            // Generate a random User ID for this session
            var client_id = Math.floor(Math.random() * 10000);
            
            // Connect to WebSocket
            var ws = new WebSocket("ws://" + window.location.host + "/ws/" + client_id);
            var chatBox = document.getElementById('chat-box');

            function appendMessage(text, type) {
                var div = document.createElement('div');
                div.textContent = text;
                div.className = 'message ' + type;
                chatBox.appendChild(div);
                chatBox.scrollTop = chatBox.scrollHeight; // Auto scroll
            }

            ws.onmessage = function(event) {
                // Determine if message is mine, others, or system
                var data = event.data;
                if (data.includes("Client #" + client_id + ":")) {
                    appendMessage(data.replace("Client #" + client_id + ": ", ""), 'my-message');
                } else if (data.includes("joined") || data.includes("left")) {
                    appendMessage(data, 'system-message');
                } else {
                    appendMessage(data, 'other-message');
                }
            };

            function sendMessage(event) {
                var input = document.getElementById("messageText");
                if (input.value.trim() !== "") {
                    ws.send(input.value);
                    input.value = '';
                }
                event.preventDefault();
            }
        </script>
    </body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: int):
    await manager.connect(websocket)
    
    # 1. Load History
    history = get_recent_messages()
    for msg in history:
        # Format history so frontend understands it
        await websocket.send_text(f"Client #{msg['client_id']}: {msg['message']}")

    # 2. Announce
    await manager.broadcast(f"Client #{client_id} joined")
    
    try:
        while True:
            data = await websocket.receive_text()
            # 3. Save
            save_message(client_id, data)
            # 4. Broadcast
            await manager.broadcast(f"Client #{client_id}: {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        await manager.broadcast(f"Client #{client_id} left")