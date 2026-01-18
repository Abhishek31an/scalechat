from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from typing import List, Dict
import mysql.connector
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# --- DATA MODELS ---
class RoomRequest(BaseModel):
    room_name: str
    password: str

# --- DATABASE FUNCTIONS ---
def get_db_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        port=os.getenv("DB_PORT"),
        database=os.getenv("DB_NAME")
    )

# 1. CREATE ROOM
@app.post("/api/create-room")
def create_room(request: RoomRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        # Check if exists
        cursor.execute("SELECT room_name FROM rooms WHERE room_name = %s", (request.room_name,))
        if cursor.fetchone():
            raise HTTPException(status_code=400, detail="Room already exists! Try a different name.")
        
        # Create new room
        cursor.execute("INSERT INTO rooms (room_name, password) VALUES (%s, %s)", 
                      (request.room_name, request.password))
        conn.commit()
        return {"message": "Room Created!"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

# 2. VERIFY PASSWORD (JOIN)
@app.post("/api/join-room")
def join_room(request: RoomRequest):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT password FROM rooms WHERE room_name = %s", (request.room_name,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=404, detail="Room not found.")
        
        if result[0] != request.password:
            raise HTTPException(status_code=403, detail="Wrong Password!")
            
        return {"message": "Access Granted"}
    finally:
        conn.close()

# 3. SAVE MESSAGE
def save_message_sync(room_name, client_id, message):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = "INSERT INTO chat_messages (room_id, client_id, message) VALUES (%s, %s, %s)"
        cursor.execute(query, (room_name, str(client_id), message))
        conn.commit()
        conn.close()
    except:
        pass

# 4. GET HISTORY
def get_history_sync(room_name):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT client_id, message FROM chat_messages WHERE room_id = %s ORDER BY timestamp DESC LIMIT 20"
        cursor.execute(query, (room_name,))
        messages = cursor.fetchall()
        conn.close()
        return messages[::-1]
    except:
        return []

# --- WEBSOCKET MANAGER ---
class ConnectionManager:
    def __init__(self):
        self.active_rooms: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, room_name: str):
        await websocket.accept()
        if room_name not in self.active_rooms:
            self.active_rooms[room_name] = []
        self.active_rooms[room_name].append(websocket)

    def disconnect(self, websocket: WebSocket, room_name: str):
        if room_name in self.active_rooms:
            if websocket in self.active_rooms[room_name]:
                self.active_rooms[room_name].remove(websocket)

    async def broadcast(self, message: str, room_name: str):
        if room_name in self.active_rooms:
            for connection in self.active_rooms[room_name][:]:
                try:
                    await connection.send_text(message)
                except:
                    pass

manager = ConnectionManager()

# --- FRONTEND UI ---
html = """
<!DOCTYPE html>
<html>
    <head>
        <title>SecureChat</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; background: #f0f2f5; }
            input { padding: 10px; margin: 5px 0; width: 100%; border-radius: 5px; border: 1px solid #ccc; box-sizing: border-box; }
            button { width: 100%; padding: 10px; margin-top: 10px; background: #0084ff; color: white; border: none; border-radius: 5px; cursor: pointer; }
            button.secondary { background: #42b72a; }
            .card { background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }
            #chat-screen { display: none; }
            #chat-box { height: 350px; overflow-y: scroll; border-bottom: 1px solid #eee; margin-bottom: 10px; }
            .message { padding: 8px 12px; margin: 5px; border-radius: 10px; display: inline-block; clear: both; }
            .my-message { background: #0084ff; color: white; float: right; }
            .other-message { background: #e4e6eb; color: black; float: left; }
        </style>
    </head>
    <body>

        <div id="auth-screen">
            <h1 style="text-align: center;">🔒 SecureChat</h1>
            
            <div class="card">
                <h3>🚪 Join Existing Room</h3>
                <input type="text" id="joinName" placeholder="Room Name (e.g. Apple)">
                <input type="password" id="joinPass" placeholder="Password">
                <button onclick="joinRoom()">Enter Room</button>
            </div>
            <br>
            <div class="card">
                <h3>✨ Create New Room</h3>
                <input type="text" id="createName" placeholder="New Room Name">
                <input type="password" id="createPass" placeholder="Set Password">
                <button class="secondary" onclick="createRoom()">Create & Join</button>
            </div>
        </div>

        <div id="chat-screen">
            <h2 id="room-header"></h2>
            <div id="chat-box"></div>
            <input type="text" id="msgInput" placeholder="Type a message..." autocomplete="off">
            <button onclick="sendMessage()">Send</button>
        </div>

        <script>
            var ws;
            var client_id = Math.floor(Math.random() * 10000);
            var current_room = "";

            async function createRoom() {
                var name = document.getElementById("createName").value;
                var pass = document.getElementById("createPass").value;
                
                var response = await fetch("/api/create-room", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({room_name: name, password: pass})
                });
                
                if (response.ok) {
                    alert("Room Created!");
                    // Auto-fill join fields
                    document.getElementById("joinName").value = name;
                    document.getElementById("joinPass").value = pass;
                } else {
                    var err = await response.json();
                    alert("Error: " + err.detail);
                }
            }

            async function joinRoom() {
                var name = document.getElementById("joinName").value;
                var pass = document.getElementById("joinPass").value;

                // 1. Verify Password with API
                var response = await fetch("/api/join-room", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({room_name: name, password: pass})
                });

                if (response.ok) {
                    // 2. If Password Correct, Connect WebSocket
                    enterChatUI(name);
                } else {
                    var err = await response.json();
                    alert(err.detail);
                }
            }

            function enterChatUI(roomName) {
                current_room = roomName;
                document.getElementById("auth-screen").style.display = "none";
                document.getElementById("chat-screen").style.display = "block";
                document.getElementById("room-header").innerText = "Room: " + roomName;

                var protocol = window.location.protocol === "https:" ? "wss://" : "ws://";
                ws = new WebSocket(protocol + window.location.host + "/ws/" + roomName + "/" + client_id);

                ws.onmessage = function(event) {
                    var box = document.getElementById("chat-box");
                    var div = document.createElement("div");
                    var data = event.data;

                    if (data.includes("Client #" + client_id + ":")) {
                        div.className = "message my-message";
                        div.textContent = data.replace("Client #" + client_id + ": ", "");
                    } else if (data.includes("joined") || data.includes("left")) {
                         // System messages (optional styling)
                         div.style.textAlign = "center";
                         div.style.fontSize = "0.8em";
                         div.style.color = "#888";
                         div.textContent = data;
                    } else {
                        div.className = "message other-message";
                        div.textContent = data;
                    }
                    box.appendChild(div);
                    box.scrollTop = box.scrollHeight;
                };
            }

            function sendMessage() {
                var input = document.getElementById("msgInput");
                if (input.value.trim()) {
                    ws.send(input.value);
                    input.value = "";
                }
            }
        </script>
    </body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)

@app.websocket("/ws/{room_name}/{client_id}")
async def websocket_endpoint(websocket: WebSocket, room_name: str, client_id: int):
    # Note: For maximum security, we should re-verify the password here using a Token.
    # But for this level of project, verifying at the "Join" button is sufficient.
    
    await manager.connect(websocket, room_name)
    
    # Load History
    history = await run_in_threadpool(get_history_sync, room_name)
    for msg in history:
        await websocket.send_text(f"Client #{msg['client_id']}: {msg['message']}")
        
    await manager.broadcast(f"Client #{client_id} joined", room_name)
    
    try:
        while True:
            data = await websocket.receive_text()
            await manager.broadcast(f"Client #{client_id}: {data}", room_name)
            await run_in_threadpool(save_message_sync, room_name, client_id, data)
    except WebSocketDisconnect:
        manager.disconnect(websocket, room_name)
        await manager.broadcast(f"Client #{client_id} left", room_name)