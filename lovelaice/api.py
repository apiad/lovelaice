from fastapi import FastAPI
from .core import Agent
from .connectors import OpenAILLM
from .config import LovelaiceConfig
from .tools import *
import uvicorn

app = FastAPI(title="Lovelaice")

config = LovelaiceConfig.load()
llm = OpenAILLM(config.model, config.api_key, config.base_url)
agent: Agent = Agent(llm, tools=[Bash(), Chat(), Interpreter(), Codegen()])


@app.post("/complete/")
async def chat(prompt):
    completion = await llm.complete(prompt, max_tokens=config.max_tokens)
    return dict(completion=prompt + completion)


def run_api(debug, host, port):
    return uvicorn.run("lovelaice.api:app", host=host, port=port, reload=debug)
