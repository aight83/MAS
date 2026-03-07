import os
import uuid
import streamlit as st
import requests

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="MAS RAG System", page_icon="🤖", layout="wide")


# Auth 

def auth_screen():
    st.title("🤖 MAS RAG System")
    st.subheader("Enter your name to log in")
    col1, col2 = st.columns([2, 1])
    with col1:
        name = st.text_input("Username", placeholder="e.g., Sanj", max_chars=30)
    with col2:
        st.write("")
        st.write("")
        if st.button("Log in →", use_container_width=True):
            if name.strip():
                st.session_state.username = name.strip()
                st.session_state.chat_id = None
                st.session_state.messages = []
                st.rerun()
            else:
                st.error("Enter name")

if "username" not in st.session_state:
    auth_screen()
    st.stop()


# Helpers 

def headers():
    return {"X-Username": st.session_state.username}

def load_chats():
    try:
        res = requests.get(f"{BACKEND}/chats", headers=headers(), timeout=10)
        return res.json() if res.ok else []
    except Exception:
        return []

def load_history(chat_id: str):
    try:
        res = requests.get(f"{BACKEND}/history/{chat_id}", headers=headers(), timeout=10)
        if res.ok:
            msgs = res.json().get("messages", [])
            result = []
            for m in msgs:
                result.append({"role": "user", "content": m["query"]})
                result.append({
                    "role": "assistant",
                    "content": m["answer"],
                    "meta": {                          
                        "time_taken": m.get("time_taken", 0),
                        "tokens":     m.get("usage", {}).get("output_tokens", 0),
                        "chat_id":    chat_id,
                        "sources":    m.get("sources_links", []),
                    }
                })
            return result
    except Exception:
        pass
    return []



# Sidebar 

with st.sidebar:
    st.markdown(f"### 👤 {st.session_state.username}")
    if st.button("🚪 Exit", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.divider()

    if st.button("✏️ New chat", use_container_width=True, type="primary"):
        st.session_state.chat_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

    st.markdown("#### 💬 History of chats")
    chats = load_chats()

    if not chats:
        st.caption("No chats yet. Start a new conversation!")
    else:
        for chat in chats:
            preview = chat.get("preview", "No title").strip()[:60] + "..."
            is_active = chat["chat_id"] == st.session_state.get("chat_id")
            label = f"{'▶ ' if is_active else ''}{preview}"
            if st.button(label, key=chat["chat_id"], use_container_width=True):
                st.session_state.chat_id = chat["chat_id"]
                st.session_state.messages = load_history(chat["chat_id"])
                st.rerun()


# Main Chat 

st.title("🤖 MAS RAG System")

# Initialize session state for chat
if st.session_state.get("chat_id") is None:
    st.session_state.chat_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

# History display
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg["role"] == "assistant" and msg.get("meta"):
            meta = msg["meta"]
            with st.expander("ℹ️ Details"):
                col1, col2, col3 = st.columns(3)
                col1.metric("⏱ Time",   f"{meta['time_taken']}s")
                col2.metric("🔢 Tokens", meta["tokens"])
                col3.metric("💬 Chat ID", meta["chat_id"][:8] + "...")
                if meta["sources"]:
                    st.write("📚 Sources:")
                    for src in meta["sources"]:
                        st.badge(src)

# Ввод
query = st.chat_input("Ask a question...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                res = requests.post(
                    f"{BACKEND}/invoke",
                    json={
                        "query":   query,
                        "chat_id": st.session_state.chat_id,
                    },
                    headers=headers(), 
                    timeout=60,
                )
                data = res.json()

                if not res.ok:
                    raise Exception(data.get("detail", "Unknown error"))

                answer = data["response"]
                st.markdown(answer)

                with st.expander("ℹ️ Details"):
                    col1, col2, col3 = st.columns(3)
                    col1.metric("⏱ Time", f"{data['time_taken']}s")
                    col2.metric("🔢 Tokens", data["token_usage"]["total_tokens"])
                    col3.metric("💬 Chat ID", data["chat_id"][:8] + "...")
                    if data["sources"]:
                        st.write("📚 Sources:")
                        for src in data["sources"]:
                            st.badge(src)

            except Exception as e:
                answer = f"Error: {str(e)}"
                st.error(answer)

    st.session_state.messages.append({
    "role": "assistant",
    "content": answer,
    "meta": {
        "time_taken":  data["time_taken"],
        "tokens":      data["token_usage"]["total_tokens"],
        "chat_id":     data["chat_id"],
        "sources":     data["sources"],
        }
    })
    st.session_state.chat_id = data.get("chat_id", st.session_state.chat_id)
