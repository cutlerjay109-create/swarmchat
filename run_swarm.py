import subprocess
import sys
import time
import signal

processes = []

def shutdown(sig, frame):
    print("\nShutting down all agents...")
    for p in processes:
        p.terminate()
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)

TOTAL_AGENTS = 3

print("Starting swarm with 3 agents...")
print("=" * 50)

for i in range(1, TOTAL_AGENTS + 1):
    p = subprocess.Popen(
        [sys.executable, "agent.py", str(i), str(TOTAL_AGENTS)],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )
    processes.append(p)
    print(f"Agent {i} launched (PID {p.pid})")
    time.sleep(0.5)

print("=" * 50)
print("All agents running. Press Ctrl+C to stop.\n")

import threading

def stream_output(process, agent_id):
    for line in iter(process.stdout.readline, ""):
        print(f"[Agent {agent_id}] {line}", end="")

threads = []
for i, p in enumerate(processes, 1):
    t = threading.Thread(target=stream_output, args=(p, i), daemon=True)
    t.start()
    threads.append(t)

for p in processes:
    p.wait()

print("\nAll agents finished.")
