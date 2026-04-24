import json
import time
import threading
import os
import sys
import re
from groq import Groq
from tasks import TASKS
from dotenv import load_dotenv
import paho.mqtt.client as mqtt

load_dotenv()

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
MQTT_BROKER = "127.0.0.1"
MQTT_PORT = 1883
HEARTBEAT_INTERVAL = 3
HEARTBEAT_TIMEOUT = 10

client_groq = Groq(api_key=GROQ_API_KEY)

class Agent:
    def __init__(self, agent_id, total_agents):
        self.agent_id = agent_id
        self.total_agents = total_agents
        self.last_seen = {i: time.time() for i in range(1, total_agents + 1) if i != agent_id}
        self.declared_dead = set()
        self.shared_state = {t["id"]: "unclaimed" for t in TASKS}
        self.completed_tasks = {}
        self.running = True

        # MQTT client setup
        self.mqtt = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"agent_{agent_id}"
        )
        self.mqtt.on_connect = self.on_connect
        self.mqtt.on_message = self.on_message

    def on_connect(self, client, userdata, flags, reason_code, properties):
        print(f"[Agent {self.agent_id}] Connected to MQTT broker (FoxMQ-compatible)")
        # subscribe to all swarm topics
        self.mqtt.subscribe("swarm/heartbeat")
        self.mqtt.subscribe("swarm/claim")
        self.mqtt.subscribe("swarm/complete")
        print(f"[Agent {self.agent_id}] Subscribed to swarm mesh")

    def on_message(self, client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            topic = msg.topic
            sender = data.get("agent_id")

            if sender == self.agent_id:
                return  # ignore own messages

            if topic == "swarm/heartbeat":
                self.last_seen[sender] = time.time()

            elif topic == "swarm/claim":
                task_id = data.get("task_id")
                if self.shared_state.get(task_id) == "unclaimed":
                    self.shared_state[task_id] = f"claimed_by_{sender}"
                    print(f"[Agent {self.agent_id}] Noted: Agent {sender} claimed task {task_id}")

            elif topic == "swarm/complete":
                task_id = data.get("task_id")
                self.shared_state[task_id] = "completed"
                print(f"[Agent {self.agent_id}] Noted: Task {task_id} completed by Agent {sender}")

        except Exception as e:
            pass

    def publish(self, topic, data):
        self.mqtt.publish(topic, json.dumps(data))

    def heartbeat_sender(self):
        while self.running:
            self.publish("swarm/heartbeat", {
                "agent_id": self.agent_id,
                "timestamp": time.time()
            })
            time.sleep(HEARTBEAT_INTERVAL)

    def fault_detector(self):
        time.sleep(5)
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
            time.sleep(HEARTBEAT_INTERVAL)

    def work(self):
        time.sleep(2)
        while self.running:
            claimed_task = None
            for task in list(TASKS):
                if not self.running:
                    break
                task_id = task["id"]
                if self.shared_state.get(task_id) == "unclaimed":
                    self.shared_state[task_id] = f"claimed_by_{self.agent_id}"
                    self.publish("swarm/claim", {
                        "agent_id": self.agent_id,
                        "task_id": task_id
                    })
                    print(f"[Agent {self.agent_id}] Claimed task {task_id}: {task['description'][:40]}...")
                    claimed_task = task
                    break

            if not claimed_task:
                all_done = len(self.shared_state) > 0 and all(
                    v == "completed" for v in self.shared_state.values()
                )
                if all_done:
                    print(f"[Agent {self.agent_id}] All tasks complete. Shutting down.")
                    self.running = False
                    break
                time.sleep(1)
                continue

            task_id = claimed_task["id"]
            time.sleep(1)
            success = False
            retries = 0
            while not success and retries < 5 and self.running:
                try:
                    response = client_groq.chat.completions.create(
                        model="llama-3.1-8b-instant",
                        messages=[{"role": "user", "content": claimed_task["description"]}]
                    )
                    result = response.choices[0].message.content
                    self.completed_tasks[task_id] = result
                    self.shared_state[task_id] = "completed"
                    self.publish("swarm/complete", {
                        "agent_id": self.agent_id,
                        "task_id": task_id
                    })
                    print(f"[Agent {self.agent_id}] Completed task {task_id}")
                    success = True
                except Exception as e:
                    retries += 1
                    wait = 6
                    match = re.search(r"try again in ([\d.]+)s", str(e))
                    if match:
                        wait = float(match.group(1)) + 1
                    print(f"[Agent {self.agent_id}] Rate limited, retrying in {wait:.1f}s...")
                    time.sleep(wait)

            if not success:
                self.shared_state[task_id] = "unclaimed"

    def start(self):
        print(f"[Agent {self.agent_id}] Starting up — connecting to MQTT broker...")
        self.mqtt.connect(MQTT_BROKER, MQTT_PORT, 60)
        self.mqtt.loop_start()
        time.sleep(1)

        threads = [
            threading.Thread(target=self.heartbeat_sender, daemon=True),
            threading.Thread(target=self.fault_detector, daemon=True),
            threading.Thread(target=self.work, daemon=True),
        ]
        for t in threads:
            t.start()

        # keep alive
        while self.running:
            time.sleep(0.5)

        self.mqtt.loop_stop()
        self.mqtt.disconnect()
        print(f"[Agent {self.agent_id}] Disconnected from MQTT broker")

if __name__ == "__main__":
    agent_id = int(sys.argv[1])
    total_agents = int(sys.argv[2])
    agent = Agent(agent_id, total_agents)
    agent.start()
