import os
import abc

from .models import Message


class LLM(abc.ABC):
    @abc.abstractmethod
    def query(self, messages: list[Message], model: str):
        pass

    def query_sync(self, messages: list[Message], model: str):
        return "".join(self.query(messages, model))


try:
    from mistralai.client import MistralClient
    from mistralai.models.chat_completion import ChatMessage


    class MistralLLM(LLM):
        def __init__(self) -> None:
            self.client = MistralClient(api_key=os.getenv("MISTRAL_API_KEY"))

        def query(self, messages: list[Message], model: str):
            for response in self.client.chat_stream(
                model, [ChatMessage(role=m.role, content=m.content) for m in messages]
            ):
                yield response.choices[0].delta.content

except ImportError:
    pass
