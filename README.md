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

## ⚙️ Local Installation & Quick Start

Follow these steps to run Sangini AI locally on your machine.

### 1. Database Setup
Ensure you have a PostgreSQL database running (locally or via Supabase/Railway).

### 2. Backend Setup (FastAPI)
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory:
```env
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/sangini
OPEN_ROUTER_API_KEY=openrouter_api_key
```

Seed the database and start the server:
```bash
python seed.py
uvicorn app.main:app --host 0.0.0.0 --port 8006
```

### 3. Frontend Setup (Next.js)
Open a new terminal window:
```bash
cd frontend
npm install
```

Create a `.env.local` file in the `frontend/` directory:
```env
NEXT_PUBLIC_BACKEND_URL=http://localhost:8006
NEXT_PUBLIC_WS_URL=ws://localhost:8006
```

Start the frontend development server:
```bash
npm run dev
```

### 4. View the Dashboards
- **Customer View:** `http://localhost:3000/customer`
- **SHG Member View:** `http://localhost:3000/shg`
- **Admin View:** `http://localhost:3000/admin`

---

## 🏆 Hackathon Details
Built with ❤️ for empowering Women SHGs.
