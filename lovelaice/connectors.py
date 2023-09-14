import requests
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

        data = { k: str(v) for k,v in kwargs.items() }

        if format == "json":
            return data
        elif format == "form":
            return "\r\n-----011000010111000001101001\r\n".join(f"Content-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}" for k,v in kwargs.items())

        raise ValueError("format %r is not valid" % format)

    def upload(self, fp, name):
        url = "https://api.monsterapi.ai/v1/upload?filename=%s" % name
        response = requests.get(url, headers=self.headers)
        result = response.json()

        upload_url = result['upload_url']
        donwload_url = result['download_url']

        requests.put(upload_url, data=fp.read())
        return donwload_url

    def transcribe(self, fp, **kwargs):
        url = "https://api.monsterapi.ai/v1/generate/whisper"

        filename = self.upload(fp, "voice.mp3")

        response = requests.post(url, headers=self.headers, json=self.build_payload(file=filename, **kwargs))
        return response

    def generate_text(self, prompt:str, model:str, **kwargs):
        url = "https://api.monsterapi.ai/v1/generate/%s" % model
        payload = self.build_payload(prompt=prompt, **kwargs)
        response = requests.post(url, json=payload, headers=self.headers)
        return response

    def resolve(self, response):
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
            response = requests.get(status_url, headers=self.headers).json()

            if response['status'] not in ["IN_PROGRESS", "IN_QUEUE"]:
                print(response, flush=True)
                return response

            time.sleep(pool)
            print(response, flush=True)
            print("Pooling...", flush=True)

            if pool < 32 * self.pooling:
                pool *= 2
