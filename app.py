import streamlit as st

from lovelaice import MonsterAPI, Document

st.set_page_config("Lovelaice", "🤖", "wide")

api_key = st.sidebar.text_input("🔑 MonsterAPI Key")

if not api_key:
    st.error("⚠️ Please paste your MonsterAPI.ai API KEY.")
    st.stop()

api = MonsterAPI(api_key=api_key)

file = st.sidebar.file_uploader("📣 Text or audio file", ["mp3", "txt"], False)

st.write("#### Transcription")

if file:
    if file.name.endswith("mp3"):
        if st.button("🗣️ Transcribe"):
            with st.spinner("Uploading"):
                response = api.transcribe(file)
            with st.spinner("Waiting for response"):
                response = api.resolve(response)

            st.session_state.doc = Document(response["result"]["text"])
    else:
        if st.button("📝 Process"):
            st.session_state.doc = Document(file.read().decode('utf8'))
else:
    st.warning("Please upload an MP3 file to transcribe or a text file.")

doc: Document = st.session_state.get('doc')

if not doc:
    st.warning("Transcription is empty")
    st.stop()

with st.expander("Raw transcription", False):
    st.write(doc.raw)

st.download_button("📝 Download transcription", doc.raw, "transcription.txt")

selected = []

with st.expander("Select sentences to keep"):
    for s in doc.sentences:
        if st.checkbox(s, True):
            selected.append(s)

chunks = st.sidebar.number_input("Chunk into sentences", min_value=1, value=10)

if st.button("✂️ Chunk document (destructive)"):
    doc.sentences = selected
    doc.chunk(chunks)
    st.session_state.doc = doc

st.write("#### Rewrite")

doc = st.session_state.doc

model = st.sidebar.selectbox(
    "Select model",
    [
        "llama2-7b-chat",
        "mpt-7b-instruct",
        "falcon-7b-instruct",
        "mpt-30b-instruct",
        "flan-T5",
        "falcon-40b-instruct",
        "openllama-13B-base",
    ]
)

instruction = st.sidebar.text_area(
    "Rewrite instruction",
    "Rewrite the following text fixing grammar and spelling issues. Reply only with the rewritten text.",
)


def rewrite(doc, chunk):
    with st.spinner(f"Submitting chunk"):
        response = api.generate_text(
            f"{instruction}\n\n{doc.chunks[chunk].rewrite}",
            model=model,
        )
    with st.spinner("Waiting for response"):
        response = api.resolve(response)
        text = response["result"]["text"].split("\n")
        rewrite = " ".join(s for s in text if not (s.startswith("Sure") or s.startswith("As an AI")))

    doc.chunks[chunk].rewrite = rewrite
    st.session_state.doc = doc


def revert(doc, chunk):
    doc.chunks[chunk].rewrite = doc.chunks[chunk].text
    st.session_state.doc = doc


for i, chunk in enumerate(doc.chunks):
    st.write("---")

    if st.checkbox("Edit mode", False, key="edit_%i" % i):
        doc.chunks[i].rewrite = st.text_area("Chunk", chunk.rewrite, key="text_%i" % i, height=200, label_visibility="collapsed")
        st.session_state.doc = doc
    else:
        st.write(chunk.rewrite)

    st.button(f"✏️ Rewrite", key="rewrite_%i" % i, on_click=rewrite, args=(doc, i))
    st.button(f"✏️ Revert", key="revert_%i" % i, on_click=revert, args=(doc, i))


st.write("---")

st.download_button("📝 Download draft", "\n\n".join([c.rewrite for c in doc.chunks]), "draft.txt")
