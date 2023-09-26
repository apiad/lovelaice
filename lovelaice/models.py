import re

class Chunk:
    def __init__(self, text:str, *, rewrite:str=None) -> None:
        self.text = text
        self.rewrite = rewrite or text


class Document:
    def __init__(self, raw) -> None:
        self.raw = raw
        self.sentences = self._split(self.raw)
        self.chunks = []

    def _split(self, text: str):
        return [s.strip() + "." for s in text.split(".") if s]

    def chunk(self, size:int, overlap:int=0) -> list[str]:
        self.chunks = list(self._chunks(size, overlap))

    def _chunks(self, size, overlap):
        current = []

        for s in self.sentences:
            current.append(s)

            if len(current) == size:
                yield Chunk(" ".join(current))

                if overlap > 0:
                    current = current[-overlap:]
                else:
                    current = []

        if current:
            yield Chunk(" ".join(current))


heading_re = re.compile(r"[Hh]eading[,:]?\s(?P<content>.*)")
subheading_re = re.compile(r"[Ss]ubheading[,:]?\s(?P<content>.*)")
title_re = re.compile(r"[Tt]itle[,:]?\s(?P<content>.*)")


class Parser:
    def __init__(self) -> None:
        self.rules = {
            title_re: self._build_title,
            heading_re: self._build_heading,
            subheading_re: self._build_subheading,
        }

    def _build_title(self, content: str):
        yield "\n"
        yield "# " + content.strip().capitalize()
        yield "\n"

    def _build_heading(self, content: str):
        yield "\n"
        yield "## " + content.strip().capitalize()
        yield "\n"

    def _build_subheading(self, content: str):
        yield "\n"
        yield "### " + content.strip().capitalize()
        yield "\n"

    def _process(self, sentence:str):
        for rule, action in self.rules.items():
            if m := rule.match(sentence):
                yield from action(m.group("content"))
                return

        yield sentence

    def parse(self, sentences:list[str]) -> list[str]:
        return list(self._parse(*sentences))

    def _parse(self, *sentences: str):
        for s in sentences:
            yield from self._process(s)
