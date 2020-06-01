all: lint test

lint:
	@flake8 $$(find pyca tests -name '*.py')

test:
	@npm run build
	@coverage run --source=pyca --omit='*.html' -m unittest discover -s tests
