all: lint test

export DOCKER_BUILDKIT=1

lint:
	@flake8 $$(find pyca tests -name '*.py') .github/selenium-tests
	@bandit -s B404,B602,B603 -r pyca
	@npm run eslint

test:
	@npm run build
	@coverage run --source=pyca --omit='*.html' -m unittest discover -s tests

build:
	@npm ci
	@npm run build

pypi: clean build
	@python setup.py sdist
	@printf "\nUpload to PyPI with \"twine upload dist/$$(python setup.py --fullname).tar.gz\"\n"

docker:
	@docker build -t quay.io/opencast/pyca .

clean:
	@python setup.py clean --all
	@rm -rf node_modules pyca/ui/static

PHONY: all lint test build pypi docker clean
