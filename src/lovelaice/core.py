from typing import Callable, Coroutine
from lingo import LLM, Context, Engine, Lingo


class Lovelaice:
    def __init__(self, models):
        self.models = models
        self.default_model = list(models)[0]
        self.skills = []
        self.tools = []

    def skill(self, func: Callable[[Context, Engine], Coroutine]):
        self.skills.append(func)

    def tool(self, func: Callable):
        self.tools.append(func)

    def build(self, model) -> Lingo:
        if model is None:
            model = self.default_model

        return Lingo(
            llm=LLM(**self.models[model])
        )
