import os
import abc

from .models import Message


class LLM(abc.ABC):
    async def chat(self, messages: list[Message]):
        result = []

        async for chunk in self.chat_stream(messages):
            result.append(chunk)

        return "".join(result)

    @abc.abstractmethod
    async def chat_stream(self, messages: list[Message]):
        pass

try:
    from openai import AsyncOpenAI

    class OpenAILLM(LLM):
        def __init__(self, model: str, api_key: str, base_url: str = None) -> None:
            self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
            self.model = model

        async def chat_stream(self, messages: list[Message]):
            stream = await self.client.chat.completions.create(
                messages=[dict(role=m.role, content=m.content) for m in messages],
                model=self.model,
                stream=True,
            )

            async for response in stream:
                yield response.choices[0].delta.content or ""

except ImportError:
    pass
