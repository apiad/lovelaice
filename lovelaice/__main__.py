import asyncio
import httpx
import os
import fire
import dotenv

from lovelaice.connectors import MonsterAPI


dotenv.load_dotenv()


class CommandLine:
    def __init__(self, verbose:bool=False):
        self._api = MonsterAPI(os.getenv("MONSTER_API"), verbose=verbose)

    async def _prompt(self, model, prompt, **kwargs):
        async with httpx.AsyncClient() as client:
            response = await self._api.generate_text(prompt, model, client)
            result = await self._api.resolve(response, client)
            return result['result']['text']

    def prompt(self, model: str, prompt: str, max_length:int=1024, temp:float=0.7):
        return asyncio.run(self._prompt(model, prompt, max_length=max_length, temp=temp))


if __name__ == "__main__":
    fire.Fire(CommandLine, name="lovelaice")
