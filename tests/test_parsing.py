from lovelaice.models import Parser


def test_title():
    sentences = ["Title: a new hope", "lorem ipsum dolor sit amet"]
    parser = Parser()

    assert parser.parse(sentences) == ["\n", "# A new hope", "\n", "lorem ipsum dolor sit amet"]


def test_heading():
    sentences = ["Heading, a new hope", "lorem ipsum dolor sit amet"]
    parser = Parser()

    assert parser.parse(sentences) == ["\n", "## A new hope", "\n", "lorem ipsum dolor sit amet"]


def test_subheading():
    sentences = ["Subheading a new hope", "lorem ipsum dolor sit amet"]
    parser = Parser()

    assert parser.parse(sentences) == ["\n", "### A new hope", "\n", "lorem ipsum dolor sit amet"]
