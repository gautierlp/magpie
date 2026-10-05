# List the recipes
help:
    @just --list

# Run the test suite
test:
    .venv/bin/pytest -v

# Copy the tested modules into the skill dir and symlink the skill globally
install:
    cp src/*.py skills/daily/
    mkdir -p ~/.claude/skills
    ln -sfn "$(pwd)/skills/daily" ~/.claude/skills/daily
    @echo "Installed. Run /daily in any Claude Code session."
