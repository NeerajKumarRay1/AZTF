import os
import json
import sqlite3
import asyncio
from datetime import datetime, timedelta
from typing import List
from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import psutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

import database
import firewall
import zero_trust

app = FastAPI(title="AI-Driven NGFW REST API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security_bearer = HTTPBearer()

# Active WebSocket connections
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
            try:
                await connection.send_text(message)
            except Exception:
                # Handle stale connections
                pass

manager = ConnectionManager()

# Pydantic models for API requests
class LoginRequest(BaseModel):
    username: str
    password: str
    browser: str = "Unknown"
    os: str = "Unknown"

class BlockRequest(BaseModel):
    ip: str
    duration: int = 300
    reason: str = "Manual Admin Block"

# Helper dependency to authenticate JWT
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_bearer)):
    token = credentials.credentials
    payload = zero_trust.decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload

@app.post("/auth/login")
def login(req: LoginRequest):
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (req.username,))
    user = cursor.fetchone()
    conn.close()
    
    if not user or not zero_trust.verify_password(req.password, user["password_hash"]):
        # Log failed auth event
        database.log_auth_event(
            event_id=str(uuid.uuid4()) if 'uuid' in globals() else str(datetime.now().timestamp()),
            user_id=req.username,
            event_type="LOGIN_FAILED",
            fingerprint={"os": req.os, "browser": req.browser},
            ip="N/A",
            status="REJECTED"
        )
        raise HTTPException(status_code=400, detail="Incorrect username or password")
        
    # Generate token
    token = zero_trust.create_access_token(data={"sub": req.username, "role": user["role"]})
    
    # Log successful auth event
    database.log_auth_event(
        event_id=str(datetime.now().timestamp()),
        user_id=req.username,
        event_type="LOGIN_SUCCESS",
        fingerprint={"os": req.os, "browser": req.browser},
        ip="N/A",
        status="APPROVED"
    )
    
    return {"access_token": token, "token_type": "bearer", "role": user["role"]}

@app.get("/threats")
def get_threats(current_user: dict = Depends(get_current_user)):
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT t.*, f.src_ip, f.dst_ip, f.src_port, f.dst_port, f.protocol
        FROM threat_events t
        JOIN flows f ON t.flow_id = f.flow_id
        ORDER BY t.timestamp DESC LIMIT 100
    ''')
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.get("/rules")
def get_rules(current_user: dict = Depends(get_current_user)):
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM firewall_rules ORDER BY created_at DESC LIMIT 100")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

@app.post("/rules/block")
def manual_block(req: BlockRequest, current_user: dict = Depends(get_current_user)):
    if not zero_trust.verify_role(current_user, "Analyst"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
        
    success = firewall.block_ip(ip=req.ip, duration_seconds=req.duration, reason=req.reason)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to apply firewall rule (IP might be whitelisted)")
    return {"message": f"Successfully blocked {req.ip}"}

@app.post("/rules/unblock/{ip}")
def manual_unblock(ip: str, current_user: dict = Depends(get_current_user)):
    if not zero_trust.verify_role(current_user, "Analyst"):
        raise HTTPException(status_code=403, detail="Insufficient permissions")
        
    firewall.unblock_ip(ip)
    return {"message": f"Successfully unblocked {ip}"}

# WebSocket background loop
async def websocket_broadcaster():
    print("FastAPI: Starting background metrics broadcaster...")
    while True:
        try:
            if manager.active_connections:
                conn = database.get_db_connection()
                cursor = conn.cursor()
                
                # Get latest threat events
                cursor.execute('''
                    SELECT t.*, f.src_ip, f.dst_ip, f.src_port, f.dst_port, f.protocol
                    FROM threat_events t
                    JOIN flows f ON t.flow_id = f.flow_id
                    ORDER BY t.timestamp DESC LIMIT 10
                ''')
                threats = [dict(row) for row in cursor.fetchall()]
                
                # Get current stats (packet rates)
                cursor.execute("SELECT COUNT(*), SUM(json_extract(features_json, '$.src_bytes') + json_extract(features_json, '$.dst_bytes')) FROM flows")
                total_flows, total_bytes = cursor.fetchone()
                total_bytes = total_bytes or 0
                
                # Active rules
                cursor.execute("SELECT COUNT(*) FROM firewall_rules WHERE revoked = 0")
                active_rules_count = cursor.fetchone()[0]
                
                # Protocol distribution
                cursor.execute("SELECT protocol, COUNT(*) FROM flows GROUP BY protocol")
                protocols = {row[0]: row[1] for row in cursor.fetchall()}
                
                conn.close()
                
                # System health metrics
                cpu = psutil.cpu_percent()
                mem = psutil.virtual_memory().percent
                disk = psutil.disk_usage('/').percent
                
                payload = {
                    "timestamp": datetime.now().strftime('%H:%M:%S'),
                    "metrics": {
                        "total_flows": total_flows,
                        "total_bytes": total_bytes,
                        "active_rules": active_rules_count,
                        "cpu": cpu,
                        "memory": mem,
                        "disk": disk
                    },
                    "protocols": protocols,
                    "latest_threats": threats
                }
                
                await manager.broadcast(json.dumps(payload))
        except Exception as e:
            print(f"Broadcaster Error: {e}")
            
        await asyncio.sleep(2.0)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.on_event("startup")
async def startup_event():
    # Run the database schema initialization
    database.init_db()
    # Initialize firewall defaults
    firewall.init_firewall()
    # Start the broadcaster task
    asyncio.create_task(websocket_broadcaster())

# Mount dashboard static directory
dashboard_path = os.path.join(BASE_DIR, "dashboard")
os.makedirs(dashboard_path, exist_ok=True)
app.mount("/dashboard", StaticFiles(directory=dashboard_path), name="dashboard")
