from __future__ import annotations

from lingo import LLM, Lingo


class Lovelaice(Lingo):
    def __init__(self, llm: LLM, prompt: str):
        super().__init__(
            name="Lovelaice",
            description="An AI engineering assistant.",
            llm=llm,
            system_prompt=prompt,
        )
