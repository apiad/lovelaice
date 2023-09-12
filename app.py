import streamlit as st

from lovelaice import MonsterAPI

api_key = st.text_input("🔑 MonsterAPI Key")

if not api_key:
    st.error("⚠️ Please paste your MonsterAPI.ai API KEY.")
    st.stop()

api = MonsterAPI(api_key=api_key)

file = st.file_uploader("📣 Audio file", "mp3", False)

if not file:
    st.warning("Please upload an MP3 file to transcribe.")
    st.stop()

if file.size >= 8 * 1024 * 1024:
    st.warning("⚠️ MonsterAPI does not support files bigger than 8 MB. Only the first 8 MB will be uploaded.")
    file.truncate(7 * 1024 * 1024)

if st.button("🗣️ Transcribe"):
    with st.spinner("Uploading"):
        response = api.transcribe(file)
    with st.spinner("Waiting for response"):
        response = api.resolve(response)

    st.write("#### Raw response")
    st.json(response, expanded=False)
    st.session_state["raw_transcription"] = response["result"]["text"]

transcription = st.session_state.get("raw_transcription", "")

st.write("#### Transcription")

if not transcription:
    st.warning("Transcription is empty")
    st.stop()

st.write(transcription)

st.write("#### Rewrite")

instruction = st.text_input("Rewrite instruction", "Rewrite the previous text fixing grammar and spelling issues.")

cols = st.columns([2,1])
model = cols[0].selectbox(
    "Select model",
    [
        "llama2-7b-chat",
        "mpt-7b-instruct",
        "falcon-7b-instruct",
        "mpt-30b-instruct",
        "flan-T5",
        "falcon-40b-instruct",
        "openllama-13B-base",
    ],
    label_visibility="collapsed"
)

if cols[1].button("✏️ Rewrite", use_container_width=True):
    with st.spinner("Submitting"):
        response = api.generate_text(
            f"{transcription}\n\n{instruction}",
            model=model,
        )
    with st.spinner("Waiting for response"):
        response = api.resolve(response)

    st.write("#### Raw response")
    st.json(response, expanded=False)
    st.session_state["rewrite"] = response["result"]["text"]

st.write(st.session_state.get("rewrite"))
