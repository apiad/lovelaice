# Lovelaice: An AI-powered assistant for your terminal and editor

Lovelaice is an LLM-powered bot that sits in your terminal.
It has access to your files and it can run bash commands for you.
It can also access the Internet and search for answers to general
questions, as well as technical ones.

## Installation

Install with pip:

    pip install lovelaice

## Ussage

Before using Lovelaice, you will need an API key for [Mistral](https://mistral.ai).

    export MISTRAL_API_KEY="..."

You can use `lovelaice` from the command line to ask something causal like:

    $ lovelaice what is the meaning of life

    The meaning of life is a philosophical and metaphysical question related to the significance of living or existence in general. Many different people, cultures, and religions have different beliefs about the purpose and meaning of life.

    [...]

You can also ask `lovelaice` to do something in your terminal:

    $ lovelaice how much free space do i have
    :: Using Bash

    Running the following code:
    $ df -h | grep '/$' | awk '{ print $4 }'
    [y]es / [N]o y

    5,5G

    You have approximately 5.5 Gigabytes of free space left on your filesystem.

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

In general, you can attempt to ask Lovelaice to do just about anything
that requires bash, and it will try its best. Your imagination is the only limit.

Here are some features under active development:

- Generate and run Python code.
- Search in Google, crawl webpages, and answer questions using that content.
- Read files and answer questions about their content.
- Create and modify notes, emails, calendar entries, etc.

## Contributing

Code is MIT. Just fork, clone, edit, and open a PR.

## FAQ

**What models do you use?**

Currently, only [Mistral](https://mistral.ai) models are integrated,
but you are welcome to submit PRs
to add other LLM providers, such as OpenAI.

**Is this safe?**

Lovelaice will never run code without your explicit consent.
That being said, LLMs are known for making subtle mistakes, so never
trust that the code does what Lovelaice says it do. Always read
the code and make sure you understand what it does.

When in doubt, adopt the same stance as if you were copy/pasting code from
a random blog somehwere in the web (because that is exactly what you're doing).
