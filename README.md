[![Release Notes](https://img.shields.io/github/release/iloveitaly/alembic-squawk)](https://github.com/iloveitaly/alembic-squawk/releases)
[![Downloads](https://static.pepy.tech/badge/alembic-squawk/month)](https://pepy.tech/project/alembic-squawk)
![GitHub CI Status](https://github.com/iloveitaly/alembic-squawk/actions/workflows/build_and_publish.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# Split Alembic Migrations into Per-Revision SQL Files

`alembic-squawk` runs Alembic in offline (SQL) mode and splits the output into one `.sql` file per migration revision. The primary use case is feeding those files to [Squawk](https://github.com/sbdchd/squawk) so lint failures point to a specific migration rather than a monolithic dump.

## Features

- Strips the outer `BEGIN`/`COMMIT` Alembic wraps the full dump in, so each file contains only its own migration SQL. Pass `--assume-in-transaction` to Squawk when linting.
- Maps each revision back to its source `.py` file to preserve the original filename in output.
- Reads squawk directives (e.g. `# squawk-ignore-file <rule>`, `# squawk-disable <rule>`) embedded as Python comments in migration files and prepends them as SQL directives in the generated output, so you can attach Squawk ignores without embedding raw SQL comments in Python source.
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

## Ignoring Squawk Errors

Squawk supports per-file ignore directives in SQL comments (e.g. `-- squawk-ignore-file ban-drop-column`). To attach these to a migration without embedding raw SQL comments in Python source, write the directive as a Python comment. The `--` prefix is optional.

**Note:** The comment must be at the very beginning of the line. Indented comments (e.g., inside a function) or inline comments (e.g., `op.execute("...") # squawk-disable`) are not supported and will be ignored.

For example, to hide a drop column error in your migration:

```python
"""add users table

Revision ID: 1a2b3c4d5e6f
Revises: 
Create Date: 2026-03-16 10:22:01.123456
"""

# squawk-ignore-file ban-drop-column
# -- squawk-disable require-concurrent-index-creation

from typing import Sequence, Union


from alembic import op
import sqlalchemy as sa

# ... migration code ...
```

When `alembic-squawk` generates the SQL for this revision, it will prepend those directives as standard SQL comments at the top of the file so Squawk honors them.

## Example

Here is an end-to-end example of how you might integrate `alembic-squawk` into a CI script or standard shell workflow to lint your database migrations:

```bash
# generate per-revision SQL files
uv run alembic-squawk --out-dir /tmp/alembic-squawk-lint

# the generated SQL is not wrapped in a transaction, but the entire migration will be.
# note: we use --assume-in-transaction so squawk knows to lint appropriately.
squawk --assume-in-transaction --pg-version=15 /tmp/alembic-squawk-lint/*.sql
```

If you are looking for examples of how to set up Alembic, SQLModel, and SQLAlchemy, check out [iloveitaly/activemodel](https://github.com/iloveitaly/activemodel). Additionally, [iloveitaly/python-starter-template](https://github.com/iloveitaly/python-starter-template) is a full Python app with a working integration of `alembic-squawk`.

## [MIT License](LICENSE.md)

*This project was created from [iloveitaly/python-package-template](https://github.com/iloveitaly/python-package-template)*
