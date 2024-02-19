import vscode as vs
import lovelaice


ext = vs.Extension(
    name="Lovelaice", metadata=vs.ExtensionMetadata(version="0.1.7", publisher="apiad")
)


@ext.event
async def on_activate():
    vs.log("Lovelaice is online!")


@ext.command("Lovelaice", keybind="Ctrl+Shift+L")
async def lovelaice(ctx: vs.Context):
    query_box = vs.InputBox("Ask Lovelaice", place_holder="Your question...")
    await ctx.show(query_box)
    print(query_box.value)
    return await ctx.show(vs.InfoMessage(query_box.value))


ext.run()
