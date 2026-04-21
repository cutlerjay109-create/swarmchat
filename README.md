# SwarmChat
### Vertex Swarm Challenge 2026 — Track 3: The Agent Economy

> *A leaderless AI agent swarm that coordinates, self-heals, and delivers — with no central orchestrator, no cloud dependency, and no single point of failure.*

---

## Overview

SwarmChat is a peer-to-peer multi-agent system built for the Vertex Swarm Challenge 2026. Three autonomous AI agents coordinate entirely over a UDP mesh network — discovering each other, claiming tasks, executing work, detecting faults, and recovering automatically — all without a master controller.

As a real-world application layer, the swarm powers **SwarmChat** — an intelligent chat interface where agents race to answer user queries in parallel. If one agent fails mid-response, another takes over instantly. The user never notices.

---

## The Problem We Solve

Most AI systems today rely on a central orchestrator:

```
Every agent → reports to central server → server tells each agent what to do
```

This is fragile. One server crash kills everything. One network hiccup stops all agents. One vendor change breaks the whole system.

SwarmChat eliminates the middleman entirely:

```
[Agent 1] ←——UDP——→ [Agent 2]
     ↑                    ↑
     └———————UDP——————————┘
               ↓
          [Agent 3]

No server. No broker. Pure peer-to-peer.
```

---

## Architecture

### Layer 1 — The Swarm (P2P Coordination)

Built from scratch using Python `asyncio` and UDP sockets. No vendor middleware. No cloud dependency.

| Function | Description |
|----------|-------------|
| **Discovery** | Agents announce themselves on startup. Every peer is tracked via heartbeat signals |
| **Task Claiming** | Agents broadcast claims across the mesh. No two agents ever duplicate work |
| **Heartbeat** | Every agent pings peers every 3 seconds to confirm it is alive |
| **Fault Detection** | Silence for 10 seconds triggers a fault — the dead agent is declared offline |
| **Auto Recovery** | Abandoned tasks are freed and claimed by surviving agents automatically |
| **Consensus** | Agents compare completed task lists and collectively confirm when all work is done |

### Layer 2 — SwarmChat (Application)

A clean web-based chat interface where the swarm processes user queries.

| Feature | Description |
|---------|-------------|
| **Parallel Execution** | All 3 agents race to answer — fastest response wins |
| **Fault Tolerance** | If an agent fails mid-query, another delivers the response |
| **Web Search** | Real-time search via Tavily for accurate, up-to-date answers |
| **Smart Routing** | Coding questions skip search and go directly to Groq LLM |
| **Chat History** | Full conversation history saved locally, resumable at any time |
| **Edit & Resend** | Users can edit any previous message and resend from that point |
| **Light / Dark Mode** | Full theme support with persistent preference |

---

## How It Works — The Full Flow

```
User sends a message
        ↓
SwarmChat receives it
        ↓
Smart router decides: search needed? (factual) or skip? (coding)
        ↓
If search → Tavily fetches real-time web results
        ↓
All 3 agents receive the query + search context simultaneously
        ↓
Agents race to respond using Groq LLaMA 3.3 70B
        ↓
First agent to respond wins — result delivered to user
        ↓
If an agent crashes → others already running → no interruption
```

---

## The Swarm Terminal Demo

Run the raw swarm without the web interface to see the coordination layer directly:

```bash
python3 run_swarm.py
```

**What you will see:**
1. 3 agents start up and discover each other
2. 9 tasks distributed across the swarm with zero duplication
3. Kill any agent mid-run — the swarm detects it within 10 seconds
4. Abandoned task recovered and completed by a surviving agent
5. All 9 tasks complete regardless of agent failures

---

## Running the Project

### Prerequisites

```bash
pip install groq flask flask-cors tavily-python python-dotenv
```

### Environment Variables

Create a `.env` file in the project root:

```
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key
```

### Run the Swarm Demo (Terminal)

```bash
python3 run_swarm.py
```

### Run SwarmChat (Web Interface)

```bash
python3 server.py
```

Then open `http://localhost:5000`

---

## Project Structure

```
swarm-project/
│
├── agent.py              # Core agent — all 6 swarm functions
├── tasks.py              # Sample task definitions
├── run_swarm.py          # Launches 3 agents simultaneously
├── server.py             # Flask backend — swarm + web search + chat API
├── requirements.txt      # Python dependencies
├── vercel.json           # Vercel deployment configuration
│
├── api/
│   └── index.py          # Serverless entry point for Vercel
│
└── templates/
    └── index.html        # SwarmChat web interface
```

---

## Tech Stack

| Component | Technology |
|-----------|------------|
| Agent coordination | Python asyncio + UDP sockets (built from scratch) |
| AI brain | Groq API — LLaMA 3.3 70B |
| Real-time search | Tavily Search API |
| Web framework | Flask + Flask-CORS |
| Frontend | Vanilla HTML/CSS/JS |
| Deployment | Vercel |

---

## Challenge Alignment

| Challenge Requirement | Our Implementation |
|----------------------|-------------------|
| Leaderless network | ✅ No master orchestrator — agents self-organize |
| Auto-discovery | ✅ Agents find each other on startup via P2P mesh |
| No central broker | ✅ Pure UDP mesh — no server in the middle |
| Task negotiation | ✅ Broadcast-based claiming — zero duplicates |
| Self-healing | ✅ Fault detection + automatic task recovery |
| No single point of failure | ✅ Any 2 of 3 agents can complete all work |
| Real-world application | ✅ SwarmChat — a practical AI assistant powered by the swarm |

---

## Demo Highlights

**Fault Recovery in action:**
```
2:27:09 PM  Agent 2 claimed task 4
2:27:09 PM  Agent 2 was killed          ← agent dies mid-task
2:27:18 PM  FAULT DETECTED: Agent 2 is dead!
2:27:18 PM  Recovering task 4 from dead Agent 2
2:27:20 PM  Agent 1 claimed task 4      ← swarm self-heals
2:27:23 PM  Agent 1 completed task 4
2:27:23 PM  All tasks complete ✓        ← nothing was lost
```

---

## Built By

Solo builder — Vertex Swarm Challenge 2026
Track 3 | The Agent Economy

---

> SwarmChat is AI and can make mistakes. The swarm coordination layer is deterministic — the AI responses are not.
