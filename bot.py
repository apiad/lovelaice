import logging

from pathlib import Path
from dotenv import load_dotenv
from io import BytesIO
import os
from telegram import Update
from telegram.ext import (
    filters,
    MessageHandler,
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
)

from lovelaice import MonsterAPI, Document

load_dotenv()
api = MonsterAPI(api_key=os.getenv("MONSTER_API"))


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="""
Send me an audio or voice message and I will transcribe it for you.

You can send more than one audio to make one larger transcription.

When done, you can download the transcription file in several formats.

Send /help for detailed instructions."""
    )


async def transcribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="I'm getting the audio."
    )
    file_id = update.effective_message.effective_attachment.file_id
    new_file = await context.bot.get_file(file_id)
    content = BytesIO()
    await new_file.download_to_memory(content)
    content.seek(0)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="I got the audio, uploading to MonsterAPI.",
    )

    attachement = update.effective_message.effective_attachment
    filename = getattr(attachement, 'file_name', 'voice.ogg')

    response = api.transcribe(content, filename)
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Uploaded, waiting for reply."
    )

    result = api.resolve(response)
    doc = Document(result["result"]["text"])

    transcript_path: Path = (
        Path(__file__).parent / f"transcription-{update.effective_chat.id}.txt"
    )

    with transcript_path.open("a") as fp:
        for line in doc.sentences:
            fp.write(line)
            fp.write("\n\n")

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="""
The transcription is ready. Send me another audio or voice to continue, or use one of the following commands:

/txt  - Download text as a .txt file
/md   - Download text as a .md file
/msg  - See text as Telegram message
/done - Discard the current file (⚠️)
""",
    )


async def msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    transcript_path: Path = (
        Path(__file__).parent / f"transcription-{update.effective_chat.id}.txt"
    )

    if not transcript_path.exists():
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="""
No transcription is currently available.
Send an audio or voice message to begin a new one."""
        )
        return

    with open(transcript_path) as fp:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=fp.read()
        )


async def txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    transcript_path: Path = (
        Path(__file__).parent / f"transcription-{update.effective_chat.id}.txt"
    )

    if not transcript_path.exists():
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="""
No transcription is currently available.
Send an audio or voice message to begin a new one."""
        )
        return

    with open(transcript_path) as fp:
        await context.bot.send_document(
            chat_id=update.effective_chat.id, document=fp, filename="transcription.txt"
        )


async def md(update: Update, context: ContextTypes.DEFAULT_TYPE):
    transcript_path: Path = (
        Path(__file__).parent / f"transcription-{update.effective_chat.id}.txt"
    )

    if not transcript_path.exists():
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="""
No transcription is currently available.
Send an audio or voice message to begin a new one."""
        )
        return

    with open(transcript_path) as fp:
        await context.bot.send_document(
            chat_id=update.effective_chat.id, document=fp, filename="transcription.md"
        )


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    transcript_path: Path = (
        Path(__file__).parent / f"transcription-{update.effective_chat.id}.txt"
    )

    if not transcript_path.exists():
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="""
No transcription is currently available.
Send an audio or voice message to begin a new one."""
        )
        return

    transcript_path.unlink()

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Note discarded. Send me an audio message to start a new note."
    )


async def default(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"I don't understand 😞",
    )


if __name__ == "__main__":
    application = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    start_handler = CommandHandler("start", start)
    application.add_handler(start_handler)

    msg_handler = CommandHandler("msg", msg)
    application.add_handler(msg_handler)

    txt_handler = CommandHandler("txt", txt)
    application.add_handler(txt_handler)

    md_handler = CommandHandler("md", md)
    application.add_handler(md_handler)

    done_handler = CommandHandler("done", done)
    application.add_handler(done_handler)

    audio_handler = MessageHandler(filters.VOICE, transcribe)
    application.add_handler(audio_handler)

    default_handler = MessageHandler(filters.TEXT, default)
    application.add_handler(default_handler)

    application.run_polling()
