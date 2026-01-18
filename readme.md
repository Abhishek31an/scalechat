# ScaleChat - High-Performance Real-Time Messaging System

**Live Demo:** [Insert your Render Link Here]

## 🚀 Overview
ScaleChat is a secure, multi-room messaging platform engineered for low-latency communication. It utilizes **WebSockets** for full-duplex communication and **TiDB (MySQL)** for persistent storage, supporting concurrent user sessions with optimistic UI updates.

## 🛠️ Tech Stack
* **Backend:** FastAPI (Python), Uvicorn (ASGI Server)
* **Protocol:** WebSockets (Async I/O)
* **Database:** TiDB Cloud (MySQL compliant)
* **Concurrency:** Async/Await + ThreadPool execution for non-blocking I/O
* **Deployment:** Render Cloud (Dockerized environment)

## ⚡ Key Features
* **Real-Time Latency:** <100ms message delivery via persistent WebSocket connections.
* **Optimistic UI:** "Talk First, Save Later" architecture ensures instant feedback even on slow networks.
* **Room-Level Security:** Password-protected channels preventing unauthorized access.
* **Concurrency Handling:** Background thread offloading for database writes to prevent event loop blocking.

## 🏗️ Architecture
[Client] <--> [FastAPI WebSocket Manager] <--> [TiDB Database]
