from httpx import AsyncClient
import asyncio
import time


TEXT_MODELS = [
    "codellama-13b-instruct",
    "codellama-34b-instruct",
    "falcon-40-instruct",
    "falcon-7b-instruct",
    "flan-t5-instruct",
    "llama2-7b-chat",
    "mpt-30b-instruct",
    "mpt-7b-instruct",
    "open-llama-instruct",
    "zephyr-7b-beta",
]


class MonsterAPI:
    def __init__(self, api_key:str, pooling:float=1, verbose:bool=True) -> None:
        self.api_key = api_key
        self.verbose = verbose
        self.headers = {
            "accept": "application/json",
            "authorization": f"Bearer {self.api_key}",
            "content-type": "application/json",
        }
        self.pooling = pooling

    def build_payload(self, format="json", **kwargs):
        if not kwargs:
            return None

        data = { str(k): v for k,v in kwargs.items() }

        if format == "json":
            return data
        elif format == "form":
            return "\r\n-----011000010111000001101001\r\n".join(f"Content-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}" for k,v in kwargs.items())

        raise ValueError("format %r is not valid" % format)

    async def upload(self, fp, name:str, client:AsyncClient):
        url = "https://api.monsterapi.ai/v1/upload?filename=%s" % name
        response = await client.get(url, headers=self.headers)
        result = response.json()

        upload_url = result['upload_url']
        donwload_url = result['download_url']

        await client.put(upload_url, data=fp.read())
        return donwload_url

    async def transcribe(self, fp, client: AsyncClient, fname:str="voice.mp3", **kwargs):
        url = "https://api.monsterapi.ai/v1/generate/whisper"

        filename = await self.upload(fp, fname, client)

        return await client.post(url, headers=self.headers, json=self.build_payload(file=filename, **kwargs))

    async def generate_image(self, client:AsyncClient, prompt:str):
        url = "https://api.monsterapi.ai/v1/generate/sdxl-base"

        aspect = "square"

        if '-h' in prompt:
            aspect = "portrait"
        elif "-w" in prompt:
            aspect = "landscape"

        payload = self.build_payload(
            aspect_ratio= aspect,
            negprompt= "deformed, bad anatomy, disfigured, poorly drawn face, out of focus",
            prompt=prompt,
            samples=1
        )

        return await client.post(url, json=payload, headers=self.headers)

    async def generate_text(self, prompt:str, model:str, client:AsyncClient, **kwargs):
        if model not in TEXT_MODELS:
            models = [m for m in TEXT_MODELS if m.startswith(model)]

            if not models:
                raise ValueError(f"Unknown model {model}")

            model = models[0]

        url = "https://api.monsterapi.ai/v1/generate/%s" % model
        payload = self.build_payload(prompt=prompt, **kwargs)
        return await client.post(url, json=payload, headers=self.headers)

    async def resolve(self, response, client:AsyncClient):
        try:
            callback = response.json()
            if self.verbose:
                print(callback, flush=True)
        except:
            if self.verbose:
                print(response, flush=True)
            raise

        if response.status_code != 200:
            raise ValueError(response.json()['message'])

        status_url = callback['status_url']

        pool = self.pooling

        while True:
            response = await client.get(status_url, headers=self.headers)
            response = response.json()

            if self.verbose:
                print(response, flush=True)

            if response['status'] in ["IN_PROGRESS", "IN_QUEUE"]:
                await asyncio.sleep(pool)

                if pool < 32 * self.pooling:
                    pool *= 2

                continue

            if response['status'] == "FAILED":
                raise ValueError(response['result']['errorMessage'])

            return response
