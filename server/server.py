from lsprotocol.types import (
    TEXT_DOCUMENT_CODE_ACTION,
    CodeActionParams,
    MessageType,
    Command,
    Range,
    Position,
    TextDocumentEdit,
    WorkspaceEdit,
    OptionalVersionedTextDocumentIdentifier,
    TextEdit,
)

from pygls.server import LanguageServer
from pygls.workspace import Document, Workspace
from .utils import extract_paragraph_around
import openai
import os

openai.api_key = os.getenv("OPENAI_KEY")


def _fix_syntax_and_grammar(text):
    return openai.Edit.create(
        model="text-davinci-edit-001",
        input=text,
        instruction="Fix the grammar and spelling mistakes",
        temperature=0.7,
        top_p=1,
    )["choices"][0]["text"].strip()


def _complete_text(text, temperature=0.7, max_tokens=256):
    return openai.Completion.create(
        model="text-davinci-003",
        prompt=text,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=1,
        frequency_penalty=0,
        presence_penalty=0,
    )["choices"][0]["text"].strip()


def _summarize(text):
    return _complete_text(text + "\n\nTL;DR:")


def _expand(text):
    return _complete_text(
        "Expand the following text, explaining each idea in more detail:\n\n" + text
    )


def _define(paragraph, text):
    return _complete_text(
        f'In the following paragraph, what is the meaning of the phrase "{text}":\n\n'
        + paragraph + "\n\n"
    )


def _evaluate(text):
    return _complete_text("Answer with a short phrase, what is the tone, difficulty (low, medium, high), audience, and overall sentiment of the following text:\n\n" + text + "\n\n", temperature=0)


def _brainstorm(text):
    return _complete_text("Brainstorm ideas based on the following premise:\n\n" + text)


def _edit_doc(doc, range, new_text):
    return TextDocumentEdit(
        text_document=OptionalVersionedTextDocumentIdentifier(
            uri=doc.uri, version=doc.version
        ),
        edits=[TextEdit(range, new_text)],
    )


class Server(LanguageServer):
    current_doc_uri: str = None

    def get_current_doc(self) -> Document:
        return self.workspace.get_document(self.current_doc_uri)


server = Server("Lovelaice", "v0.1")


@server.feature(TEXT_DOCUMENT_CODE_ACTION)
def on_code_action(ls: Server, params: CodeActionParams):
    uri = params.text_document.uri
    range = params.range

    return [
        Command("🪄 Continue this text", "completeText", (uri, range)),
        Command("🔍 What does this mean?", "define", (uri, range)),
        Command("✨ Expand & explain", "expand", (uri, range)),
        Command("💡 Brainstorm", "brainstorm", (uri, range)),
        Command("🚩 Summarize", "summarize", (uri, range)),
        Command("🔧 Quick fix", "fixGrammar", (uri, range)),
        Command("💖 Evaluate", "evaluate", (uri, range)),
    ]


@server.thread()
@server.command("fixGrammar")
def fix_syntax_and_grammar(ls: Server, args):
    uri, range = args
    range = Range(start=Position(**range["start"]), end=Position(**range["end"]))

    doc: Document = ls.workspace.get_document(uri)
    start = doc.offset_at_position(range.start)
    end = doc.offset_at_position(range.end)

    if abs(start - end) <= 20:
        ls.show_message("Select a larger fragment of text.", MessageType.Error)
        return

    text = doc.source[start:end]
    ls.show_message("⌛ Querying the OpenAI API...")
    fix = _fix_syntax_and_grammar(text)

    ls.apply_edit(WorkspaceEdit(document_changes=[_edit_doc(doc, range, fix)]))
    ls.show_message("Replaced %i characters" % len(text))


@server.thread()
@server.command("completeText")
def complete_text(ls: Server, args):
    uri, range = args
    range = Range(start=Position(**range["start"]), end=Position(**range["end"]))

    doc: Document = ls.workspace.get_document(uri)
    start = doc.offset_at_position(range.start)
    end = doc.offset_at_position(range.end)

    if abs(start - end) <= 20:
        ls.show_message("Select a larger fragment of text.", MessageType.Error)
        return

    text = doc.source[start:end]
    ls.show_message("⌛ Querying the OpenAI API...")
    completion = _complete_text(text)

    ls.apply_edit(
        WorkspaceEdit(document_changes=[_edit_doc(doc, range, text + completion)])
    )
    ls.show_message("Inserted %i characters" % len(completion))


@server.thread()
@server.command("summarize")
def summarize(ls: Server, args):
    uri, range = args
    range = Range(start=Position(**range["start"]), end=Position(**range["end"]))

    doc: Document = ls.workspace.get_document(uri)
    start = doc.offset_at_position(range.start)
    end = doc.offset_at_position(range.end)

    if abs(start - end) <= 100:
        ls.show_message("Select a larger fragment of text.", MessageType.Error)
        return

    text = doc.source[start:end]
    ls.show_message("⌛ Querying the OpenAI API...")
    summary = _summarize(text)

    ls.apply_edit(
        WorkspaceEdit(
            document_changes=[_edit_doc(doc, range, text + "\n\nTL;DR: " + summary)]
        )
    )
    ls.show_message("Inserted %i characters" % len(summary))


@server.thread()
@server.command("expand")
def expand(ls: Server, args):
    uri, range = args
    range = Range(start=Position(**range["start"]), end=Position(**range["end"]))

    doc: Document = ls.workspace.get_document(uri)
    start = doc.offset_at_position(range.start)
    end = doc.offset_at_position(range.end)

    if abs(start - end) <= 20:
        ls.show_message("Select a larger fragment of text.", MessageType.Error)
        return

    text = doc.source[start:end]
    ls.show_message("⌛ Querying the OpenAI API...")
    replacement = _expand(text)

    ls.apply_edit(WorkspaceEdit(document_changes=[_edit_doc(doc, range, replacement)]))
    ls.show_message("Replaced %i characters" % len(replacement))


@server.thread()
@server.command("brainstorm")
def brainstorm(ls: Server, args):
    uri, range = args
    range = Range(start=Position(**range["start"]), end=Position(**range["end"]))

    doc: Document = ls.workspace.get_document(uri)
    start = doc.offset_at_position(range.start)
    end = doc.offset_at_position(range.end)

    if abs(start - end) <= 20:
        ls.show_message("Select a larger fragment of text.", MessageType.Error)
        return

    text = doc.source[start:end]
    ls.show_message("⌛ Querying the OpenAI API...")
    replacement = _brainstorm(text)

    ls.apply_edit(
        WorkspaceEdit(
            document_changes=[_edit_doc(doc, range, text + "\n\n" + replacement)]
        )
    )
    ls.show_message("Inserted %i characters" % len(replacement))


@server.thread()
@server.command("define")
def define(ls: Server, args):
    uri, range = args
    range = Range(start=Position(**range["start"]), end=Position(**range["end"]))

    doc: Document = ls.workspace.get_document(uri)
    start = doc.offset_at_position(range.start)
    end = doc.offset_at_position(range.end)

    if abs(start - end) <= 3:
        ls.show_message("Select a larger fragment of text.", MessageType.Error)
        return

    if abs(start - end) >= 128:
        ls.show_message("Select a shorter fragment of text.", MessageType.Error)
        return

    text = doc.source[start:end]
    paragraph = extract_paragraph_around(doc.source, start, end)

    ls.show_message("⌛ Querying the OpenAI API...")
    definition = _define(paragraph, text)

    ls.show_message("🔎 " + definition)

@server.thread()
@server.command("evaluate")
def evaluate(ls: Server, args):
    uri, range = args
    range = Range(start=Position(**range["start"]), end=Position(**range["end"]))

    doc: Document = ls.workspace.get_document(uri)
    start = doc.offset_at_position(range.start)
    end = doc.offset_at_position(range.end)

    if abs(start - end) >= 10:
        text = doc.source[start:end]
    else:
        text = extract_paragraph_around(doc.source, start, end)

    ls.show_message("⌛ Querying the OpenAI API...")
    evaluation = _evaluate(text)

    ls.show_message("💖 " + evaluation)
