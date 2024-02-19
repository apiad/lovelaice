import os
import asyncio
import abc

from .models import Message


class LLM(abc.ABC):
    @abc.abstractmethod
    async def query(self, messages: list[Message]):
        pass

    async def query_all(self, messages: list[Message]):
        result = []

        async for response in self.query(messages):
            result.append(response)

        return "".join(result)


try:
    from mistralai.async_client import MistralAsyncClient
    from mistralai.models.chat_completion import ChatMessage


    class MistralLLM(LLM):
        def __init__(self, model:str, api_key:str=None) -> None:
            self.client = MistralAsyncClient(api_key=api_key or os.getenv("MISTRAL_API_KEY"))
            self.model = model

        async def query(self, messages: list[Message]):
            async for response in self.client.chat_stream(
                self.model, [ChatMessage(role=m.role, content=m.content) for m in messages]
            ):
                yield response.choices[0].delta.content

except ImportError:
    pass
