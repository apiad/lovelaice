# Lovelaice: An AI-powered assistant for your terminal and editor

![PyPI - Version](https://img.shields.io/pypi/v/lovelaice)
![GitHub License](https://img.shields.io/github/license/apiad/lovelaice)
![PyPI - Downloads](https://img.shields.io/pypi/dm/lovelaice)
![GitHub commit activity](https://img.shields.io/github/commit-activity/m/apiad/lovelaice)

Lovelaice is an LLM-powered bot that sits in your terminal.
It has access to your files and it can run bash commands for you.
It can also access the Internet and search for answers to general
questions, as well as technical ones.

## Installation

Install with pip:

    pip install lovelaice

## Usage

Before using Lovelaice, you will need an API key for OpenAI and a model:

    export LOVELAICE_API_KEY="..."
    export LOVELAICE_MODEL="..."

> You can also define a custom base URL
> (if you are using an alternative, OpenAI-compatible
> provider such as <fireworks.ai> or <mistral.ai>, or a local LLM server
> such as LMStudio or vLLM) with `LOVELAICE_BASE_URL`.
>
> You can also pass `--model`, `--api-key`, and `--base-url` when calling
> `lovelaice` if you want to define these in a per-call basis.

You can use `lovelaice` from the command line to ask anything.
Lovelaice understands many different types of requests, and will
employ different tools according to the question.

You can also use Lovelaice in interactive mode just by typing `lovelaice` without a query.
It will launch a conversation loop that you can close at any time with Ctrl+D.

### Basic completion

You can use `lovelaice` a basic completion model, passing `--complete` or `-c` for short.

    $ lovelaice -c Once upon a time, in a small village

    Once upon a time, in a small village nestled in the rolling hills of Provence, there was a tiny, exquisite perfume shop. The sign above the door read "Maison de Rêve" – House of Dreams. The shop was owned by a kind-hearted and talented perfumer named Colette, who spent her days crafting enchanting fragrances that transported those who wore them to a world of beauty and wonder.

    [...]

### Chat

You can ask a casual question about virtually anything:

    $ lovelaice what is the meaning of life

    The meaning of life is a philosophical and metaphysical question
    related to the significance of living or existence in general.
    Many different people, cultures, and religions have different
    beliefs about the purpose and meaning of life.

    [...]

### Bash

You can also ask `lovelaice` to do something in your terminal:

    $ lovelaice how much free space do i have
    :: Using Bash

    Running the following code:
    $ df -h | grep '/$' | awk '{ print $4 }'
    [y]es / [N]o y

    5,5G

    You have approximately 5.5 Gigabytes of free space left on your filesystem.

### Codegen

You can ask a general question about programming:

    $ lovelaice how to make an async iterator in python
    :: Using Codegen

    In Python, you can create an asynchronous iterator using the `async for` statement and the `async def` syntax. Asynchronous iterators are useful when you want to iterate over a sequence of asynchronous tasks, such as fetching data from a web service.

    Here's a general explanation of how to create an asynchronous iterator in Python:

    1. Define an asynchronous generator function using the `async def` syntax.
    2. Inside the function, use the `async for` statement to iterate over the asynchronous tasks.
    3. Use the `yield` keyword to return each item from the generator function.

    Here's an example of an asynchronous iterator that generates a sequence of integers:

    ```python
    async def async_integer_generator():
        i = 0
        while True:
            yield i
            i += 1
            await asyncio.sleep(0.1)
    ```
    [...]

    Overall, creating an asynchronous iterator in Python is a powerful way to iterate over a sequence of asynchronous tasks. By using the `async def` syntax, the `async for` statement, and the `yield` keyword, you can create an efficient and flexible iterator that can handle a wide range of use cases.

### Interpreter

And if you ask it something math-related it can generate and run Python for you:

    $ lovelaice throw three d20 dices and return the middle value
    :: Using Interpreter

    Will run the following code:

    def solve():
        values = [random.randint(1, 20) for _ in range(3)]
        values.sort()
        return values[1]

    result = solve()

    [y]es / [N]o y

    Result: 14

> **NOTE**: Lovelaice will *always* require you to explicitly agree to run any code.
Make sure that you understand what the code will do, otherwise there is no guarantee
your computer won't suddenly grow a hand and slap you in the face, like, literally.

## Features

So far Lovelaice has both general-purpose chat capabilites, and access to bash.
Here is a list of things you can try:

- Chat with Lovelaice about casual stuff
- Ask Lovelaice questions about your system, distribution, free space, etc.
- Order Lovelaice to create folders, install packages, update apps, etc.
- Order Lovelaice to set settings, turn off the wifi, restart the computer, etc.
- Order Lovelaice to stage, commit, push, show diffs, etc.
- Ask Lovelaice to solve some math equation, generate random numbers, etc.

In general, you can attempt to ask Lovelaice to do just about anything
that requires bash, and it will try its best. Your imagination is the only limit.

Here are some features under active development:

- Generate and run Python code.
- Search in Google, crawl webpages, and answer questions using that content.
- Read files and answer questions about their content.
- Create and modify notes, emails, calendar entries, etc.
- VSCode extension (!)

## Contributing

Code is MIT. Just fork, clone, edit, and open a PR.
All suggestions, bug reports, and contributions are welcome.

## FAQ

**What models do you use?**

Currently, all OpenAI-compatible APIs are supported, which
should cover most use cases, including major commercial LLM providers
as well as local serves.

If you want to use a custom API that is not OpenAI-compatible,
you can easily setup a proxy with [LiteLLM](https://litellm.ai).

I do not have specific plans to add any other API, because maintaining
different APIs could become hell,
but you are free to submit a PR for your favorite API and
it might get included.

**Is this safe?**

Lovelaice will never run code without your explicit consent.
That being said, LLMs are known for making subtle mistakes, so never
trust that the code does what Lovelaice says it do. Always read
the code and make sure you understand what it does.

When in doubt, adopt the same stance as if you were copy/pasting code from
a random blog somehwere in the web (because that is exactly what you're doing).
