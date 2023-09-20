import logging
from dotenv import load_dotenv
from io import BytesIO
import os
from telegram import Update
from telegram.ext import filters, MessageHandler, ApplicationBuilder, ContextTypes, CommandHandler

from lovelaice import MonsterAPI, Document

load_dotenv()
api = MonsterAPI(api_key=os.getenv("MONSTER_API"))


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")


async def transcribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="I'm getting the audio.")
    file_id = update.effective_message.effective_attachment.file_id
    new_file = await context.bot.get_file(file_id)
    content = BytesIO()
    await new_file.download_to_memory(content)
    content.seek(0)

    await context.bot.send_message(chat_id=update.effective_chat.id, text="I got the audio, uploading to MonsterAPI.")

    response = api.transcribe(content, "voice.ogg")
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Uploaded, waiting for reply.")

    result = api.resolve(response)
    doc = Document(result['result']['text'])

    with open("transcription.txt", "w") as fp:
        for line in doc.sentences:
            fp.write(line)
            fp.write("\n")

    await context.bot.send_message(chat_id=update.effective_chat.id, text='Here is your transcription.')
    await context.bot.send_document(chat_id=update.effective_chat.id, document="transcription.txt")


async def default(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"I don't know what to do with: '{update.message.text}'")


if __name__ == '__main__':
    application = ApplicationBuilder().token(os.getenv("BOT_TOKEN")).build()

    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    audio_handler = MessageHandler(filters.VOICE, transcribe)
    application.add_handler(audio_handler)

    default_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), default)
    application.add_handler(default_handler)

    application.run_polling()