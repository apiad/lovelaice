import re

class Chunk:
    def __init__(self, text:str, *, rewrite:str=None) -> None:
        self.text = text
        self.rewrite = rewrite or text


class Document:
    def __init__(self, raw, parse=True) -> None:
        self.raw = raw
        self.sentences = Parser().parse(self._split(self.raw)) if parse else raw.split("\n")
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

    def __str__(self) -> str:
        return "\n".join(self.sentences)


heading_re = re.compile(r"[Hh]eading[,:]? (?P<content>.*)")
subheading_re = re.compile(r"[Ss]ubheading[,:]? (?P<content>.*)")
title_re = re.compile(r"[Tt]itle[,:]? (?P<content>.*)")

being_ul = re.compile(r"[Bb]egin unorder(ed)? list.*")
end_ul = re.compile(r"[Ee]nd unorder(ed)? list.*")
being_ol = re.compile(r"[Bb]egin order(ed)? list.*")
end_ol = re.compile(r"[Ee]nd order(ed)? list.*")
being_tl = re.compile(r"[Bb]egin todo list.*")
end_tl = re.compile(r"[Ee]nd todo list.*")


class Parser:
    def __init__(self) -> None:
        self.rules = {
            title_re: self._build_section("#"),
            heading_re: self._build_section("##"),
            subheading_re: self._build_section("###"),

            being_ul: self._toggle_prefix("- ", skip=True),
            end_ul: self._toggle_prefix("", skip=True),
            being_ol: self._toggle_prefix(1, skip=True),
            end_ol: self._toggle_prefix("", skip=True),
            being_tl: self._toggle_prefix("- [ ] ", skip=True),
            end_tl: self._toggle_prefix("", skip=True),
        }

        self.prefix = ""

    def _toggle_prefix(self, prefix, skip):
        def _build(content: str):
            self.prefix = prefix
            if skip: return
            yield content

        return _build

    def _build_section(self, mark):
        def _build(content: str):
            yield f"{mark} {content.strip().capitalize()}"

        return _build

    def _process(self, sentence:str):
        for rule, action in self.rules.items():
            if m := rule.match(sentence):
                yield from action(m.groupdict().get("content", ""))
                return

        if isinstance(self.prefix, int):
            prefix = f"{self.prefix}. "
            self.prefix += 1
        else:
            prefix = self.prefix

        yield f"{prefix}{sentence}"

    def parse(self, sentences:list[str]) -> list[str]:
        return list(self._parse(*sentences))

    def _parse(self, *sentences: str):
        for s in sentences:
            yield from self._process(s)
