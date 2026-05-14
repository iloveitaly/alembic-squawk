[![Release Notes](https://img.shields.io/github/release/iloveitaly/alembic-squawk)](https://github.com/iloveitaly/alembic-squawk/releases)
[![Downloads](https://static.pepy.tech/badge/alembic-squawk/month)](https://pepy.tech/project/alembic-squawk)
![GitHub CI Status](https://github.com/iloveitaly/alembic-squawk/actions/workflows/build_and_publish.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# Split Alembic Migrations into Per-Revision SQL Files

`alembic-squawk` runs Alembic in offline (SQL) mode and splits the output into one `.sql` file per migration revision. The primary use case is feeding those files to [Squawk](https://github.com/sbdchd/squawk) so lint failures point to a specific migration rather than a monolithic dump.

## Features

- Strips the outer `BEGIN`/`COMMIT` Alembic wraps the full dump in, so each file contains only its own migration SQL. Pass `--assume-in-transaction` to Squawk when linting.
- Maps each revision back to its source `.py` file to preserve the original filename in output.
- Reads `# -- squawk-ignore-file <rule>` Python comments from migration files and prepends them as SQL directives in the generated output, so you can attach Squawk ignores without embedding raw SQL comments in Python source.
- Supports filtering by revision range or creation date to narrow linting to recently added migrations.

## Installation

```bash
uv add alembic-squawk
```

## Usage

Run from your project root (where `alembic.ini` lives):

```bash
alembic-squawk --out-dir /tmp/alembic_sql
```

The output directory is wiped and recreated on every run.

### Options

- `--out-dir` (required): Directory to write SQL files into.
- `--revisions`: Alembic revision range. Defaults to `base:head`. Accepts any valid range, e.g. `origin/main@HEAD:head` to dump only migrations not yet on main.
- `--created-after YYYY-MM-DD`: Skip migrations created before this date.
- `--lint-preamble`: Also write the Alembic preamble (boilerplate `SET` statements) to `000_preamble.sql`. Skipped by default.
- `--verbose`: Print the Alembic command and any stderr output.

Each file is named after its migration source file, e.g. `2026_03_16_d4b9da2f705c_add_users.sql`.

## Example

[iloveitaly/python-starter-template](https://github.com/iloveitaly/python-starter-template) is a full Python app with a working integration of `alembic-squawk`.

## [MIT License](LICENSE.md)

*This project was created from [iloveitaly/python-package-template](https://github.com/iloveitaly/python-package-template)*
