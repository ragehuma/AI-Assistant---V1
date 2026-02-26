import streamlit as st
import os
from mem0 import MemoryClient
from litellm import completion

st.set_page_config(page_title="My Adaptive Grok Assistant", page_icon="🧠", layout="centered")

# ============== LOAD SECRETS & MAP GROK → XAI ==============
for key in ["MEM0_API_KEY", "GROK_API_KEY", "XAI_API_KEY", "PASSCODE"]:
    if key in st.secrets:
        os.environ[key] = st.secrets[key]

# LiteLLM needs XAI_API_KEY for Grok models
if "GROK_API_KEY" in os.environ and "XAI_API_KEY" not in os.environ:
    os.environ["XAI_API_KEY"] = os.environ["GROK_API_KEY"]

# ============== PASSCODE PROTECTION ==============
if "authenticated" not in st.session_state:
    st.title("🔒 Protected Grok Adaptive Assistant")
    st.caption("Enter passcode to continue")
    passcode_input = st.text_input("Passcode", type="password")
    if st.button("Unlock", type="primary"):
        if passcode_input == st.secrets.get("PASSCODE", ""):
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("❌ Incorrect passcode")
    st.stop()

# ============== HOSTED MEMORY ==============
memory = MemoryClient(api_key=os.environ["MEM0_API_KEY"])

if "user_id" not in st.session_state:
    st.session_state.user_id = "default_user"

if "waiting_for_confirmation" not in st.session_state:
    st.session_state.waiting_for_confirmation = False

# Friendly model names → real LiteLLM model strings
MODEL_MAP = {
    "Grok-4 (Standard)": "xai/grok-4",
    "Grok-4.1 Fast Reasoning": "xai/grok-4-1-fast-reasoning",
    "Grok-4 Fast Reasoning": "xai/grok-4-fast-reasoning",
    # Add "Grok-4 Heavy" below if you have access (SuperGrok Heavy users)
    # "Grok-4 Heavy": "xai/grok-4-heavy",
}

# ====================== SIDEBAR ======================
with st.sidebar:
    st.title("🧠 Grok Adaptive Assistant")
    user_id = st.text_input("Your User ID", value=st.session_state.user_id)
    st.session_state.user_id = user_id

    display_model = st.selectbox(
        "Grok Model",
        options=list(MODEL_MAP.keys())
    )
    actual_model = MODEL_MAP[display_model]
    
    st.info("100% Grok-powered • Memories stored forever.\nType **UPDATE_MEM** for full consistency check.")

# ====================== MAIN CHAT ======================
st.title("Your Long-Term Grok Assistant")
st.caption("Passcode protected • Remembers everything • Pure Grok")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask me anything or teach me something..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # ============== SPECIAL COMMAND: UPDATE_MEM ==============
    if prompt.strip().upper() == "UPDATE_MEM":
        with st.chat_message("assistant"):
            with st.spinner("Scanning ALL your memories for contradictions..."):
                all_data = memory.search(
                    query="", 
                    filters={"user_id": user_id},
                    limit=1000
                )
                memories_list = [item.get("memory", "") for item in all_data.get("results", [])]

                recent = "\n".join([f"{m['role']}: {m['content']}" 
                                  for m in st.session_state.messages[-40:]])

                analysis_prompt = f"""You are an expert memory auditor.
Analyze these stored memories and the recent conversation for any contradictions or outdated facts.

Stored memories:
{chr(10).join(memories_list) if memories_list else "No memories yet."}

Recent conversation:
{recent if recent else "No recent conversation."}

List every contradiction clearly like:
1. Old: "..."
   New: "..."
   Conflict: "..."

If none, reply exactly: "No contradictions found."

End with: "Do you want to proceed with updating the memories?" """

                response = completion(
                    model=actual_model,
                    messages=[{"role": "user", "content": analysis_prompt}],
                    temperature=0.3
                )
                analysis = response.choices[0].message.content

                st.markdown(analysis)
                st.session_state.messages.append({"role": "assistant", "content": analysis})

                if "No contradictions found" not in analysis:
                    st.session_state.waiting_for_confirmation = True
                else:
                    st.session_state.waiting_for_confirmation = False

    # ============== NORMAL CHAT OR CONFIRMATION ==============
    else:
        if st.session_state.waiting_for_confirmation:
            if prompt.strip().upper() in ["YES", "Y", "PROCEED", "OK"]:
                with st.chat_message("assistant"):
                    with st.spinner("Updating all memories..."):
                        recent_msgs = [
                            {"role": m["role"], "content": m["content"]}
                            for m in st.session_state.messages[-40:]
                            if m["role"] != "system"
                        ]
                        if recent_msgs:
                            memory.add(recent_msgs, user_id=user_id)
                            reply = "✅ All memories updated successfully!\nContradictions resolved with latest information."
                        else:
                            reply = "No data to update."
                        st.markdown(reply)
                        st.session_state.messages.append({"role": "assistant", "content": reply})
                        st.session_state.waiting_for_confirmation = False
            else:
                with st.chat_message("assistant"):
                    reply = "Update cancelled."
                    st.markdown(reply)
                    st.session_state.messages.append({"role": "assistant", "content": reply})
                    st.session_state.waiting_for_confirmation = False
        else:
            # Normal chat
            relevant = memory.search(
                query=prompt,
                filters={"user_id": user_id},
                limit=8
            )
            memories_str = "\n".join([f"• {m['memory']}" for m in relevant.get("results", [])]) or "No prior memories yet."

            system_prompt = f"""You are Grok, a warm, intelligent, long-term adaptive assistant built by xAI.
You remember EVERYTHING important about the user.
Relevant memories:
{memories_str}"""

            with st.chat_message("assistant"):
                with st.spinner("Thinking with Grok..."):
                    response = completion(
                        model=actual_model,
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

            if any(x in prompt.lower() for x in ["remember", "correct:", "my preference", "teach"]):
                st.toast("🧠 Taught and remembered forever!", icon="✅")
