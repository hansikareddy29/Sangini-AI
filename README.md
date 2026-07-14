# 🌸 Sangini AI

> **An Agentic AI-powered WhatsApp assistant for Women-led Self Help Groups (SHGs)**

Sangini is a multi-agent AI system designed to help women-led Self Help Groups (SHGs) manage their business operations directly through **WhatsApp**. Instead of acting as a traditional chatbot, Sangini functions as an intelligent digital coordinator capable of understanding customer requests, checking inventory, allocating work among SHG members, and autonomously making operational decisions.

---

# 📌 Problem Statement

India has more than **8 million Self Help Groups (SHGs)**, empowering millions of women through micro-businesses such as papads, pickles, handicrafts, spices, tailoring, and other locally manufactured products.

Although these businesses are highly skilled in production, their day-to-day operations remain largely manual.

Common challenges include:

- Orders are received through WhatsApp messages and phone calls.
- Inventory is tracked manually.
- There is no centralized system to know who can produce what.
- Work allocation depends on the group leader's memory.
- Production capacity of members changes frequently.
- Communication between members is slow and inefficient.
- Coordinating large customer orders becomes difficult.

As SHGs grow, managing operations manually becomes increasingly inefficient, leading to delayed deliveries, poor inventory management, and missed business opportunities.

---

# 💡 Our Solution

Sangini transforms WhatsApp into an intelligent business management platform using **Agentic AI**.

Instead of simply answering questions, Sangini autonomously coordinates business operations by assigning specialized AI agents to perform different responsibilities.

A customer can simply send a message such as:

> "I need 100 papads by Friday."

Sangini automatically:

- Understands the customer's request.
- Extracts structured order information.
- Checks available inventory.
- Finds eligible SHG members who can produce the remaining quantity.
- Allocates work based on production capacity.
- Generates a final confirmation for the customer.

All of this happens automatically without requiring manual coordination from the SHG leader.

---

# 🤖 Agentic AI Architecture

Sangini consists of six specialized AI agents that collaboratively manage the complete order lifecycle. Instead of relying on a single chatbot, each agent is responsible for one business capability while communicating through a shared workflow state orchestrated by LangGraph.

---

## 🛒 Order Agent

The first point of contact for every customer request.

### Responsibilities

- Parses customer text or voice messages.
- Extracts:
  - Product(s)
  - Quantity
  - Delivery deadline
- Converts natural language into structured JSON.
- Initializes the shared workflow state.

Example

**Input**

```
Need 50 papads by Friday.
```

**Output**

```json
{
  "item": "Papads",
  "quantity": 50,
  "deadline": "Friday"
}
```

---

## 👥 Community Agent

Maintains a live map of all SHG members.

### Responsibilities

- Tracks member skills.
- Knows which products each member can produce.
- Maintains production capacity.
- Tracks daily availability.
- Returns eligible members for a given order.

---

## 🎯 Allocation Agent

Determines the best production plan.

### Responsibilities

- Scores members based on:
  - Skill match
  - Available capacity
  - Fair workload distribution
- Divides work among multiple members.
- Handles insufficient production capacity.
- Generates the final allocation plan.

---

## 📦 Inventory Agent

Manages existing stock before assigning production.

### Responsibilities

- Checks current inventory.
- Verifies stock availability.
- Reserves inventory for confirmed orders.
- Updates stock after order confirmation.
- Prevents unnecessary production if inventory already exists.

---

## 🚚 Fulfillment Agent

Handles execution after allocation.

### Responsibilities

- Creates fulfillment plans.
- Integrates with logistics APIs.
- Tracks delivery status.
- Updates order lifecycle:

---

## 👑 CEO Agent

The CEO Agent is the brain of Sangini.

Instead of performing business operations itself, it orchestrates the complete workflow.

### Responsibilities

- Determines which agent executes next.
- Maintains the shared workflow state.
- Coordinates communication between agents.
- Handles workflow routing.
- Performs asynchronous analysis over historical orders.
- Generates proactive recommendations for SHG leaders.

Unlike a sequential pipeline, the CEO Agent dynamically decides the next step depending on the current workflow state.

---

# 🔄 Tentative Workflow

```
                           ┌───────────────────────┐
                           │      Customer         │
                           │ (WhatsApp Message)    │
                           └──────────┬────────────┘
                                      │
                                      ▼
                      ┌────────────────────────────────┐
                      │     WhatsApp Business App      │
                      └──────────┬─────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────────┐
                    │  Meta WhatsApp Cloud API   │
                    └──────────┬─────────────────┘
                               │
                    Incoming Webhook Request
                               │
                               ▼
                ┌──────────────────────────────────┐
                │       FastAPI Backend            │
                │                                  │
                │  POST /webhook                   │
                │  GET  /webhook (verification)    │
                └──────────────┬───────────────────┘
                               │
                               ▼
                 ┌──────────────────────────────┐
                 │ CEO Agent (LangGraph)        │
                 │                              │
                 │ Shared State                 │
                 │ Decision Making              │
                 │ Workflow Routing             │
                 └───────┬───────────────┬──────┘
                         │               │
     ┌───────────────────┼───────────────┼────────────────────┐
     ▼                   ▼               ▼                    ▼
┌────────────┐   ┌──────────────┐  ┌──────────────┐   ┌──────────────┐
│Order Agent │   │Inventory     │  │Community     │   │Allocation    │
│            │   │Agent         │  │Agent         │   │Agent         │
└─────┬──────┘   └──────┬───────┘  └──────┬───────┘   └──────┬───────┘
      │                 │                 │                  │
      └─────────────────┼─────────────────┼──────────────────┘
                        │
                        ▼
              ┌──────────────────────┐
              │ PostgreSQL Database  │
              │                      │
              │ Members              │
              │ Inventory            │
              │ Orders               │
              │ Allocations          │
              └──────────┬───────────┘
                         │
                         ▼
                 CEO Agent Final Decision
                         │
                         ▼
            WhatsApp Service (Send Message)
                         │
                         ▼
              Meta WhatsApp Cloud API
                         │
                         ▼
                  Customer receives reply
```

---

# 🧠 Why Agentic AI?

A traditional chatbot follows a predefined sequence of prompts and generates responses.

Sangini goes beyond conversation by enabling autonomous decision-making through multiple specialized agents.

The CEO Agent dynamically decides:

- Which agent should execute next.
- Whether inventory alone can fulfill an order.
- Whether production needs to be allocated.
- Whether more information is required.
- When the workflow is complete.

This allows Sangini to adapt its execution path based on the current business state instead of following a rigid sequence of API calls.

As the system evolves, new agents can be introduced without redesigning the entire architecture, making the platform modular, scalable, and maintainable.

---
# 🗂 Shared State
All agents communicate through a centralized **Shared State**, which acts as the single source of truth throughout the workflow.

Instead of passing data directly between agents, every agent reads from and updates this shared object.

Example state:

```python
order_state = {
    "order_id": "",
    "customer": {},
    "parsed_order": {},
    "inventory_status": {},
    "eligible_members": [],
    "allocation_plan": {},
    "fulfillment_status": {},
    "response": ""
}
```

This architecture enables:

- Modular agents
- Better fault tolerance
- Easier debugging
- Dynamic workflow routing
- Scalable orchestration through LangGraph

# 🛢 Database Design

Sangini uses **PostgreSQL (Supabase)** to manage structured business data.

Core entities include:

- SHGs
- Members
- Products
- Inventory
- Orders
- Allocations

The relational schema allows efficient querying, transactional consistency, and scalable business operations.

---

# 💬 WhatsApp Integration

Sangini is designed to operate entirely within WhatsApp.

Users interact with the system using text or voice messages.

Future workflow:

```
WhatsApp
      │
      ▼
Meta WhatsApp Cloud API
      │
      ▼
FastAPI Backend
      │
      ▼
LangGraph Workflow
      │
      ▼
Database + AI Agents
      │
      ▼
WhatsApp Response
```

This ensures users never need to install a separate application.

---

# 🌐 Multilingual Support

To improve accessibility across tier 2 ad 3 cities in India, Sangini will support:

- Speech-to-Text
- Translation
- Text-to-Speech

allowing women to interact naturally in their preferred language through WhatsApp voice messages.

---

# 🛠 Tech Stack

### Backend

- Python
- FastAPI

### Agent Orchestration

- LangGraph
- Pydantic

### LLM

- Gemini (via OpenRouter)

### Database

- PostgreSQL
- Supabase

### Messaging

- Meta WhatsApp Cloud API

### Language Layer

- Deepgram (Speech-to-Text)
- Translation APIs
- Text-to-Speech

---
# 🌍 Vision

Our goal is to empower women-led Self Help Groups with an intelligent AI operations manager that simplifies order management, inventory tracking, production planning, and business coordination—all through the familiarity of WhatsApp.

By reducing operational overhead and enabling autonomous decision-making, Sangini aims to help SHGs scale their businesses while allowing women entrepreneurs to focus on what they do best: creating quality products for their communities.

---