# Lovelaice - An AI-powered writing assistant for VSCode

Lovelaice is a writing assistant for VSCode. It is implemented as a Python Language Server that works on Markdown files.
It contains commands and tools to generate, format, revise, and change prose, using the OpenAI API and several of its models.

Lovelaice is a text editing platform that seeks to provide users with a range of features to enhance their writing. It utilizes OpenAI's models to provide auto-completion, text formatting, and revision suggestions. This means that users can take advantage of the models' predictive capabilities to save time and energy on mundane tasks. Additionally, Lovelaice will provide tools to generate summaries, headlines, and titles. These tools use AI to quickly generate content that is tailored to the user's needs. Finally, Lovelaice provides feedback on sentence structure to ensure that users can write in an effective and organized manner. This feedback is based on the models' understanding of grammar and syntax, ensuring accuracy and consistency. In short, Lovelaice provides a comprehensive suite of features that can help users write better and faster.

In addition to its writing assistance capabilities, Lovelaice will also offer AI-assisted text analytics. This allows users to gain insight into the sentiment, topics, and key phrases in the text they are writing. The AI-powered text analytics feature can also generate summaries of the text, helping the user to understand the key points of the text and quickly identify any areas that need further development or refinement. The text analytics feature can help users better understand their own work, as well as quickly and accurately understand the work of others when reading and reviewing documents.

Overall, Lovelaice aims to be a powerful writing assistant for VSCode that offers a wide range of features to help users write better documents more quickly and accurately.

> By the way, all of the above has been written in a large part using Lovelaice.

**NOTE**: You will need to have an OpenAI account and setup your token for this extension to work.

## Features

Here's a non-exhaustive list of features/commands that are implemented or planned.

- [x] Fix grammar and spelling
- [x] Arbitary text completion
- [x] Summarize large chunks of text
- [x] Expand fragments of text
- [x] Brainstorm ideas based on a fragment of text
- [ ] Change the tone/formality of text
- [ ] Detect and change the sentiment of text
- [ ] Generate headings and titles

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

This will open a new VSCode window with the extension activated.

### Use it

Now open a Markdown document and start writing. Select a chunk of text, and hit `Ctrl+.` to open the Code Action popup menu and select a magic command.

## Contribution

Code is MIT, so you know the drill. Fork, test, PR, rinse and repeat.
