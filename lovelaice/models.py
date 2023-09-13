class Chunk:
    def __init__(self, text:str) -> None:
        self.text = text
        self.rewrite = text


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
