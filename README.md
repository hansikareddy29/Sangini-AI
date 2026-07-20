# 🌸 Sangini AI: Agentic Orchestration for Self-Help Groups (SHGs)

![Sangini AI Cover](https://via.placeholder.com/1000x300/004d40/ffffff?text=Sangini+AI+-+Empowering+Women+with+Agentic+AI)

## 📌 The Problem
Millions of women in rural India operate in Self-Help Groups (SHGs), producing high-quality local goods like papads, pickles, and handicrafts. However, they face critical systemic bottlenecks:
1. **Demand Aggregation:** They rely on manual word-of-mouth or fragmented WhatsApp messages to get orders.
2. **Capacity Blindness:** When a large bulk order arrives, it's nearly impossible to know exactly who has the bandwidth to produce what.
3. **Language Barriers:** Software solutions are typically in English, excluding women who prefer interacting in native regional languages.

## 🚀 The Solution: Sangini AI
**Sangini AI** is an autonomous, multi-agent AI orchestration platform that acts as the digital manager for women’s Self-Help Groups. Using a powerful LangGraph-based swarm, Sangini AI listens to customer orders (via WhatsApp), parses them, checks real-time community inventory, dynamically calculates the workforce capacity, and automatically allocates production tasks to individual women based on their real-time bandwidth. 

It completely removes the administrative overhead of managing an SHG, allowing women to focus entirely on production and earning.

---

## 🧠 Technical Architecture 

At the core of Sangini AI is a strict **LangGraph Workflow** powered by **Gemini 2.5 Flash**. Instead of a single monolithic LLM prone to hallucinations, Sangini uses a deterministic swarm of specialized micro-agents that read and write to a strongly typed `SharedState` schema.

1. **Intent & Language Agent:** Instantly detects the native language and classifies the business intent (Order Placement, Inquiry, or Modification). 
2. **Order Extraction Agent:** Parses the raw text and strictly maps the requested items against the live **PostgreSQL Product Catalog**. Prevents AI hallucinations.
3. **Inventory Agent:** Queries live database stock. Calculates exactly what can be fulfilled instantly and computes the exact `need_to_produce` deficit. Creates atomic stock reservations.
4. **Community Capacity Agent:** Scans the SHG database. Calculates real-time maximum community bandwidth by evaluating active women and their daily production capacities.
5. **Allocation Agent:** Executes a dynamic greedy scoring algorithm to optimally distribute the `need_to_produce` deficit to the women who have available bandwidth. Dispatches live **WebSocket** notifications.
6. **Response Synthesis Agent:** Formulates a concise, empathetic final response to the customer, translating complex backend states back into the customer's native script.

---

## 💻 The Platform Ecosystem

Sangini AI provides three distinct, real-time user interfaces powered by **Next.js** and **WebSockets**:

1. **The Customer Interface (WhatsApp Simulator):** A seamless chat interface representing the end-user. Customers can simply text *"naku 30 papad lu 30 pachadlu kavali"* (I need 30 papads and 30 pickles in Telugu), and Sangini AI understands, processes the entire backend supply chain, and replies in Telugu.
2. **The SHG Member Dashboard:** 
   - **Private AI Chat:** Women can chat directly with Sangini AI in their native language to report production. (e.g., *"Aaj maine 40 papad extra banaye hain"*).
   - **Community Group:** A unified group chat where Sangini AI posts automated production allocations for everyone to see.
3. **The Admin/Observer Dashboard:** A powerful command center for NGOs or SHG leaders displaying real-time metrics, system logs, total orders processed, and current community capacity limits over live WebSockets.

---

## 🛠️ Tech Stack
* **Frontend:** Next.js (React), Tailwind CSS, Lucide Icons, Shadcn UI
* **Backend:** FastAPI (Python), AsyncIO, WebSockets for real-time bi-directional communication.
* **AI / LLM Orchestration:** LangGraph, LangChain, Google Gemini 2.5 Flash via OpenRouter.
* **Database:** PostgreSQL (Asyncpg) with SQLAlchemy ORM. Atomic transactions and strictly relational schema design.

---
# 🚀 Local Setup Guide

## Prerequisites

Before starting, ensure the following are installed on your system:

- Git
- Python 3.11+
- Node.js (v18 or later)
- npm
- Docker Engine
- Docker Compose (v2)

Verify your installation:

```bash
git --version
python3 --version
node --version
npm --version
docker --version
docker compose version
```

If `docker compose version` returns an error or Docker is not installed, install Docker first.

---

# Install Docker (Ubuntu)

Update packages:

```bash
sudo apt update
```

Install Docker:

```bash
sudo apt install docker.io docker-compose-v2 -y
```

Start Docker:

```bash
sudo systemctl start docker
```

Enable Docker on boot:

```bash
sudo systemctl enable docker
```

(Optional) Allow Docker to run without sudo:

```bash
sudo usermod -aG docker $USER
```

Log out and log back in (or reboot), then verify:

```bash
docker --version
docker compose version
```

---

# Clone the Repository

```bash
git clone <repository-url>
cd Sangini-AI
```

---

# 1. Database Setup (Docker)

From the project root:

```bash
docker compose up -d
```

Verify the database is running:

```bash
docker ps
```

Expected output should include:

```
sangini_db
```

---

# 2. Backend Setup (FastAPI)

Open a new terminal:

```bash
cd backend
```

Create a virtual environment:

```bash
python3 -m venv venv
```

Activate it:

### Linux/macOS

```bash
source venv/bin/activate
```

### Windows

```powershell
venv\Scripts\activate
```

Install dependencies:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Create a `.env` file:

```env
DATABASE_URL=postgresql+asyncpg://sangini_user:sangini_password@localhost:5432/sangini_db
OPEN_ROUTER_API_KEY=YOUR_OPENROUTER_API_KEY
```

Seed the database:

```bash
python seed.py
```

Run the backend:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8006 --reload
```

---

# 3. Frontend Setup (Next.js)

Open another terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create `.env.local`:

```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8006
NEXT_PUBLIC_WS_URL=ws://localhost:8006
```

Run the frontend:

```bash
npm run dev
```

---

# 4. Access the Application

Open your browser:

Customer Dashboard

```
http://localhost:3000/customer
```

SHG Dashboard

```
http://localhost:3000/shg
```

Admin Dashboard

```
http://localhost:3000/admin
```

---

# Stopping the Application

Stop the backend/frontend using:

```
Ctrl + C
```

Stop the database:

```bash
docker compose down
```

---

# Troubleshooting

### Docker not running

Start Docker:

```bash
sudo systemctl start docker
```

---

### Permission denied while running Docker

Run:

```bash
sudo usermod -aG docker $USER
```

Log out and log back in.

---

### PostgreSQL container not starting

Remove old containers:

```bash
docker compose down
docker compose up -d
```

---

### Backend cannot connect to database

Verify the database is running:

```bash
docker ps
```

You should see:

```
sangini_db
```

---

### Check service logs

Database logs:

```bash
docker logs sangini_db
```

Backend logs appear directly in the terminal where FastAPI is running.
## 🏆 Hackathon Details
Built with ❤️ for empowering Women SHGs.
