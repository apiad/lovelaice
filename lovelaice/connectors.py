import abc
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionChunk
from openai.types.completion import Completion

from .config import LovelaiceConfig
from .models import Message


class LLM(abc.ABC):
    def __init__(self, config: LovelaiceConfig) -> None:
        self.config = config

    async def chat(self, messages: list[Message], **kwargs):
        result = []

        async for chunk in self.chat_stream(messages, **kwargs):
            result.append(chunk)

        return "".join(result)

    async def complete(self, prompt: str, **kwargs):
        result = []

        async for chunk in self.complete_stream(prompt, **kwargs):
            result.append(chunk)

        return "".join(result)

    async def chat_stream(self, messages: list[Message], **kwargs):
        client = AsyncOpenAI(api_key=self.config.chat_model.api_key, base_url=self.config.chat_model.base_url)
        model = self.config.chat_model.model

        stream = await client.chat.completions.create(
            messages=[dict(role=m.role, content=m.content) for m in messages],
            model=model,
            stream=True,
            **kwargs,
        )

        async for response in stream:
            r: ChatCompletionChunk = response
            yield r.choices[0].delta.content or ""

    async def complete_stream(self, prompt: str, **kwargs):
        client = AsyncOpenAI(api_key=self.config.chat_model.api_key, base_url=self.config.chat_model.base_url)
        model = self.config.chat_model.model

        stream = await client.completions.create(
            model=model, prompt=prompt, stream=True, **kwargs
        )

        async for chunk in stream:
            r: Completion = chunk
            yield r.choices[0].text or ""

    async def transcribe(self, file, **kwargs):
        client = AsyncOpenAI(api_key=self.config.audio_model.api_key, base_url=self.config.audio_model.base_url)
        model = self.config.audio_model.model

        response = await client.audio.transcriptions.create(file=file, model=model, **kwargs)
        return response
