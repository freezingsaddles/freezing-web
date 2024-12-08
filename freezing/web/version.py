#!/usr/bin/env python3
# meta.py
#
# Metadata about the built version of this package
#
# The bin/freeze.sh script will replace this file with
# frozen values of commit, build_date, and branch.

import datetime
import logging
import subprocess


# Thanks https://stackoverflow.com/a/21901260/424301
def get_git_revision_short_hash() -> str:
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "--short", "HEAD"])
            .decode("ascii")
            .strip()
        )
    except Exception as e:
        logging.warning(f"Could not get revision from git {e}")
        return "unknown"


def get_git_branch() -> str:
    try:
        return (
            subprocess.check_output(["git", "symbolic-ref", "-q", "HEAD"])
            .decode("ascii")
            .strip()
            .replace("refs/heads/", "")
        )
    except Exception as e:
        logging.warning(f"Could not get branch from git {e}")
        return "unknown"


def freeze():
    return f"""
commit = "{get_git_revision_short_hash()}"
build_date = "{datetime.datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"
branch = "{get_git_branch()}"
"""


# Thanks https://stackoverflow.com/a/4546755/424301 for inspiration
commit = get_git_revision_short_hash()
build_date = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
branch = get_git_branch()
