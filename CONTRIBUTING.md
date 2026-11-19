# Contributing

Thanks for looking at patchproof. Issues and pull requests are welcome.

## Before you start

- For a starter issue, claim it with a comment first, so two people do not build the same thing.
- Keep each change small and focused on one issue.

## Running the tests

```console
python3 run_tests.py
```

The full suite (17 tests, stdlib `unittest`) must pass before a pull request is reviewed. The ground-truth suite's border-recovery numbers (28 of 28 sides exact) must not go backwards. If your change alters the CLI or its output, update the README in the same pull request — and SKILL.md too, if install, commands, flags, exit codes or output wording changed.

## Pull requests

- Say what you changed and how you tested it.
- A detection change should say what it does to the UNCERTAIN pile: a panel that cannot be proved must stay UNCERTAIN, never gain made-up borders.
