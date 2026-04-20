from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import re
import time
import os
from groq import Groq
from tavily import TavilyClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
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

def needs_search(message):
    msg_lower = message.lower()
    for kw in CODING_KEYWORDS:
        if kw in msg_lower:
            print(f"[ROUTER] Coding — skipping search")
            return False
    for kw in SEARCH_KEYWORDS:
        if kw in msg_lower:
            print(f"[ROUTER] Factual — searching web")
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
        combined = "\n\n".join(snippets)
        print(f"[SEARCH] Found {len(snippets)} results")
        return combined
    except Exception as e:
        print(f"[SEARCH ERROR] {e}")
        return ""

def call_groq(messages):
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

    for attempt in range(5):
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=enriched,
                max_tokens=1500
            )
            return response.choices[0].message.content
        except Exception as e:
            wait = 6
            match = re.search(r"try again in ([\d.]+)s", str(e))
            if match:
                wait = float(match.group(1)) + 1
            print(f"[ERROR] attempt {attempt+1}: {e}")
            time.sleep(wait)
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
    response = call_groq(messages)
    return jsonify({"response": response})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
