from pydantic import BaseModel, AnyUrl, Field
import yaml
import pathlib


class ModelConfig(BaseModel):
    base_url: str = Field(default="", description="The API base URL (in case you're not using OpenAI)")
    api_key: str = Field(default="", description="The API key to authenticate with the LLM provider")
    name: str = Field(default="", description="The concrete LLM model to use")


class LovelaiceConfig(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig, description="Configuration for the code model.")
    max_tokens: int = Field(2048, description="Max number of tokens to generate in a single prompt")
    min_words: int = Field(0, description="For completion only, min number of words to generate")

    @classmethod
    def load(cls, root_path: pathlib.Path = pathlib.Path(".")):
        root_path = root_path.absolute()

        if not root_path.is_dir():
            raise ValueError('The root path must a directory.')

        matches: list[pathlib.Path] = []

        while True:
            if (root_path / ".lovelaice.yml").exists():
                matches.append(root_path / ".lovelaice.yml")

            if root_path.parent != root_path:
                root_path = root_path.parent
            else:
                break

        config = {}

        while matches:
            path = matches.pop()

            with path.open() as fp:
                config.update(yaml.safe_load(fp))

        return LovelaiceConfig(**config)


    def save(self, root_path: pathlib.Path = pathlib.Path(".")):
        root_path = root_path.absolute()

        if not root_path.is_dir():
            raise ValueError('The root path must a directory.')

        with open(root_path / ".lovelaice.yml", "w") as fp:
            yaml.dump(self.model_dump(mode="json"), fp)
