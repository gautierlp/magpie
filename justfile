# List the recipes
help:
    @just --list

# Run the test suite
test:
    .venv/bin/pytest -v

# Copy the tested modules into the skill dir and symlink the skill globally
install:
    cp src/*.py skills/magpie/
    mkdir -p ~/.claude/skills
    ln -sfn "$(pwd)/skills/magpie" ~/.claude/skills/magpie
    @echo "Installed. Run /magpie in any Claude Code session."
