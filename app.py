import streamlit as st

from lovelaice import MonsterAPI, Document

st.set_page_config("Lovelaice", "🤖", "wide")

api_key = st.sidebar.text_input("🔑 MonsterAPI Key")

if not api_key:
    st.error("⚠️ Please paste your MonsterAPI.ai API KEY.")
    st.stop()

api = MonsterAPI(api_key=api_key)

file = st.sidebar.file_uploader("📣 Audio file", "mp3", False)


st.write("#### Transcription")

if file:
    if st.button("🗣️ Transcribe"):
        with st.spinner("Uploading"):
            response = api.transcribe(file)
        with st.spinner("Waiting for response"):
            response = api.resolve(response)

        st.session_state["raw_transcription"] = response["result"]["text"]
else:
    st.warning("Please upload an MP3 file to transcribe.")

transcription = st.session_state.get("raw_transcription", "")

if not transcription:
    st.warning("Transcription is empty")
    st.stop()

with st.expander("Raw transcription", False):
    st.write(transcription)

doc = Document(transcription)
selected = []

with st.expander("Sentences"):
    for s in doc.sentences:
        if st.checkbox(s, True):
            selected.append(s)

doc.sentences = selected

st.download_button("📝 Download transcription", "\n".join(selected), "transcription.txt")

st.write("#### Rewrite")

instruction = st.text_input(
    "Rewrite instruction",
    "Rewrite the previous text fixing grammar and spelling issues",
)

cols = st.columns([2, 1])
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
    label_visibility="collapsed",
)

doc.chunk(
    st.sidebar.number_input("Chunk into sentences", min_value=1, value=10),
    st.sidebar.number_input("Chunk overlap", min_value=0, value=0),
)

block = st.container()

selected_chunks = []

for chunk in doc.chunks:
    if st.checkbox(chunk, True):
        selected_chunks.append(chunk)

if cols[1].button(f"✏️ Rewrite {len(selected_chunks)} chunks", use_container_width=True):
    progress = block.progress(0)
    results = []

    with block:
        for i, chunk in enumerate(selected_chunks):
            progress.progress((i+1) / len(selected_chunks), f"Rewriting {len(selected_chunks)} chunks...")
            with st.spinner(f"Submitting chunk #{i+1}"):
                response = api.generate_text(
                    f"{chunk}\n\n{instruction}",
                    model=model,
                )
            with st.spinner("Waiting for response"):
                response = api.resolve(response)
                results.append(response["result"]["text"])

    st.session_state["rewrite"] = results

st.write("---")

for chunk in st.session_state.get("rewrite", []):
    st.write(chunk)
