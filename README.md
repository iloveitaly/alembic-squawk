[![Release Notes](https://img.shields.io/github/release/iloveitaly/alembic-squawk)](https://github.com/iloveitaly/alembic-squawk/releases)
[![Downloads](https://static.pepy.tech/badge/alembic-squawk/month)](https://pepy.tech/project/alembic-squawk)
![GitHub CI Status](https://github.com/iloveitaly/alembic-squawk/actions/workflows/build_and_publish.yml/badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

# alembic-squawk

`alembic-squawk` is a CLI tool that extracts raw SQL from Alembic in offline mode and splits the output into per-revision SQL files, one file per migration. 

This makes it easier to run SQL linters (e.g. [Squawk](https://github.com/sbdchd/squawk)) against individual migrations rather than the entire dump, so lint failures map directly to a specific revision file.

## Installation

```bash
uv add alembic-squawk
```

Or using pip:

```bash
pip install alembic-squawk
```

## Usage

The script requires a `--out-dir` argument specifying where to write the SQL files.
The directory is wiped and recreated on every run so stale artifacts from previous
runs are never mixed with current output.

```bash
alembic-squawk --out-dir /tmp/alembic_sql
```

### Options

- `--revisions`: The Alembic revision range to dump. Defaults to "base:head" (all migrations). Supports any valid Alembic range, e.g. "origin/main@HEAD:head".
- `--out-dir`: (Required) Directory to write SQL files into. Wiped and recreated on each run.
- `--created-after`: Filter to only write migrations created on or after a given date (YYYY-MM-DD). Useful for narrowing output to recently added migrations.
- `--lint-preamble`: Output the SQL preamble emitted by Alembic before the first revision marker. It is skipped by default.
- `--verbose`: Prints the raw Alembic command being run and any stderr output.

## Output Format

Each migration is written as a single `.sql` file named after the migration file (e.g., `2026_03_16_d4b9da2f705c_add_users.sql`).

## Squawk Ignore Directives

Squawk supports per-file ignore directives in SQL comments:

```sql
-- squawk-ignore-file ban-drop-column
```

To attach these to a migration without embedding raw SQL comments in Python source, write the directive as a Python comment with a `--` prefix:

```python
# -- squawk-ignore-file ban-drop-column
```

The script scans each migration's source file for these comments and prepends the corresponding SQL directives to the generated `.sql` file so Squawk honours them.

---

*This project was created from [iloveitaly/python-package-template](https://github.com/iloveitaly/python-package-template)*
