# SwarmChat
### Vertex Swarm Challenge 2026 — Track 3: The Agent Economy

> *A leaderless AI agent swarm that coordinates, self-heals, and delivers — with no central orchestrator, no cloud dependency, and no single point of failure.*

---

## Overview

SwarmChat is a peer-to-peer multi-agent system built for the Vertex Swarm Challenge 2026. Three autonomous AI agents coordinate entirely over an MQTT mesh network — discovering each other, claiming tasks, executing work, detecting faults, and recovering automatically — all without a master controller.

As a real-world application, the swarm powers **SwarmChat** — an intelligent chat interface where agents race to answer user queries in parallel. If one agent fails mid-response, another takes over instantly. The user never notices.

---

## The Problem We Solve

Most AI systems today rely on a central orchestrator:

```
Every agent → reports to central server → server tells each agent what to do
```

This is fragile. One server crash kills everything. One network hiccup stops all agents.

SwarmChat eliminates the middleman entirely:

```
[Agent 1] ←——MQTT——→ [Broker] ←——MQTT——→ [Agent 2]
     ↑                                         ↑
     └———————————————MQTT————————————————————┘
                       ↓
                  [Agent 3]

Leaderless. Broker-coordinated. No single point of failure.
```

---

## Architecture

### Layer 1 — The Swarm (MQTT Coordination)

Agents communicate via standard MQTT publish/subscribe protocol — fully compatible with FoxMQ by Tashi Network.

| MQTT Topic | Purpose |
|------------|---------|
| `swarm/heartbeat` | Agents broadcast presence every 3 seconds |
| `swarm/claim` | Agents claim tasks across the mesh — zero duplicates |
| `swarm/complete` | Agents broadcast task completion to all peers |

| Swarm Function | Description |
|----------------|-------------|
| **Discovery** | Agents connect to the MQTT broker and subscribe to swarm topics on startup |
| **Task Claiming** | Agents publish to `swarm/claim` — no two agents ever duplicate work |
| **Heartbeat** | Every agent publishes to `swarm/heartbeat` every 3 seconds |
| **Fault Detection** | Silence for 10 seconds triggers a fault — the dead agent is declared offline |
| **Auto Recovery** | Abandoned tasks are freed and claimed by surviving agents automatically |
| **Consensus** | Agents collectively confirm when all work is done — no single agent decides |

### Layer 2 — SwarmChat (Application)

A clean web-based chat interface powered entirely by the swarm.

| Feature | Description |
|---------|-------------|
| **Parallel Execution** | All 3 agents race to answer — fastest response wins |
| **Fault Tolerance** | If an agent fails mid-query, another delivers the response |
| **Real-time Knowledge** | Answers grounded in current, up-to-date web search results |
| **Smart Routing** | Coding questions skip search — factual questions trigger live search |
| **Chat History** | Full conversation history saved locally, resumable at any time |
| **Edit and Resend** | Users can edit any previous message and resend from that point |
| **Light / Dark Mode** | Full theme support with persistent preference |
| **Pull to Refresh** | Native browser pull-to-refresh support |

---

## How It Works

```
User sends a message
        ↓
SwarmChat receives it
        ↓
Smart router: coding question? → skip search
              factual question? → fetch live web results
        ↓
All 3 agents process the query simultaneously via MQTT mesh
        ↓
First agent to respond wins — result delivered to user
        ↓
If an agent crashes → others already running → no interruption
        ↓
Response saved to local chat history
```

---

## Running the Project

### Prerequisites

```bash
pip install -r requirements.txt
apt-get install mosquitto -y
```

### Environment Variables

Create a `.env` file in the project root:

```
AI_API_KEY=your_key_here
SEARCH_API_KEY=your_key_here
```

### Start the MQTT Broker

```bash
mosquitto -v
```

### Run the Swarm Demo (Terminal)

In a second terminal:

```bash
python3 run_swarm.py
```

**What you will see:**
1. 3 agents connect to MQTT broker and subscribe to swarm topics
2. Heartbeats flowing across the mesh every 3 seconds
3. Tasks distributed across agents with zero duplication
4. Kill any agent mid-run — swarm detects it within 10 seconds
5. Abandoned task recovered and completed by a surviving agent
6. All tasks complete regardless of agent failures
7. All agents disconnect cleanly from the broker

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
├── agent.py              # Core agent — MQTT mesh + all 6 swarm functions
├── tasks.py              # Sample task definitions
├── run_swarm.py          # Launches all agents simultaneously
├── server.py             # Backend — swarm coordination + chat API
├── requirements.txt      # Python dependencies
├── vercel.json           # Deployment configuration
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
| Agent coordination | MQTT publish/subscribe (FoxMQ-compatible) via paho-mqtt |
| MQTT broker | FoxMQ by Tashi Network (Mosquitto for ARM64 development) |
| AI execution | Large language model inference |
| Real-time knowledge | Live web search integration |
| Web framework | Flask |
| Frontend | Vanilla HTML / CSS / JavaScript |
| Deployment | Vercel |

---

## Challenge Alignment

| Challenge Requirement | Our Implementation |
|----------------------|-------------------|
| Leaderless network | ✅ No master orchestrator — agents self-organize via MQTT |
| Auto-discovery | ✅ Agents subscribe to swarm topics on startup |
| MQTT broker integration | ✅ Standard MQTT protocol — FoxMQ compatible |
| Task negotiation | ✅ Broadcast claiming via `swarm/claim` — zero duplicates |
| Self-healing | ✅ Heartbeat fault detection + automatic task recovery |
| No single point of failure | ✅ Any 2 of 3 agents can complete all work |
| Real-world application | ✅ SwarmChat — a practical AI assistant powered by the swarm |

---

## Demo Highlights

**MQTT mesh coordination:**

```
Agent 1 → PUBLISH swarm/heartbeat
Agent 2 → PUBLISH swarm/heartbeat
Agent 3 → PUBLISH swarm/heartbeat

Agent 3 → PUBLISH swarm/claim {task_id: 1}
Agent 1 → PUBLISH swarm/claim {task_id: 2}
Agent 2 → PUBLISH swarm/claim {task_id: 3}

Agent 3 → PUBLISH swarm/complete {task_id: 1}  ✓
Agent 1 → PUBLISH swarm/complete {task_id: 2}  ✓
Agent 2 → PUBLISH swarm/complete {task_id: 3}  ✓
```

**Fault Recovery in action:**

```
Agent 2 claimed task 4 via swarm/claim
Agent 2 was killed              ← agent dies mid-task
FAULT DETECTED: Agent 2 is dead!
Recovering task 4 from dead Agent 2
Agent 1 claimed task 4          ← swarm self-heals
Agent 1 completed task 4
All tasks complete ✓            ← nothing was lost
```

---

## Note on FoxMQ

FoxMQ by Tashi Network does not currently provide an ARM64 binary. Development was carried out on an aarch64 machine using Mosquitto as the MQTT broker, which implements the same standard MQTT protocol. The agent code connects to any MQTT-compliant broker and is fully compatible with FoxMQ on amd64 systems.

---

## Built For

Vertex Swarm Challenge 2026 — Track 3 | The Agent Economy

Solo builder submission.

---

> SwarmChat is AI-powered and can make mistakes. The swarm coordination layer is deterministic — the AI responses are not.
