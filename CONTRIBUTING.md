# Contributing

Thanks for contributing to `paper-radar`.

## Scope

The project is intentionally small and pragmatic. Changes are most useful when they improve one of these areas:

- source reliability
- ranking quality
- report readability
- onboarding and reproducibility
- test coverage for existing behavior

Avoid large refactors without a concrete reliability or maintainability benefit.

## Development Setup

Recommended:

```bash
bash bootstrap.sh
source .venv/bin/activate
```

Manual setup:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
```

## Common Commands

```bash
make test
make dry-run
make run
make clean
```

## Before Opening a PR

Please make sure that:

- tests pass locally
- the README stays accurate after your change
- config changes are reflected in validation logic when needed
- output format changes are covered by tests
- unrelated generated files are not committed

## Coding Guidelines

- Prefer readable code over deep abstraction.
- Keep modules single-purpose.
- Handle external source failures gracefully.
- Keep logs concise and actionable.
- Add tests for behavior changes, especially around parsing, ranking, and rendering.

## Pull Request Notes

A good PR should include:

- what changed
- why it changed
- any user-visible behavior change
- how it was validated

If the PR changes ranking behavior, include a short before/after note with example papers when possible.
