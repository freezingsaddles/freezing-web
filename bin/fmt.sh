#!/usr/bin/env bash
echo "Running formatters"
echo "*** black ***"
black freezing
echo "*** isort ***"
isort freezing
echo "*** djlint ***"
djlint --reformat .
