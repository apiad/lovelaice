from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from functools import wraps


def query(prompt: str, client: MistralClient, model:str = "mistral-small"):
    return client.chat(model, messages=[
        ChatMessage(role="user", content=prompt)
    ]).choices[0].message.content


def query_async(prompt: str, client: MistralClient, model:str = "mistral-small"):
    for response in client.chat_stream(model, messages=[
        ChatMessage(role="user", content=prompt)
    ]):
        yield response.choices[0].delta.content


def prompt(function):
    client = MistralClient()

    @wraps(function)
    def wrapper(*args, **kwargs):
        template: str = function(*args, **kwargs)
        return query(template, client)

    return wrapper
