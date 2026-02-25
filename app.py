import streamlit as st
import os
from mem0 import Memory
from litellm import completion

st.set_page_config(page_title="My Adaptive AI", page_icon="🧠", layout="centered")

# ============== LOAD SECRETS ==============
for key in ["MEM0_API_KEY", "OPENAI_API_KEY", "GROK_API_KEY",
            "ANTHROPIC_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY", "PASSCODE"]:
    if key in st.secrets:
        os.environ[key] = st.secrets[key]

# ============== PASSCODE PROTECTION ==============
if "authenticated" not in st.session_state:
    st.title("🔒 Protected Adaptive AI")
    st.caption("Enter passcode to continue")
    passcode_input = st.text_input("Passcode", type="password")
    if st.button("Unlock", type="primary"):
        if passcode_input == st.secrets.get("PASSCODE", ""):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ Incorrect passcode")
    st.stop()  # Stop execution until authenticated

# ============== MEMORY & CONFIG ==============
memory = Memory()   # Hosted cloud memory

if "user_id" not in st.session_state:
    st.session_state.user_id = "default_user"

if "waiting_for_confirmation" not in st.session_state:
    st.session_state.waiting_for_confirmation = False

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
    st.info("All memories stored forever in Mem0 cloud.\nType **UPDATE_MEM** for consistency check.")

# ====================== MAIN CHAT ======================
st.title("Your Long-Term Adaptive Assistant")
st.caption("Passcode protected • Remembers everything forever")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask me anything or teach me something..."):
    # Display user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # ============== SPECIAL COMMAND: UPDATE_MEM ==============
    if prompt.strip().upper() == "UPDATE_MEM":
        with st.chat_message("assistant"):
            with st.spinner("Scanning all memories for contradictions..."):
                # Get ALL memories (this is the "recursive search" into entire memory store)
                all_data = memory.get_all(user_id=user_id)
                memories_list = [item.get("memory", "") for item in all_data.get("results", [])]

                # Recent conversation as "new data"
                recent = "\n".join([f"{m['role']}: {m['content']}" 
                                  for m in st.session_state.messages[-40:]])

                analysis_prompt = f"""You are an expert memory auditor.
Analyze these stored memories and the recent conversation for any contradictions, outdated facts, or conflicts.

Stored memories:
{chr(10).join(memories_list) if memories_list else "No memories yet."}

Recent conversation:
{recent if recent else "No recent conversation."}

List every contradiction clearly like:
1. Old: "..."
   New: "..."
   Conflict: "..."

If no contradictions, reply exactly: "No contradictions found."

End with: "Do you want to proceed with updating the memories?" """

                response = completion(
                    model=model,
                    messages=[{"role": "user", "content": analysis_prompt}],
                    temperature=0.3
                )
                analysis = response.choices[0].message.content

                st.markdown(analysis)
                st.session_state.messages.append({"role": "assistant", "content": analysis})

                # Set flag for next message
                if "No contradictions found" not in analysis:
                    st.session_state.waiting_for_confirmation = True
                else:
                    st.session_state.waiting_for_confirmation = False

    # ============== NORMAL CHAT OR CONFIRMATION ==============
    else:
        if st.session_state.waiting_for_confirmation:
            # User is answering YES/NO to update
            if prompt.strip().upper() in ["YES", "Y", "PROCEED", "OK"]:
                with st.chat_message("assistant"):
                    with st.spinner("Updating memories..."):
                        # Re-add recent messages → Mem0 automatically detects & resolves contradictions
                        recent_msgs = [
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.messages[-40:]
                            if m["role"] != "system"
                        ]
                        if recent_msgs:
                            memory.add(recent_msgs, user_id=user_id)
                            reply = "✅ Memories successfully updated!\nAll contradictions resolved using latest information."
                        else:
                            reply = "No recent data to update."
                        st.markdown(reply)
                        st.session_state.messages.append({"role": "assistant", "content": reply})
                        st.session_state.waiting_for_confirmation = False
            else:
                with st.chat_message("assistant"):
                    reply = "Update cancelled. Continuing normal conversation."
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    st.session_state.waiting_for_confirmation = False
        else:
            # Normal chat flow (exactly like before)
            relevant = memory.search(query=prompt, user_id=user_id, limit=8)
            memories_str = "\n".join([f"• {m['memory']}" for m in relevant.get("results", [])]) or "No prior memories yet."

            system_prompt = f"""You are a warm, intelligent, long-term adaptive AI assistant.
You remember EVERYTHING important about the user.
Relevant memories:
{memories_str}"""

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

            # Save to long-term memory
            memory.add([
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": reply}
            ], user_id=user_id)

            # Bonus explicit teaching
            if any(x in prompt.lower() for x in ["remember", "correct:", "my preference", "teach"]):
                st.toast("🧠 Taught and remembered forever!", icon="✅")
