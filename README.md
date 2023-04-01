# Lovelaice - An AI-powered writing assistant for VSCode

Lovelaice is a writing assistant for VSCode. It is implemented as a Python Language Server that works on Markdown files.
It contains commands and tools to generate, format, revise, and change prose, using the OpenAI API and several of its models.

Lovelaice aims to support features such as auto-completion, text formatting, and revision suggestions, all powered by OpenAI's models. It will also provide tools to generate summaries, headlines, and titles, and provide feedback on sentence structure.

In addition to its writing assistance capabilities, Lovelaice will also offer AI-assisted text analytics. This allows users to analyze their text for sentiment and key phrases, as well as generate summaries.

Overall, Lovelaice aims to be a powerful writing assistant for VSCode that offers a wide range of features to help users write better documents more quickly and accurately.

**NOTE**: You will need to have an OpenAI account and setup your token for this extension to work.

## Features

Here's a non-exhaustive list of features/commands that are implemented or planned.

- [x] Fix grammar and spelling
- [x] Arbitary text completion
- [ ] Change the tone/formality of text
- [ ] Detect and change the sentiment of text
- [ ] Generate headings and titles
- [ ] Summarize large chunks of text

## Usage

This project is in an alpha development stage, and as such it is not directly installable as an extension. To take it for a spin, you have to clone the project and setup a development environment.

### Install Server and Client Dependencies

This project uses Poetry and Node/NPM, so make sure to have those installed.

1. `poetry install`
2. `npm install`
3. `cd client/ && npm install`
4. Create `.env` and add your OpenAI token as `OPENAI_KEY`.

### Run the extension in debug mode

1. Open this directory in VS Code
2. Open debug view (`ctrl + shift + D`)
3. Select `Server + Client` and press `F5`
