import asyncio
import json
import socket
import time
import os
from groq import Groq
from tasks import TASKS
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
HEARTBEAT_INTERVAL = 3
HEARTBEAT_TIMEOUT = 10
BASE_PORT = 9000

client = Groq(api_key=GROQ_API_KEY)

class Agent:
    def __init__(self, agent_id, total_agents):
        self.agent_id = agent_id
        self.port = BASE_PORT + agent_id
        self.peers = {
            i: BASE_PORT + i
            for i in range(1, total_agents + 1)
            if i != agent_id
        }
        self.last_seen = {i: time.time() for i in self.peers}
        self.declared_dead = set()
        self.completed_tasks = {}
        self.shared_state = {}
        self.running = True
        self.sock = None

    def broadcast(self, message):
        for peer_port in self.peers.values():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.sendto(json.dumps(message).encode(), ("127.0.0.1", peer_port))
                s.close()
            except:
                pass

    async def listen(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", self.port))
        self.sock.settimeout(1.0)
        print(f"[Agent {self.agent_id}] Listening on port {self.port}")
        while self.running:
            try:
                loop = asyncio.get_event_loop()
                data, _ = await loop.run_in_executor(None, self.sock.recvfrom, 4096)
                message = json.loads(data.decode())
                await self.handle_message(message)
            except socket.timeout:
                continue
            except:
                continue

    async def handle_message(self, message):
        t = message.get("type")
        sender = message.get("agent_id")
        if t == "heartbeat":
            self.last_seen[sender] = time.time()
        elif t == "claim":
            task_id = message.get("task_id")
            if self.shared_state.get(task_id) == "unclaimed":
                self.shared_state[task_id] = f"claimed_by_{sender}"
        elif t == "complete":
            task_id = message.get("task_id")
            self.shared_state[task_id] = "completed"

    async def heartbeat_sender(self):
        while self.running:
            self.broadcast({"type": "heartbeat", "agent_id": self.agent_id})
            await asyncio.sleep(HEARTBEAT_INTERVAL)

    async def fault_detector(self):
        await asyncio.sleep(5)
        while self.running:
            now = time.time()
            for peer_id, last in list(self.last_seen.items()):
                if now - last > HEARTBEAT_TIMEOUT and peer_id not in self.declared_dead:
                    self.declared_dead.add(peer_id)
                    print(f"[Agent {self.agent_id}] *** FAULT DETECTED: Agent {peer_id} is dead ***")
                    for task_id, status in self.shared_state.items():
                        if status == f"claimed_by_{peer_id}":
                            self.shared_state[task_id] = "unclaimed"
                            print(f"[Agent {self.agent_id}] Recovering task {task_id} from dead Agent {peer_id}")
            await asyncio.sleep(HEARTBEAT_INTERVAL)

    async def work(self):
        await asyncio.sleep(2)
        while self.running:
            claimed_task = None
            for task in list(TASKS):
                if not self.running:
                    break
                task_id = task["id"]
                if self.shared_state.get(task_id) == "unclaimed":
                    self.shared_state[task_id] = f"claimed_by_{self.agent_id}"
                    self.broadcast({"type": "claim", "agent_id": self.agent_id, "task_id": task_id})
                    print(f"[Agent {self.agent_id}] Claimed task {task_id}: {task['description'][:40]}...")
                    claimed_task = task
                    break
            if not claimed_task:
                all_done = len(self.shared_state) > 0 and all(v == "completed" for v in self.shared_state.values())
                if all_done:
                    print(f"[Agent {self.agent_id}] All tasks complete. Shutting down.")
                    self.running = False
                    break
                await asyncio.sleep(1)
                continue
            task_id = claimed_task["id"]
            await asyncio.sleep(1)
            success = False
            retries = 0
            while not success and retries < 5 and self.running:
                try:
                    response = client.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": claimed_task["description"]}]
                    )
                    result = response.choices[0].message.content
                    self.completed_tasks[task_id] = result
                    self.shared_state[task_id] = "completed"
                    self.broadcast({"type": "complete", "agent_id": self.agent_id, "task_id": task_id})
                    print(f"[Agent {self.agent_id}] Completed task {task_id}")
                    success = True
                except Exception as e:
                    retries += 1
                    import re
                    wait = 6
                    match = re.search(r"try again in ([\d.]+)s", str(e))
                    if match:
                        wait = float(match.group(1)) + 1
                    print(f"[Agent {self.agent_id}] Rate limited, retrying in {wait:.1f}s...")
                    await asyncio.sleep(wait)
            if not success:
                self.shared_state[task_id] = "unclaimed"

    async def start(self):
        print(f"[Agent {self.agent_id}] Starting up...")
        for task in TASKS:
            self.shared_state[task["id"]] = "unclaimed"
        await asyncio.gather(
            self.listen(),
            self.heartbeat_sender(),
            self.fault_detector(),
            self.work()
        )

if __name__ == "__main__":
    import sys
    agent_id = int(sys.argv[1])
    total_agents = int(sys.argv[2])
    agent = Agent(agent_id, total_agents)
    asyncio.run(agent.start())
