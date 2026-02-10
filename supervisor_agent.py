import os
import json
import datetime
import neo4j
import re
import time
from google import genai
from langchain_community.embeddings import OllamaEmbeddings
from neo4j_graphrag.retrievers import VectorRetriever
from neo4j_graphrag.generation import GraphRAG
from neo4j_graphrag.llm.base import LLMInterface
from langchain_community.llms import Ollama
from dataclasses import dataclass
import threading


@dataclass
class LLMResponse:
    content: str


# === 1️⃣ Setup: API + Neo4j ===
GOOGLE_API_KEY = "AIzaSyDioekLy0lcRRMShudYIxvWUO_zY0_rZYc"
client = genai.Client(api_key=GOOGLE_API_KEY)

NEO4J_URI = "neo4j+s://1d0cca9a.databases.neo4j.io"
NEO4J_USER = "neo4j"
NEO4J_PASS = "VVwrlfIgFASoThf5qb-vD-2r62HnNLuXthVzw8xnPPM"
driver = neo4j.GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))


# === 2️⃣ Local Ollama Embeddings ===
embeddings = OllamaEmbeddings(model="nomic-embed-text")


# === 3️⃣ Ollama LLM wrapper ===
class OllamaLLM:
    def __init__(self, model_name="llama3"):
        self.llm = Ollama(model=model_name)

    def invoke(self, prompt: str, message_history=None, system_instruction=None):
        full_prompt = (
            f"{system_instruction}\n\nUser Query:\n{prompt}"
            if system_instruction
            else prompt
        )
        response = self.llm.invoke(full_prompt)
        return LLMResponse(content=response)

    async def ainvoke(self, prompt: str):
        return self.invoke(prompt)

    def __call__(self, prompt: str):
        return self.invoke(prompt)


# === 4️⃣ Initialize VectorRetriever + GraphRAG ===
retriever = VectorRetriever(
    driver=driver, index_name="vectorIndexCTF", embedder=embeddings
)
llm = OllamaLLM("llama3")
graph_rag = GraphRAG(retriever, llm)


# === 5️⃣ Student State Management ===
STATE_PATH = os.path.join("data", "student_state.json")
os.makedirs("data", exist_ok=True)


def load_student_state():
    if not os.path.exists(STATE_PATH):
        return {"students": []}
    with open(STATE_PATH, "r") as f:
        return json.load(f)


def save_student_state(state):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2)


# === 6️⃣ Context Retrieval + Hint Triggers ===
def retrieve_context(student_id: str, query: str):
    print(f"\nRetrieving context for: '{query}' (student={student_id})")

    start_time = time.time()  # 🟩 NEW: Track time start

    result = graph_rag.search(
        query_text=query, retriever_config={"top_k": 5}, return_context=True
    )

    end_time = time.time()  # 🟩 NEW: Track time end
    response_time = round(end_time - start_time, 2)  # 🟩 NEW: duration in seconds

    # === Load existing student state ===
    state = load_student_state()
    students = state.get("students", [])
    student_entry = next((s for s in students if s["id"] == student_id), None)

    # === Retrieve node metadata safely ===
    retrieved_nodes, scores = [], []
    if hasattr(result, "retriever_result") and getattr(
        result, "retriever_result", None
    ):
        try:
            for item in result.retriever_result.items:
                node_name = "Unknown"
                if isinstance(item.content, str):
                    match = re.search(r"'name': '([^']+)'", item.content)
                    if match:
                        node_name = match.group(1)
                retrieved_nodes.append(node_name)
                if isinstance(item.metadata, dict):
                    scores.append(item.metadata.get("score"))
        except Exception as e:
            print(f"⚠️ Error parsing retriever_result: {e}")

    # === Determine interaction type ===
    q_lower = query.lower()
    if "hint" in q_lower:
        interaction_type = "hint_request"
    elif any(
        word in q_lower for word in ["code", "script", "function", "write", "implement"]
    ):
        interaction_type = "code_request"
    elif any(
        word in q_lower
        for word in ["concept", "explain", "definition", "understand", "what is"]
    ):
        interaction_type = "concept_request"
    else:
        interaction_type = "context_request"

    # === Compute node count and repeat count ===
    node_entry_count = len(retrieved_nodes)
    # query_repeat_count = 0
    # if student_entry:
    #     query_repeat_count = sum(1 for t in student_entry["trajectory"] if t["query"].strip().lower() == query.strip().lower())
    query_repeat_count = 0
    semantic_threshold = 0.85  # similarity above this counts as same intent

    if student_entry and student_entry.get("trajectory"):
        current_emb = embeddings.embed_query(query)
        for t in student_entry["trajectory"]:
            past_query = t["query"].strip().lower()
            # 1️⃣ Exact text match
            if past_query == query.strip().lower():
                query_repeat_count += 1
            else:
                # 2️⃣ Semantic similarity check
                try:
                    past_emb = embeddings.embed_query(past_query)
                    # Cosine similarity
                    dot = sum(a * b for a, b in zip(current_emb, past_emb))
                    mag1 = sum(a * a for a in current_emb) ** 0.5
                    mag2 = sum(a * a for a in past_emb) ** 0.5
                    cosine_sim = dot / (mag1 * mag2)
                    if cosine_sim >= semantic_threshold:
                        query_repeat_count += 1
                except Exception as e:
                    print(f"⚠️  Semantic comparison failed for '{past_query}': {e}")
                    continue
    # === 🟩 Hint trigger conditions ===
    hint_triggered = False
    hint_reason = None
    hint_text = None

    # Trigger a hint only if the student repeats the same query multiple times
    if query_repeat_count >= 2:
        hint_triggered = True
        hint_reason = "Repeated query (possible confusion)"
        hint_prompt = (
            f"Provide a short, encouraging hint to help the student progress on: '{query}'. "
            f"Focus on conceptual reinforcement rather than giving the answer directly. "
            f"Context nodes: {retrieved_nodes[:3]}"
        )
        hint_text = llm.invoke(hint_prompt).content.strip()
        print(f"💡 Hint triggered: {hint_reason}\n→ {hint_text}")

    # No previous queries → never trigger hints on first interaction

    # === 🟩 Generate hint if triggered ===
    hint_text = None
    if hint_triggered:
        hint_prompt = f"Provide a short, encouraging hint to help the student progress on: '{query}'. Context nodes: {retrieved_nodes[:3]}"
        hint_text = llm.invoke(hint_prompt).content.strip()
        print(f"💡 Hint triggered: {hint_reason}\n→ {hint_text}")

    elif student_entry and len(student_entry["trajectory"]) >= 3:
        # Check last 3 queries for procedural patterns
        recent_queries = [t["query"].lower() for t in student_entry["trajectory"][-3:]]
        procedural_keywords = [
            "run",
            "fix",
            "load",
            "execute",
            "implement",
            "solve",
            "compile",
            "test",
            "error",
            "code",
        ]

        def is_procedural(q):
            return any(k in q for k in procedural_keywords)

        if all(is_procedural(q) for q in recent_queries + [query.lower()]):
            hint_triggered = True
            hint_reason = "Procedural impasse (stuck on how-to steps)"
            hint_prompt = (
                f"The student has been asking several procedural questions in a row. "
                f"Generate a reflective, conceptual hint encouraging them to focus on the underlying idea of '{query}'. "
                f"Do not reveal exact code; instead, suggest understanding the concept that supports this step."
            )
            hint_text = llm.invoke(hint_prompt).content.strip()
            print(f"Hint triggered: {hint_reason}\n→ {hint_text}")

    # === Log entry ===
    entry = {
        "timestamp": datetime.datetime.now().isoformat(),
        "student_id": student_id,
        "query": query,
        "retrieved_nodes": retrieved_nodes,
        "scores": scores,
        "interaction_type": interaction_type,
        "query_repeat_count": query_repeat_count + 1,
        "node_entry_count": node_entry_count,
        "response_time_sec": response_time,
        "hint_triggered": hint_triggered,
        "hint_reason": hint_reason,
        "hint_text": hint_text,
    }

    if student_entry:
        student_entry["trajectory"].append(entry)
    else:
        students.append({"id": student_id, "trajectory": [entry]})

    state["students"] = students
    save_student_state(state)

    print(
        f"✅ Context retrieval logged. ({interaction_type}, {node_entry_count} nodes, {response_time}s)"
    )

    return result


# === Interactive Run Mode ===
if __name__ == "__main__":
    print("\nSupervisor Agent Interactive Mode (will later link to UI)")
    print("Type your question below (or 'exit' to quit)\n")

    student_id = "student_001"

    def idle_nudge():
        time.sleep(60)  # 60 seconds of inactivity
        if not idle_event.is_set():
            print("\nYou’ve been quiet for a bit... Everything okay?")
            print("You can ask for help, a hint, or just type your next question!\n")

    while True:
        # Reset nudge timer
        idle_event = threading.Event()
        nudge_thread = threading.Thread(target=idle_nudge)
        nudge_thread.daemon = True
        nudge_thread.start()

        query = input("Enter your query: ").strip()
        idle_event.set()  # stop nudge thread if user typed something

        if not query:
            continue
        if query.lower() in {"exit", "quit"}:
            print("Exiting Supervisor Agent. Goodbye!\n")
            break

        result = retrieve_context(student_id, query)
        clean_answer = (
            result.answer.strip()
            if hasattr(result, "answer") and isinstance(result.answer, str)
            else str(getattr(result, "answer", result))
        )

        print("\nResponse (student view):\n")
        print(clean_answer)
        print("\n───────────────────────────────────────────────\n")

        # Optional: log full retriever output for instructor
        os.makedirs("logs", exist_ok=True)
        with open("logs/context_debug.txt", "a") as f:
            f.write(f"\n\n[Query: {query}]\n")
            f.write(f"Answer: {clean_answer}\n")
            f.write(
                f"Retriever Context: {getattr(result, 'retriever_result', 'N/A')}\n"
            )
