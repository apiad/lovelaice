import logging
import urllib.parse
import json
import datetime
from httpx import AsyncClient

from pathlib import Path
from dotenv import load_dotenv
from io import BytesIO
import os
from telegram import Update, LabeledPrice
from telegram.ext import (
    filters,
    MessageHandler,
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
    PreCheckoutQueryHandler,
)

from lovelaice import MonsterAPI, Document

load_dotenv()
api = MonsterAPI(api_key=os.getenv("MONSTER_API"))
admin = os.getenv("ADMIN")

data_folder = Path(__file__).parent / "data" / "bot"

with open(Path(__file__).parent / "bot_help.md") as fp:
    help_text = fp.read()


def _get_tg_user(update: Update):
    return str(
        update.effective_user.username
        or update.effective_user.full_name
        or update.effective_user.id
    )


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
        chat_id=update.effective_chat.id,
        text="""
Send me an audio or voice message and I will transcribe it for you.

You can send more than one audio to make one larger transcription.

When done, you can download the transcription file in several formats.

Send /help for detailed instructions.""",
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = _get_user_data(_get_tg_user(update))

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"""
Credits: {data['credits']}

If you need more credits, send /buy.""",
    )


async def imagine(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = _get_user_data(_get_tg_user(update))

    if data["credits"] <= 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="I'm sorry but your out of credits. Send /status to check.",
        )
        return

    prompt = " ".join(context.args)

    if not prompt:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="You must pass some prompt. Ex: `/imagine an astronaut riding a horse`.",
        )
        return

    async with AsyncClient() as client:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="Submitting the job to MonsterAPI."
        )

        response = await api.generate_image(client, prompt)
        print(response, flush=True)

        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="Submitted. Waiting for response."
        )

        result = await api.resolve(response, client)
        print(result, flush=True)
        credits = int(result["credit_used"])
        _update_credits(_get_tg_user(update), -credits)

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Job finished. I'm forwarding the image.",
        )

        output = result["result"]["output"]

        for path in output:
            await context.bot.send_photo(update.effective_chat.id, path)

    credits = _get_user_data(_get_tg_user(update))["credits"]

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=f"Done. You have {credits} credits left."
    )


async def transcribe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = _get_user_data(_get_tg_user(update))

    if data["credits"] <= 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="I'm sorry but your out of credits. Send /status to check.",
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

    # attachement = update.effective_message.effective_attachment
    # filename = getattr(attachement, 'file_name', 'voice.ogg')
    # print("Voice file is", filename, flush=True)

    # if filename.endswith(".oga"):
    #     filename = "voice.ogg"

    async with AsyncClient() as client:
        response = await api.transcribe(content, client, "voice.ogg")

        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="Uploaded, waiting for reply."
        )

        result = await api.resolve(response, client)

    _update_credits(_get_tg_user(update), -int(result["credit_used"]))

    await _process_text(result["result"]["text"], update, context)


async def _process_text(text, update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = Document(text, parse=False)
    selected_note = _get_selected_note(_get_tg_user(update))
    data = _get_user_data(_get_tg_user(update))

    if selected_note:
        transcript_path = selected_note
    else:
        title = doc.sentences[0]
        title = title[:50]
        title = "".join([c for c in title if c.isalnum() or c == " "])
        now = datetime.datetime.now().isoformat()

        transcript_path = _get_data(_get_tg_user(update)) / f"{title} - {now}.txt"

    with transcript_path.open("a") as fp:
        for line in doc.sentences:
            fp.write(line)
            fp.write("\n")

        fp.write("\n")

    with transcript_path.open("r") as fp:
        full_text = fp.read()

    if len(full_text) < 512:
        summary = full_text
    else:
        summary = full_text[:256] + "\n[...]\n" + full_text[-256:]

    _select_note(_get_tg_user(update), transcript_path.name)

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"""Remaining credits: {data['credits']}

Summary:
_{summary.strip()}_

Send an voice or text message to continue this note, or use one of the following commands:

/rewrite - Rewrite and improve this note with AI.
/prompt - Pass this note as prompt to the AI.
/msg - Print note as Telegram message.
/txt - Download note as TXT file.
/delete - Delete this note. Undoable!
/publish - Publish note online to Telegraph.
/done - Finish with this note.
""",
        parse_mode="markdown",
    )


async def msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_note = _get_selected_note(_get_tg_user(update))

    if not selected_note:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="""
No note is currently selected.
Send an audio or voice message to begin a new one.""",
        )
        return

    with open(selected_note) as fp:
        text = fp.read()

        if len(text) > 2048:
            text = text[:2048] + "... [cut here].\n\nUse /txt to see the full note."

        await context.bot.send_message(chat_id=update.effective_chat.id, text=text)


async def txt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_note = _get_selected_note(_get_tg_user(update))

    if not selected_note:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="""
No note is currently selected.
Send an audio or voice message to begin a new one.""",
        )
        return

    with open(selected_note) as fp:
        await context.bot.send_document(
            chat_id=update.effective_chat.id, document=fp, filename="transcription.txt"
        )


async def publish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_note = _get_selected_note(_get_tg_user(update))

    if not selected_note:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="""
No note is currently selected.
Send an audio or voice message to begin a new one.""",
        )
        return

    data = _get_user_data(_get_tg_user(update))

    if "token" not in data:
        await context.bot.send_message("You must /login to Telegraph first.")
        return

    token = data["token"]

    with open(selected_note) as fp:
        text = fp.readlines()
        title = text[0].strip().replace(" ", "+")
        content = json.dumps(
            [dict(tag="p", children=[(t.strip()).replace(" ", "+")]) for t in text],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        print(content, flush=True)

    async with AsyncClient() as client:
        page = await client.get(
            f'https://api.telegra.ph/createPage?access_token={token}&title="{title}"&content={content}'
        )
        print(page, flush=True)
        url = page.json()["result"]["url"]

        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Note published to Telegraph.\n\n{url}",
        )


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_note = _get_selected_note(_get_tg_user(update))

    if not selected_note:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="""
No note is currently selected.
Send an audio or voice message to begin a new one.""",
        )
        return

    _select_note(_get_tg_user(update))

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Done. Send me an audio message to start a new note.",
    )


async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    selected_note = _get_selected_note(_get_tg_user(update))

    if not selected_note:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="""
No note is currently selected.
Send an audio or voice message to begin a new one.""",
        )
        return

    selected_note.unlink()
    _select_note(_get_tg_user(update))

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Note discarded. Send me an audio message to start a new note.",
    )


async def select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    notes = [path.name for path in _get_data(_get_tg_user(update)).glob("*.txt")]
    mapping = {f"/note_{i+1}": note for i, note in enumerate(notes)}

    note = update.effective_message.text

    if note not in mapping:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="Invalid note ID."
        )
        return

    _select_note(_get_tg_user(update), mapping[note])

    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"""Selected note: **{mapping[note]}**

Send a voice or text message to continue this note, or use one of the following commands:

/rewrite - Rewrite and improve this note with AI.
/prompt - Pass this note as prompt to the AI.
/msg - Print note as Telegram message.
/txt - Download note as TXT file.
/delete - Delete this note. Undoable!
/publish - Publish note online to Telegraph.
/done - Finish with this note.
""",
        parse_mode="markdown",
    )


async def list_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    notes = [path.name for path in _get_data(_get_tg_user(update)).glob("*.txt")]
    msg = "\n".join(f"/note_{i+1} - {note}" for i, note in enumerate(notes))

    if not msg:
        msg = (
            "You don't have any notes yet. Send an audio message to create a new note."
        )

    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, text=help_text, parse_mode="markdown"
    )


async def reload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if _get_tg_user(update) != admin:
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
    if _get_tg_user(update) != admin:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Nice try 🙄",
        )
        return

    users = []

    for user in data_folder.iterdir():
        try:
            credits = _get_user_data(user.name)["credits"]
            notes = len(list(user.glob("*.txt")))
            users.append(f"{user.name} - 📝 {notes} 🪙 {credits}")
        except Exception as e:
            print(e)
            pass

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="\n".join(users)
    )


async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = _get_tg_user(update)
    data = _get_user_data(user)

    async with AsyncClient() as client:
        if "token" not in data:
            response = await client.get(
                f"https://api.telegra.ph/createAccount?short_name=My+Lovelaice+Notes&author_name={update.effective_user.full_name}"
            )
            response = response.json()
            data["token"] = response["result"]["access_token"]
            _store_user_data(user, data)

        token = data["token"]
        response = await client.get(
            f'https://api.telegra.ph/getAccountInfo?access_token={token}&fields=["auth_url"]'
        )
        auth_url = response.json()["result"]["auth_url"]

    await context.bot.send_message(
        update.effective_chat.id,
        text=f"Click this link to login to your private notes Telegraph account:\n\n{auth_url}",
    )


PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN")

BUY_OPTIONS = [
    (100, 100),
    (500, 300),
    (1000, 500),
    (10000, 2000),
]


async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends an invoice with shipping-payment."""
    chat_id = update.message.chat_id

    for credits, price in BUY_OPTIONS:
        title = f"{credits} Credits"
        description = f"Add {credits} credits to your total quota."
        # select a payload just for you to recognize its the donation from your bot
        payload = f"lovelaice_credits:{credits}"
        # In order to get a provider_token see https://core.telegram.org/bots/payments#getting-a-token
        currency = "USD"
        # price in dollars
        prices = [LabeledPrice(f"{credits} Credits", price)]

        # optionally pass need_name=True, need_phone_number=True,
        # need_email=True, need_shipping_address=True, is_flexible=True
        await context.bot.send_invoice(
            chat_id, title, description, payload, PAYMENT_TOKEN, currency, prices
        )


# after (optional) shipping, it's the pre-checkout
async def precheckout_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Answers the PreQecheckoutQuery"""
    query = update.pre_checkout_query
    # check the payload, is this from your bot?
    if not query.invoice_payload.startswith("lovelaice_credits"):
        # answer False pre_checkout_query
        await query.answer(ok=False, error_message="Something went wrong...")
    else:
        await query.answer(ok=True)


async def successful_payment_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Confirms the successful payment."""
    # do something after successfully receiving payment?
    _, credits = update.effective_message.successful_payment.invoice_payload.split(":")
    credits = int(credits)
    user = _get_tg_user(update)
    _update_credits(user, credits)
    new_credits = _get_user_data(user)["credits"]

    await update.effective_message.reply_text(
        f"Done! You now have have {new_credits} credits."
    )


async def default(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.effective_message.text
    await _process_text(text, update, context)


REWRITE_PROMPT = """
Rewrite the following text to improve the grammar, punctuation and style.
Cut sentences when necessary to make them crisp and use active voice.
Respect the tone.
Do not add anything not explicitly said in the text.

## Original text

{0}
"""


async def rewrite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = _get_user_data(_get_tg_user(update))

    if data["credits"] <= 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="I'm sorry but your out of credits. Send /status to check.",
        )
        return

    selected_note = _get_selected_note(_get_tg_user(update))

    if not selected_note:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="""
No note is currently selected.
Send /list to select a note for rewriting.""",
        )
        return

    with selected_note.open("r") as fp:
        text = fp.read()

    chunks = [t.strip() for t in text.split("\n\n") if t.strip()]
    split_chunks = []

    # Split into 1024-ish chunks but respecting sentence boundaries

    for chunk in chunks:
        if len(chunk) <= 1024:
            split_chunks.append(chunk)
        else:
            sentences = chunk.split("\n")
            current = ""

            for sentence in sentences:
                current += sentence

                if len(current) >= 1024:
                    split_chunks.append(current)
                    current = ""

            if current:
                split_chunks.append(current)

    results = []
    cost = 0

    for i, chunk in enumerate(split_chunks):
        await update.effective_chat.send_message(
            f"Rewriting chunk {i+1}/{len(split_chunks)}..."
        )

        async with AsyncClient() as client:
            response = await api.generate_text(
                prompt=REWRITE_PROMPT.format(chunk),
                model="zephyr",
                client=client,
                max_length=len(chunk) * 2,
            )
            result = await api.resolve(response, client=client)

        credits = int(result["credit_used"])
        cost += credits
        results.append(result["result"]["text"])

    _update_credits(_get_tg_user(update), -cost)
    _select_note(_get_tg_user(update))
    await update.effective_chat.send_message(f"Creating new note with resulting text.")

    text = "\n\n".join(results)
    await _process_text(text, update, context)


async def prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = _get_user_data(_get_tg_user(update))

    if data["credits"] <= 0:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="I'm sorry but your out of credits. Send /status to check.",
        )
        return

    selected_note = _get_selected_note(_get_tg_user(update))

    if not selected_note:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="""
No note is currently selected.
Send /list to select a note.""",
        )
        return

    with selected_note.open("r") as fp:
        text = fp.read()

    await context.bot.send_message(
        chat_id=update.effective_chat.id, text="Sending prompt..."
    )

    async with AsyncClient() as client:
        response = await api.generate_text(
            prompt=text, model="zephyr", client=client, max_length=4096
        )
        await context.bot.send_message(
            chat_id=update.effective_chat.id, text="Waiting for response..."
        )
        result = await api.resolve(response, client=client)

    credits = int(result["credit_used"])
    result = result["result"]["text"]
    _update_credits(_get_tg_user(update), -credits)

    await _process_text(result, update, context)


def main():
    application = (
        ApplicationBuilder()
        .token(os.getenv("BOT_TOKEN"))
        .concurrent_updates(True)
        .build()
    )

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

    publish_handler = CommandHandler("publish", publish)
    application.add_handler(publish_handler)

    rewrite_handler = CommandHandler("rewrite", rewrite)
    application.add_handler(rewrite_handler)

    prompt_handler = CommandHandler("prompt", prompt)
    application.add_handler(prompt_handler)

    done_handler = CommandHandler("done", done)
    application.add_handler(done_handler)

    imagine_handler = CommandHandler("imagine", imagine)
    application.add_handler(imagine_handler)

    delete_handler = CommandHandler("delete", delete)
    application.add_handler(delete_handler)

    help_handler = CommandHandler("help", help)
    application.add_handler(help_handler)

    login_handler = CommandHandler("login", login)
    application.add_handler(login_handler)

    buy_handler = CommandHandler("buy", buy)
    application.add_handler(buy_handler)

    application.add_handler(PreCheckoutQueryHandler(precheckout_callback))

    application.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_callback)
    )

    audio_handler = MessageHandler(filters.VOICE, transcribe)
    application.add_handler(audio_handler)

    select_handler = MessageHandler(
        filters.COMMAND & filters.Regex(r"/note_\d+"), select
    )
    application.add_handler(select_handler)

    default_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, default)
    application.add_handler(default_handler)

    application.run_polling()


if __name__ == "__main__":
    main()
