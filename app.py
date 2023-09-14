import streamlit as st

from lovelaice import MonsterAPI, Document
from lovelaice.models import Chunk

st.set_page_config("Lovelaice", "🤖", "wide")

api_key = st.sidebar.text_input("🔑 MonsterAPI Key")

if not api_key:
    st.error("⚠️ Please paste your MonsterAPI.ai API KEY.")
    st.stop()

api = MonsterAPI(api_key=api_key)

file = st.sidebar.file_uploader("📣 Text or audio file", ["mp3", "txt"], False)

input_tab, edit_tab, query_tab = st.tabs(["🎁 Input", "📝 Edit", "🗨️ Query"])

with input_tab:

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
                st.session_state.doc = Document(file.read().decode("utf8"))
    else:
        st.warning("Please upload an MP3 file to transcribe or a text file.")

    doc: Document = st.session_state.get("doc")

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

    chunks = st.sidebar.number_input("Chunk into sentences", min_value=1, value=5)

    if st.button("✂️ Chunk document (destructive)"):
        doc.sentences = selected
        doc.chunk(chunks)
        st.session_state.doc = doc

with edit_tab:

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
        ],
    )

    instruction = st.sidebar.text_area(
        "Rewrite instruction",
        "Rewrite the following text fixing grammar and spelling issues. Make the tone more formal.",
    )

    fix_reply = st.sidebar.checkbox(
        "Attempt to friendly fix replies",
        True,
        help="An heuristic that attempts to fix when the LLM adds some extra comments like 'Sure, here is the fixed text...'",
    )


    def rewrite(doc, chunk):
        st.toast("Submitting chunk", icon="↗️")

        response = api.generate_text(
            f"{instruction}\n\n{doc.chunks[chunk].rewrite}",
            model=model,
        )

        st.toast("Waiting for response", icon="⚙️")

        response = api.resolve(response)
        text: str = response["result"]["text"].strip()

        if fix_reply:
            if text.endswith('"'):
                text = text.split('"')
                text = text[1].strip()
            if text.startswith("Sure,"):
                text = text.split(':', maxsplit=1)
                text = text[1].strip()

        st.toast("Done!", icon="🪄")

        doc.chunks[chunk].rewrite = text
        st.session_state.doc = doc


    def revert(doc, chunk):
        doc.chunks[chunk].rewrite = doc.chunks[chunk].text
        st.session_state.doc = doc

        st.toast("Reverted", icon="➰")


    def split(doc, chunk):
        previous = doc.chunks[:chunk]
        next = doc.chunks[chunk+1:]

        chunk = doc.chunks[chunk]
        text = chunk.text
        rewrites = chunk.rewrite.split("\n\n")

        chunks = [Chunk(text, rewrite=rewrite) for rewrite in rewrites]
        doc.chunks = previous + chunks + next
        st.session_state.doc = doc

        st.toast("Splitted", icon="🔀")


    for i, chunk in enumerate(doc.chunks):
        cols = st.columns([1, 1, 1, 5])

        if cols[-1].toggle(
            "✏️ Manual edit (toggle back to save)", False, key="edit_%i" % i
        ):
            doc.chunks[i].rewrite = st.text_area(
                "Chunk",
                chunk.rewrite,
                key="text_%i" % i,
                height=200,
                label_visibility="collapsed",
            )
            st.session_state.doc = doc
        else:
            st.write(chunk.rewrite)

        cols[0].button(
            f"🪄 Rewrite",
            key="rewrite_%i" % i,
            use_container_width=True,
            on_click=rewrite,
            args=(doc, i),
        )
        cols[1].button(
            f"➰ Revert",
            key="revert_%i" % i,
            use_container_width=True,
            on_click=revert,
            args=(doc, i),
        )
        cols[2].button(
            f"🔀 Split",
            key="split_%i" % i,
            use_container_width=True,
            on_click=split,
            args=(doc, i),
        )

        st.write("---")


full_doc = "\n\n".join([c.rewrite for c in doc.chunks])

st.sidebar.download_button(
    "📝 Download draft", full_doc, "draft.txt"
)

with query_tab:

    def add_chunk(doc, text):
        doc.chunks.append(Chunk(text))
        st.session_state.doc = doc

        st.toast("➕ Chunk added to document")

    query = st.text_input("Ask a question or instruction about your document:")

    if st.button("Go 🚀"):
        with st.spinner("Processing query.."):
            response = api.generate_text(
                f"{query}\n\n{full_doc}",
                model=model,
            )

        with st.spinner("Waiting for response..."):
            response = api.resolve(response)
            text = response["result"]["text"]
            st.write(text)

        st.button("➕ Add chunk", on_click=add_chunk, args=(doc, text))