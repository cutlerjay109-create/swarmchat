from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import re
import time
import os
import threading
import json
import socket
from groq import Groq
from tavily import TavilyClient

app = Flask(__name__, template_folder="../templates", static_folder="../static")
CORS(app)

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")

client = Groq(api_key=GROQ_API_KEY)
tavily = TavilyClient(api_key=TAVILY_API_KEY)

SYSTEM_PROMPT = """You are SwarmChat, a highly knowledgeable AI assistant.
When web search results are provided, use them as your primary source of truth.
For coding questions, write clean correct working code with brief explanation.
Be clear, accurate, concise and friendly.
Always remember the full conversation history."""

CODING_KEYWORDS = [
    "write", "code", "function", "script", "program", "debug", "fix",
    "error", "bug", "python", "javascript", "html", "css", "sql",
    "class", "loop", "array", "list", "dict", "api", "regex",
    "algorithm", "implement", "build", "create a", "make a"
]

SEARCH_KEYWORDS = [
    "what is", "who is", "when did", "where is", "how does",
    "price", "news", "today", "current", "latest", "forex",
    "stock", "crypto", "trading", "market", "define", "meaning",
    "explain", "tell me about", "history of", "2024", "2025", "2026"
]

# Swarm state — in-memory for this serverless instance
swarm_state = {
    "agents": {1: "idle", 2: "idle", 3: "idle"},
    "winner": None
}

def needs_search(message):
    msg_lower = message.lower()
    for kw in CODING_KEYWORDS:
        if kw in msg_lower:
            return False
    for kw in SEARCH_KEYWORDS:
        if kw in msg_lower:
            return True
    return True

def search_web(query):
    try:
        results = tavily.search(query=query, max_results=5)
        snippets = []
        for r in results.get("results", []):
            title = r.get("title", "")
            content = r.get("content", "")
            url = r.get("url", "")
            snippets.append(f"Source: {title}\n{content}\nURL: {url}")
        return "\n\n".join(snippets)
    except Exception as e:
        print(f"[SEARCH ERROR] {e}")
        return ""

def agent_attempt(agent_id, messages, result_holder, done_event):
    """Each agent tries to answer. First one wins."""
    try:
        swarm_state["agents"][agent_id] = "busy"
        # stagger agents slightly to avoid simultaneous rate limits
        time.sleep((agent_id - 1) * 0.4)
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=1500
        )
        if not done_event.is_set():
            done_event.set()
            result_holder["response"] = response.choices[0].message.content
            result_holder["agent_id"] = agent_id
            swarm_state["agents"][agent_id] = "done"
    except Exception as e:
        swarm_state["agents"][agent_id] = "failed"
        print(f"[Agent {agent_id}] Error: {e}")

def call_swarm(messages):
    """3 agents race to answer — fastest wins. If one fails others cover."""
    last_user_msg = ""
    for m in reversed(messages):
        if m["role"] == "user":
            last_user_msg = m["content"]
            break

    enriched = list(messages)
    if needs_search(last_user_msg):
        search_context = search_web(last_user_msg)
        if search_context:
            enriched.insert(-1, {
                "role": "system",
                "content": f"Real-time web search results:\n\n{search_context}\n\nUse these as your primary source of truth."
            })

    result_holder = {"response": None, "agent_id": None}
    done_event = threading.Event()

    threads = []
    for i in range(1, 4):
        t = threading.Thread(
            target=agent_attempt,
            args=(i, enriched, result_holder, done_event),
            daemon=True
        )
        threads.append(t)
        t.start()

    # wait max 25 seconds for any agent to respond
    done_event.wait(timeout=25)

    if result_holder["response"]:
        print(f"[SWARM] Agent {result_holder['agent_id']} won the race")
        return result_holder["response"]

    # fallback — try one more time with a single direct call
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=enriched,
            max_tokens=1500
        )
        return response.choices[0].message.content
    except Exception as e:
        return "Sorry, I could not get a response. Please try again."

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    message = data.get("message", "")
    history = data.get("history", [])
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    for msg in history:
        if msg.get("role") in ["user", "assistant"] and msg.get("content"):
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": message})
    response = call_swarm(messages)
    return jsonify({"response": response})

@app.route("/swarm-status", methods=["GET"])
def swarm_status():
    return jsonify(swarm_state)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
