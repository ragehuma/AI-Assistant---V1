import streamlit as st
import os
from mem0 import Memory
from litellm import completion

st.set_page_config(page_title="My Adaptive AI", page_icon="🧠", layout="centered")

# ============== SECRETS → ENVIRONMENT (works perfectly on Cloud) ==============
for key in ["MEM0_API_KEY", "OPENAI_API_KEY", "GROK_API_KEY", 
            "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY"]:
    if key in st.secrets:
        os.environ[key] = st.secrets[key]

# Mem0 Hosted (cloud memory)
memory = Memory()   # automatically reads MEM0_API_KEY from env

if "user_id" not in st.session_state:
    st.session_state.user_id = "default_user"

# ====================== SIDEBAR ======================
with st.sidebar:
    st.title("🧠 Adaptive AI")
    user_id = st.text_input("Your User ID", value=st.session_state.user_id)
    st.session_state.user_id = user_id

    model = st.selectbox(
        "LLM Model",
        ["gpt-4o-mini", "grok-beta", "claude-3-5-sonnet-20241022", 
         "gemini-1.5-flash", "gemini-2.0-flash"]
    )
    st.info("All memories are stored forever in Mem0 cloud.")

# ====================== MAIN CHAT ======================
st.title("Your Long-Term Adaptive Assistant")
st.caption("It remembers everything across devices & any LLM")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask me anything or teach me something..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Retrieve memories
    relevant = memory.search(query=prompt, user_id=user_id, limit=8)
    memories_str = "\n".join([f"• {m['memory']}" for m in relevant.get("results", [])]) or "No memories yet."

    system_prompt = f"""You are a warm, intelligent, long-term adaptive AI assistant.
You remember EVERYTHING important about the user.
Relevant memories:
{memories_str}"""

    # Generate answer
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            response = completion(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            reply = response.choices[0].message.content
            st.markdown(reply)

    st.session_state.messages.append({"role": "assistant", "content": reply})

    # Save to long-term memory (this is your preserved training!)
    memory.add([
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": reply}
    ], user_id=user_id)
