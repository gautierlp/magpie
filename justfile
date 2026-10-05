# List the recipes
help:
    @just --list

# Run the test suite
test:
    .venv/bin/pytest -v
