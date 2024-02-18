import os
import time
import dotenv
import argparse
from mistralai.client import MistralClient
from .core import query


dotenv.load_dotenv()

parser = argparse.ArgumentParser("lovelaice")
parser.add_argument("-f", "--file", action="store", help="Add a file to the context")
parser.add_argument("--model", action="store", help="Select model", default="mistral-small")
parser.add_argument("query", nargs="+")


if __name__ == "__main__":
    args = parser.parse_args()
    client = MistralClient(api_key=os.getenv("MISTRAL_API_KEY"))

    prompt = " ".join(args.query)

    for response in query(prompt, client, args.model):
        print(response, end="", flush=True)

    print()
