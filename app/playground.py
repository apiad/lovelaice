import streamlit as st
from lovelaice.core import Agent
from lovelaice.connectors import MistralLLM


st.set_page_config("Lovelaice Playground", "🤖")

MISTRAL_API_KEY = st.secrets.get("MISTRAL_API_KEY")


@st.cache_resource
def get_agent():
    return Agent(client=MistralLLM("mistral-small", MISTRAL_API_KEY), tools=[])


agent = get_agent()

messages = st.container()

query = st.chat_input()

if query:
    with messages.chat_message("human"):
        st.write(query)

    reply = agent.query()
