all: lint test

lint:
	@flake8 $$(find . -name '*.py')

test:
	@coverage run --source=pyca --omit='*.html' -m unittest discover -s tests
