import os
import abc

from .models import Message


class LLM(abc.ABC):
    async def chat(self, messages: list[Message], **kwargs):
        result = []

        async for chunk in self.chat_stream(messages, **kwargs):
            result.append(chunk)

        return "".join(result)

    @abc.abstractmethod
    async def chat_stream(self, messages: list[Message], **kwargs):
        pass

    @abc.abstractmethod
    async def complete_stream(self, prompt: str, **kwargs):
        pass


try:
    from openai import AsyncOpenAI
    from openai.types.chat import ChatCompletionChunk
    from openai.types.completion import Completion

    class OpenAILLM(LLM):
        def __init__(self, model: str, api_key: str, base_url: str = None) -> None:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
            self.model = model

        async def chat_stream(self, messages: list[Message], **kwargs):
            stream = await self.client.chat.completions.create(
                messages=[dict(role=m.role, content=m.content) for m in messages],
                model=self.model,
                stream=True,
                **kwargs,
            )

            async for response in stream:
                r: ChatCompletionChunk = response
                yield r.choices[0].delta.content or ""

        async def complete_stream(self, prompt: str, **kwargs):
            stream = await self.client.completions.create(
                model=self.model, prompt=prompt, stream=True, **kwargs
            )

            async for chunk in stream:
                r: Completion = chunk
                yield r.choices[0].text or ""

except ImportError:
    pass
