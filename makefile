.PHONY: publish
publish: clean build
	uv publish --token `dotenv -f .env get PYPI_TOKEN`

.PHONY: build
build:
	uv build
	uv pip install -e .

.PHONY: clean
clean:
	rm -rf dist
	rm -rf lovelaice.egg-info
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -rf {} +
