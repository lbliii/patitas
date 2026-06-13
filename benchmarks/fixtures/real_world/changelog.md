# Changelog

All notable changes to this project are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/), and this project adheres to
semantic versioning.

## [2.4.0] - 2026-05-18

### Added

- New `--format json` flag on the `report` command for machine-readable output.
- Support for reading credentials from the system keyring on macOS and Linux.
- A `doctor` subcommand that checks your environment and prints actionable fixes.

### Changed

- The default cache directory now follows the XDG base-directory spec on Linux.
- Error messages for malformed config files now point at the exact line and column.

### Fixed

- Fixed a crash when a config file contained a BOM ([#412](https://example.com/412)).
- `report --since` no longer silently ignores time zones.

## [2.3.1] - 2026-04-02

### Fixed

- Restored compatibility with Python 3.11 after an accidental use of a 3.12-only
  standard-library function ([#398](https://example.com/398)).
- The progress bar no longer leaves stray characters on narrow terminals.

### Security

- Upgraded the bundled TLS roots to address an expired intermediate certificate.

## [2.3.0] - 2026-03-10

### Added

- Parallel uploads, controlled by `--jobs N` (defaults to the number of CPUs).
- A plugin hook, `pre_upload`, for last-minute payload rewriting.

### Deprecated

- The `--legacy-auth` flag is deprecated and will be removed in 3.0. Migrate to
  token-based auth; see the [migration notes](docs/migrating.md) for details.

### Removed

- Dropped support for the long-deprecated `.acmerc` ini format. Use `acme.toml`.

[2.4.0]: https://example.com/compare/2.3.1...2.4.0
[2.3.1]: https://example.com/compare/2.3.0...2.3.1
[2.3.0]: https://example.com/compare/2.2.0...2.3.0
