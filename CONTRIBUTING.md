# Contributing

Use English for code, documentation and issues. Keep changes small and tested.
Run `python -m pytest` and `ruff check scripts proxy tests` in an isolated
environment. Build both images and run complete vulnerability scans. Do not
upload account exports or credentials to reproduce a bug; use synthetic data.

Changes to authentication, secret handling, persistence or deployment require
explicit review. Keep Actions pinned to immutable commit SHAs. Do not reduce
scanner coverage to make CI pass. Never run deployment from an untrusted PR.
Contributions are under the repository license; retain upstream attribution.