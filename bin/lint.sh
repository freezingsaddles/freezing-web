#!/usr/bin/env bash
echo "Running linting checks"
echo "*** black ***"
black --check freezing
echo "*** isort ***"
isort --check freezing
echo "*** flake8 ***"
flake8 freezing
echo "*** mypy ***"
echo "*** djlint ***"
djlint --check freezing/web/templates
echo "*** pymarkdown ***"
pymarkdown scan .
