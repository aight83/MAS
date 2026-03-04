import os
import uuid
import streamlit as st
import requests

BACKEND = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="MAS RAG System", page_icon="🤖")
st.title("🤖 MAS RAG System")

# Инициализируем chat_id для сессии
if "chat_id" not in st.session_state:
    st.session_state.chat_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

# Отображаем историю сообщений
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Поле ввода
query = st.chat_input("Задай вопрос...")

if query:
    st.session_state.messages.append({"role": "user", "content": query})
    with st.chat_message("user"):
        st.write(query)

    with st.chat_message("assistant"):
        with st.spinner("Думаю..."):
            try:
                res = requests.post(
                    f"{BACKEND}/invoke",
                    json={
                        "query": query,
                        "chat_id": st.session_state.chat_id,
                    },
                    timeout=60,
                )
                data = res.json()
                answer = data["response"]
                st.write(answer)

                # Метаданные
                with st.expander("ℹ️ Детали"):
                    st.write(f"⏱ Время: {data['time_taken']}s")
                    st.write(f"💬 Chat ID: {data['chat_id']}")
                    if data["sources"]:
                        st.write("📚 Источники:", data["sources"])

            except Exception as e:
                answer = f"Ошибка: {str(e)}"
                st.error(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})
