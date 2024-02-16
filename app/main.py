import flet as ft
import aiofiles
import pathlib
import dotenv
import os
import httpx

dotenv.load_dotenv()

from lovelaice.connectors import MonsterAPI

upload_dir = pathlib.Path(__file__).parent / "uploads"
api = MonsterAPI(api_key=os.getenv("MONSTER_API"))


async def main(page: ft.Page):
    page.title = "Lovelaice"

    async def pick_files(e: ft.FilePickerResultEvent):
        if e.files is None:
            return

        upload_list = []

        for file in e.files:
            dir = await page.get_upload_url_async(f"raw/{file.name}", 600)
            upload_list.append(ft.FilePickerUploadFile(file.name, dir))

        await picker.upload_async(upload_list)

    async def picker_upload(e: ft.FilePickerUploadEvent):
        if e.progress < 1:
            return

        async with aiofiles.open(upload_dir / "raw" / e.file_name) as fp:
            if e.file_name.endswith(".txt") or e.file_name.endswith(".md"):
                text = await fp.read()
            else:
                async with httpx.AsyncClient() as client:
                    response = await api.transcribe(fp, client)
                    print(response)
                    result = await api.resolve(response, client)
                    print(result)
                    text = result["result"]["text"]

        current_text = current_note.current.value or ""

        if current_text:
            current_text = current_text.strip() + "\n\n"

        current_text += text

        current_note.current.value = current_text

        await current_note.current.update_async()

    picker = ft.FilePicker(on_result=pick_files, on_upload=picker_upload)
    page.overlay.append(picker)

    async def main_action_click(e):
        page.snack_bar = ft.SnackBar(
            content=ft.Text("This functionality is not implemented."), open=True
        )
        await page.update_async()

    async def upload_text(e):
        await picker.pick_files_async(
            "Select a text file to turn it into a new note",
            file_type=ft.FilePickerFileType.CUSTOM,
            allowed_extensions=["txt", "md"],
            allow_multiple=False,
        )

    async def upload_audio(e):
        await picker.pick_files_async(
            "Select an audio file to turn it into a new note",
            file_type=ft.FilePickerFileType.AUDIO,
            allow_multiple=False,
        )

    page.floating_action_button = ft.FloatingActionButton(
        width=75,
        height=75,
        content=ft.Icon("mic", size=40),
        shape=ft.StadiumBorder(),
        on_click=main_action_click,
    )
    page.floating_action_button_location = ft.FloatingActionButtonLocation.END_FLOAT

    current_note = ft.Ref[ft.Markdown]()
    all_notes = ft.Ref[ft.ListView]()

    await page.add_async(
        ft.SafeArea(
            ft.Column(
                [
                    ft.Text("Lovelaice", size=32, text_align=ft.TextAlign.CENTER),
                    ft.Text(
                        "Upload an audio or text to make a new note, or browse your existing notes.",
                        size=18,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    ft.Tabs(
                        tabs=[
                            ft.Tab(
                                "Current",
                                icon="sticky_note_2",
                                content=ft.Container(
                                    ft.Column(
                                        [
                                            ft.Row(
                                                [
                                                    ft.FilledButton(
                                                        icon="star",
                                                        text="New",
                                                    ),
                                                    ft.PopupMenuButton(
                                                        content=ft.Container(
                                                            ft.Row(
                                                                [
                                                                    ft.Icon("upload"),
                                                                    ft.Text("Upload"),
                                                                ]
                                                            ),
                                                            border=ft.border.all(ft.BorderSide(1, "black")),
                                                            border_radius=10,
                                                            padding=2,
                                                        ),
                                                        items=[
                                                            ft.PopupMenuItem(
                                                                icon="insert_drive_file",
                                                                text="Upload text file",
                                                                on_click=upload_text,
                                                            ),
                                                            ft.PopupMenuItem(
                                                                icon="audio_file",
                                                                text="Upload audio",
                                                                on_click=upload_audio,
                                                            ),
                                                        ],
                                                    ),
                                                ]
                                            ),
                                            ft.Column(
                                                [
                                                    ft.Markdown(
                                                        ref=current_note,
                                                        extension_set=ft.MarkdownExtensionSet.GITHUB_FLAVORED,
                                                    ),
                                                ],
                                            ),
                                        ],
                                        scroll=ft.ScrollMode.AUTO,
                                    ),
                                    padding=10,
                                ),
                            ),
                            ft.Tab(
                                "Archive",
                                icon="all_inbox",
                                content=ft.Container(
                                    ft.Column([ft.ListView(ref=all_notes)]),
                                    padding=10,
                                ),
                            ),
                            ft.Tab(
                                "Settings",
                                icon="settings",
                            ),
                        ],
                        scrollable=False,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
        )
    )


ft.app(target=main, view=ft.WEB_BROWSER, upload_dir=upload_dir)
