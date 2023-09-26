from lovelaice.models import Parser


def test_title():
    sentences = ["Title: a new hope", "lorem ipsum dolor sit amet"]
    parser = Parser()

    assert parser.parse(sentences) == ["# A new hope", "lorem ipsum dolor sit amet"]


def test_heading():
    sentences = ["Heading, a new hope", "lorem ipsum dolor sit amet"]
    parser = Parser()

    assert parser.parse(sentences) == ["## A new hope", "lorem ipsum dolor sit amet"]


def test_subheading():
    sentences = ["Subheading a new hope", "lorem ipsum dolor sit amet"]
    parser = Parser()

    assert parser.parse(sentences) == ["### A new hope", "lorem ipsum dolor sit amet"]


def test_ul():
    sentences = ["Something", "Begin unordered list.", "Item 1.", "Item 2.", "end unordered list", "Something else"]
    parser = Parser()

    assert parser.parse(sentences) == [
        "Something",
        "- Item 1.",
        "- Item 2.",
        "Something else",
    ]


def test_ol():
    sentences = ["Something", "Begin ordered list.", "Item 1.", "Item 2.", "end ordered list", "Something else"]
    parser = Parser()

    assert parser.parse(sentences) == [
        "Something",
        "1. Item 1.",
        "2. Item 2.",
        "Something else",
    ]


def test_tl():
    sentences = ["Something", "Begin todo list.", "Item 1.", "Item 2.", "end todo list", "Something else"]
    parser = Parser()

    assert parser.parse(sentences) == [
        "Something",
        "- [ ] Item 1.",
        "- [ ] Item 2.",
        "Something else",
    ]
