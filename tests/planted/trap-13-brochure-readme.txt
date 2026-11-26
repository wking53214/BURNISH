about: A promotional README with an install line and no admitted limits: style, not a false claim.
group: trap
suite: passed=12

=== file: README.md
# demo

A small planted repository.

## Install

A powerful, seamless tool that simply works.

Run pip install demo to get it.
=== file: pyproject.toml
[project]
name = "demo"
version = "0.1.0"
description = "A planted repository"
dependencies = []
=== file: demo/__init__.py
"""Demo: a small package used only to plant defects for Burnish to find."""
