from httpx import AsyncClient
import asyncio
import time


class MonsterAPI:
    def __init__(self, api_key:str, pooling:float=1) -> None:
        self.api_key = api_key
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

        payload = self.build_payload(
            aspect_ratio= "square",
            negprompt= "deformed, bad anatomy, disfigured, poorly drawn face, out of focus",
            prompt=prompt,
            samples=1
        )

        return await client.post(url, json=payload, headers=self.headers)

    async def generate_text(self, prompt:str, model:str, client:AsyncClient, **kwargs):
        url = "https://api.monsterapi.ai/v1/generate/%s" % model
        payload = self.build_payload(prompt=prompt, **kwargs)
        return await client.post(url, json=payload, headers=self.headers)

    async def resolve(self, response, client:AsyncClient):
        try:
            callback = response.json()
            print(callback, flush=True)
        except:
            print(response, flush=True)
            raise

        if response.status_code != 200:
            raise ValueError(response.json()['message'])

        status_url = callback['status_url']

        pool = self.pooling

        while True:
            response = await client.get(status_url, headers=self.headers)
            response = response.json()
            print(response, flush=True)

            if response['status'] in ["IN_PROGRESS", "IN_QUEUE"]:
                await asyncio.sleep(pool)

                if pool < 32 * self.pooling:
                    pool *= 2

                continue

            if response['status'] == "FAILED":
                raise ValueError(response['result']['errorMessage'])

            return response
