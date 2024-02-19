import os
import abc
from typing import Coroutine

from .models import Message


class LLM(abc.ABC):
    @abc.abstractmethod
    def query(self, messages: list[Message]):
        pass

    def query_sync(self, messages: list[Message]) -> str:
        return "".join(self.query(messages))


try:
    from mistralai.client import MistralClient
    from mistralai.models.chat_completion import ChatMessage


    class MistralLLM(LLM):
        def __init__(self, model:str) -> None:
            self.client = MistralClient(api_key=os.getenv("MISTRAL_API_KEY"))
            self.model = model

        def query(self, messages: list[Message]):
            for response in self.client.chat_stream(
                self.model, [ChatMessage(role=m.role, content=m.content) for m in messages]
            ):
                yield response.choices[0].delta.content

except ImportError:
    pass
