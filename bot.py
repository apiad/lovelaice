import logging
import json
import datetime

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
admin = os.getenv('ADMIN')

data_folder = Path(__file__).parent / "data" / "bot"

with open(Path(__file__).parent / "bot_help.md") as fp:
    help_text = fp.read()


def _get_data(user_id) -> Path:
    user_folder = data_folder / str(user_id)
    user_folder.mkdir(parents=True, exist_ok=True)
    return user_folder


def _get_user_data(user_id):
    user_data = _get_data(user_id) / ".user.json"

    if not user_data.exists():
        _store_user_data(user_id, dict(credits=100))

    with open(user_data) as fp:
        return json.load(fp)


def _store_user_data(user_id, data):
    user_data = _get_data(user_id) / ".user.json"

    with open(user_data, "w") as fp:
        json.dump(data, fp, indent=2)


def _update_credits(user_id, delta_credits):
    data = _get_user_data(user_id)
    data["credits"] += delta_credits
    _store_user_data(user_id, data)


def _select_note(user_id, name=None):
    selected_file = _get_data(user_id) / ".selected-note"

    if name:
        with open(selected_file, "w") as fp:
            fp.write(name)
    else:
        selected_file.unlink(missing_ok=True)


def _get_selected_note(user_id) -> Path:
    selected_file = _get_data(user_id) / ".selected-note"

    if not selected_file.exists():
        return None

    return _get_data(user_id) / str(open(selected_file).read())


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


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = _get_user_data(update.effective_user.username)

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"""
Credits: {data['credits']}

If you need more credits, contact @{admin}."""
    )


async def transcribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = _get_user_data(update.effective_user.username)

    if data['credits'] <= 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="I'm sorry but your out of credits. Send /status to check."
        )
        return

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
    _update_credits(update.effective_user.username, -int(result['credit_used']))
    selected_note = _get_selected_note(update.effective_user.username)
    data = _get_user_data(update.effective_user.username)

    if selected_note:
        transcript_path = selected_note
    else:
        title = doc.sentences[0]
        title = title[:25]
        title = "".join([c for c in title if c.isalnum() or c == " "])
        now = datetime.datetime.now().isoformat()

        transcript_path = _get_data(update.effective_user.username) / f"{title} - {now}.txt"

    with transcript_path.open("a") as fp:
        for line in doc.sentences:
            fp.write(line)
            fp.write("\n")

        fp.write("\n")

    summary = str(doc)[:100] + "..."

    _select_note(update.effective_user.username, transcript_path.name)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"""The transcription is ready.

Remaining credits: {data['credits']}

Summary:
_{summary}_

Send me another audio or voice to continue this note, or one of the following commands:

/msg - Print note as Telegram message.
/txt - Download note as TXT file.
/delete - Delete this note (undoable!)
/done - Finish with this note.
""",
     parse_mode="markdown")


async def msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_note = _get_selected_note(update.effective_user.username)

    if not selected_note:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="""
No note is currently selected.
Send an audio or voice message to begin a new one."""
        )
        return

    with open(selected_note) as fp:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text=fp.read()
        )


async def txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_note = _get_selected_note(update.effective_user.username)

    if not selected_note:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="""
No note is currently selected.
Send an audio or voice message to begin a new one."""
        )
        return

    with open(selected_note) as fp:
        await context.bot.send_document(
            chat_id=update.effective_chat.id, document=fp, filename="transcription.txt"
        )


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_note = _get_selected_note(update.effective_user.username)

    if not selected_note:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="""
No note is currently selected.
Send an audio or voice message to begin a new one."""
        )
        return

    _select_note(update.effective_user.username)

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Done. Send me an audio message to start a new note."
    )


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_note = _get_selected_note(update.effective_user.username)

    if not selected_note:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="""
No note is currently selected.
Send an audio or voice message to begin a new one."""
        )
        return

    selected_note.unlink()
    _select_note(update.effective_user.username)

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Note discarded. Send me an audio message to start a new note."
    )


async def select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    notes = [path.name for path in _get_data(update.effective_user.username).glob("*.txt")]
    mapping = {f"/note_{i+1}": note for i,note in enumerate(notes)}

    note = update.effective_message.text

    if note not in mapping:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="Invalid note ID."
        )
        return

    _select_note(update.effective_user.username, mapping[note])

    await context.bot.send_message(
            chat_id=update.effective_chat.id, text=f"""Selected note: **{mapping[note]}**

Send a voice message to append to this note, or use the following commands:

/msg - Print note as Telegram message.
/txt - Download note as TXT file.
/delete - Delete this note (undoable!)
/done - Finish with this note.
""", parse_mode="markdown"
        )

async def list_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    notes = [path.name for path in _get_data(update.effective_user.username).glob("*.txt")]
    msg = "\n".join(f"/note_{i+1} - {note}" for i, note in enumerate(notes))

    if not msg:
        msg = "You don't have any notes yet. Send an audio message to create a new note."

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=msg
    )


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=help_text, parse_mode="markdown"
    )


async def reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != admin:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Nice try 🙄",
        )
        return

    user, credits = context.args
    _update_credits(user, int(credits))
    data = _get_user_data(user)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"Done. User {user} now has {data['credits']} credits.",
    )


async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.username != admin:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Nice try 🙄",
        )
        return

    users = []

    for user in data_folder.iterdir():
        try:
            credits = _get_user_data(user.name)['credits']
            notes = len(list(user.glob("*.txt")))
            users.append(f"{user.name} - 📝 {notes} 🪙 {credits}")
        except Exception as e:
            print(e)
            pass

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="\n".join(users)
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

    status_handler = CommandHandler("status", status)
    application.add_handler(status_handler)

    reload_handler = CommandHandler("reload", reload)
    application.add_handler(reload_handler)

    users_handler = CommandHandler("users", users)
    application.add_handler(users_handler)

    list_handler = CommandHandler("list", list_notes)
    application.add_handler(list_handler)

    msg_handler = CommandHandler("msg", msg)
    application.add_handler(msg_handler)

    txt_handler = CommandHandler("txt", txt)
    application.add_handler(txt_handler)

    done_handler = CommandHandler("done", done)
    application.add_handler(done_handler)

    delete_handler = CommandHandler("delete", delete)
    application.add_handler(delete_handler)

    help_handler = CommandHandler("help", help)
    application.add_handler(help_handler)

    audio_handler = MessageHandler(filters.VOICE, transcribe)
    application.add_handler(audio_handler)

    select_handler = MessageHandler(filters.COMMAND & filters.Regex(r"/note_\d+"), select)
    application.add_handler(select_handler)

    default_handler = MessageHandler(filters.TEXT, default)
    application.add_handler(default_handler)

    application.run_polling()
