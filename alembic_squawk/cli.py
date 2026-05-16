"""
Alembic SQL Dumper

This script generates SQL from Alembic in offline mode and splits the output into
per-revision SQL files, one file per migration. This makes it easier to run SQL
linters (e.g. Squawk) against individual migrations rather than the entire dump,
so lint failures map directly to a specific revision file.

Usage
-----
The script requires a --out-dir argument specifying where to write the SQL files.
The directory is wiped and recreated on every run so stale artifacts from previous
runs are never mixed with current output.

Example:

    alembic-squawk --out-dir /tmp/alembic_sql

Options
-------
--revisions
    The Alembic revision range to dump. Defaults to "base:head" (all migrations).
    Supports any valid Alembic range, e.g. "origin/main@HEAD:head" to dump only
    migrations not yet on main.

--out-dir (required)
    Directory to write SQL files into. Wiped and recreated on each run.

--created-after
    Filter to only write migrations created on or after a given date (YYYY-MM-DD).
    Useful for narrowing output to recently added migrations.

--lint-preamble
    By default, the SQL preamble emitted by Alembic before the first revision
    marker is skipped. The preamble contains boilerplate SET statements and is
    not associated with any specific migration. Pass this flag to write it to a
    file named "000_preamble.sql" as well.

--verbose
    Prints the raw Alembic command being run and any stderr output.

Output format
-------------
Each migration is written as a single .sql file named after the migration file
(e.g. "2026_03_16_d4b9da2f705c_move_constants_to_distribution_model.sql").

The outer BEGIN/COMMIT that Alembic wraps the entire dump in is stripped before
splitting so the per-file output contains only the migration's own SQL. Files are
not re-wrapped in their own transaction — pass --assume-in-transaction to Squawk
so it treats each file as already inside a transaction (required for linting
statements that are only valid within a transaction, e.g. ALTER TYPE).

Offline mode and data migrations
---------------------------------
Alembic's --sql mode runs migrations against a MockConnection rather than a real
database. Any migration that performs data migrations (ORM queries, raw SQL
selects/updates) must guard those code paths using the is_offline_migration()
helper from migrations/utils.py, which checks op.get_context().as_sql. Only DDL
operations (CREATE TABLE, ALTER TABLE, DROP COLUMN, etc.) are emitted in offline
mode — data migration logic is silently skipped.

LOG_LEVEL is set to CRITICAL when invoking Alembic to suppress noisy application
log output that would otherwise contaminate the SQL stdout that this script parses.

Squawk ignore directives
------------------------
Squawk supports per-file ignore directives in SQL comments:

    -- squawk-ignore-file ban-drop-column

To attach these to a migration without embedding raw SQL comments in Python source,
write the directive as a Python comment with a -- prefix:

    # -- squawk-ignore-file ban-drop-column

The script scans each migration's source file for these comments and prepends the
corresponding SQL directives to the generated .sql file so Squawk honours them.
Note: directives written inside docstrings (without a leading #) are not detected.
"""

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

import click

# Matches the Alembic progress comment that appears at the start of each
# revision block in --sql output, e.g.:
#   -- Running upgrade abc123 -> def456
# Captures the destination revision ID (the "head" side of the arrow).
REVISION_RE = re.compile(r"^--\s+Running upgrade .*?->\s+([^\s]+)")

# Matches the revision ID assignment in a migration file, handling both plain
# and annotated forms:
#   revision = 'abc123'
#   revision: str = 'abc123'
REVISION_ID_RE = re.compile(
    r"^revision(?::\s*str)?\s*=\s*['\"]([^'\"]+)['\"]", re.MULTILINE
)

# Matches the "Create Date:" line written by Alembic into each migration file's
# header comment, e.g.:
#   # Create Date: 2026-03-16 10:22:01.123456
# Captures the date portion only (YYYY-MM-DD).
CREATE_DATE_RE = re.compile(r"^Create Date: (\d{4}-\d{2}-\d{2})", re.MULTILINE)

# Matches squawk directives embedded as Python comments in migration
# source files, e.g.:
#   # -- squawk-ignore-file ban-drop-column
#   # squawk-disable require-concurrent-index-creation
# These are extracted and re-emitted as plain SQL comments in the generated
# output so Squawk honours them when linting the split files.
SQUAWK_IGNORE_RE = re.compile(r"^#\s*(?:--\s*)?(squawk-.*)", re.MULTILINE)


@dataclass
class SqlChunk:
    name: str
    created_date: date | None = None
    squawk_ignores: list[str] = field(default_factory=list)
    lines: list[str] = field(default_factory=list)

    @property
    def has_content(self) -> bool:
        """Return True if this chunk contains any non-blank lines."""
        return any(line.strip() for line in self.lines)

    @property
    def is_preamble(self) -> bool:
        return self.name == "_preamble"


def check_dependencies() -> None:
    """Ensure required CLI tools are available in PATH."""
    missing = [tool for tool in ("alembic",) if not shutil.which(tool)]
    if missing:
        raise click.ClickException(
            "Missing required executables in PATH: " + ", ".join(missing)
        )


def generate_alembic_sql(revisions: str, verbose: bool = False) -> str:
    """Run Alembic in offline mode to generate raw SQL."""
    cmd = ["alembic", "upgrade", revisions, "--sql"]
    click.secho(f"Generating Alembic SQL dump for {revisions}...", fg="blue", bold=True)

    if verbose:
        click.echo(f"$ {' '.join(cmd)}")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, "LOG_LEVEL": "CRITICAL"},
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        message = f"Alembic failed with exit code {result.returncode}."
        if stderr:
            message += f"\n\n{stderr}"
        raise click.ClickException(message)

    if verbose and result.stderr.strip():
        click.secho("Alembic stderr:", fg="yellow", bold=True)
        click.echo(result.stderr)

    return result.stdout


def build_revision_map() -> dict[str, tuple[str, date | None, list[str]]]:
    versions_dir = Path("migrations/versions")
    mapping = {}
    if not versions_dir.exists():
        return mapping
    for py_file in versions_dir.glob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8")
            rev_match = REVISION_ID_RE.search(content)
            if rev_match:
                rev_id = rev_match.group(1)
                chunk_name = py_file.stem

                date_match = CREATE_DATE_RE.search(content)
                created_date = (
                    date.fromisoformat(date_match.group(1)) if date_match else None
                )

                squawk_ignores = SQUAWK_IGNORE_RE.findall(content)

                mapping[rev_id] = (chunk_name, created_date, squawk_ignores)
        except Exception:
            pass
    return mapping


def split_sql_dump(
    sql_dump: str, revision_map: dict[str, tuple[str, date | None, list[str]]]
) -> list[SqlChunk]:
    """
    Split a single Alembic SQL dump into ordered per-revision chunks.

    Any content before the first '-- Running upgrade ...' marker is placed into
    a special '_preamble' chunk.
    """
    lines = sql_dump.splitlines()

    # Remove the first BEGIN; to avoid unbalanced transactions when split
    for i, line in enumerate(lines):
        if line.strip() == "BEGIN;":
            lines.pop(i)
            break

    # Remove the last COMMIT;
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() == "COMMIT;":
            lines.pop(i)
            break

    chunks: list[SqlChunk] = [SqlChunk("_preamble")]
    current_chunk = chunks[0]

    for line in lines:
        match = REVISION_RE.search(line)
        if match:
            rev_id = match.group(1)
            if rev_id in revision_map:
                chunk_name, created_date, squawk_ignores = revision_map[rev_id]
            else:
                chunk_name, created_date, squawk_ignores = rev_id, None, []

            current_chunk = SqlChunk(
                name=chunk_name,
                created_date=created_date,
                squawk_ignores=squawk_ignores,
            )
            chunks.append(current_chunk)
        current_chunk.lines.append(line)

    return [chunk for chunk in chunks if chunk.has_content]


def write_chunks(
    chunks: list[SqlChunk],
    out_dir: Path,
    *,
    skip_preamble: bool = True,
    created_after: date | None = None,
) -> tuple[list[Path], int]:
    """Write SQL chunks to disk and return the created file paths."""
    writable = [c for c in chunks if not (skip_preamble and c.is_preamble)]
    if not writable:
        return ([], 0)

    written_files: list[Path] = []

    skipped = 0
    for chunk in writable:
        if created_after and chunk.created_date and chunk.created_date < created_after:
            skipped += 1
            continue

        if chunk.name == "_preamble":
            filename = "000_preamble.sql"
        else:
            filename = f"{chunk.name}.sql"

        file_path = out_dir / filename
        date_comment = (
            f"-- Created at: {chunk.created_date}\n" if chunk.created_date else ""
        )
        ignore_comments = "".join(f"-- {d}\n" for d in chunk.squawk_ignores)
        chunk_content = date_comment + ignore_comments + "\n".join(chunk.lines) + "\n"
        file_path.write_text(chunk_content, encoding="utf-8")
        written_files.append(file_path)

    return written_files, skipped


@click.command()
@click.option(
    "--revisions",
    default="base:head",
    envvar="ALEMBIC_SQUAWK_REVISIONS",
    show_envvar=True,
    help="Alembic revision range to dump (e.g. base:head, origin/main@HEAD:head).",
)
@click.option(
    "--out-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    required=True,
    help="Output directory for generated SQL files.",
)
@click.option(
    "--created-after",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Only output migrations created on or after this date (YYYY-MM-DD).",
)
@click.option(
    "--lint-preamble",
    is_flag=True,
    help="Also output the SQL preamble emitted before the first revision marker.",
)
@click.option(
    "--verbose",
    is_flag=True,
    help="Print executed commands and additional diagnostic output.",
)
def main(
    revisions: str,
    out_dir: Path,
    created_after: datetime | None,
    lint_preamble: bool,
    verbose: bool,
) -> None:
    """
    Extracts raw SQL from Alembic, splits it by revision, and saves each file individually.
    """
    click.secho("Starting Alembic SQL Dumper...\n", bold=True)

    check_dependencies()
    revision_map = build_revision_map()
    sql_dump = generate_alembic_sql(revisions, verbose=verbose)
    chunks = split_sql_dump(sql_dump, revision_map)

    if out_dir.exists():
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True)

    created_after_date = created_after.date() if created_after else None
    sql_files, skipped = write_chunks(
        chunks,
        out_dir,
        skip_preamble=not lint_preamble,
        created_after=created_after_date,
    )

    msg = f"Wrote {len(sql_files)} revision file(s) to {out_dir}/"
    if skipped:
        msg += f" ({skipped} skipped by --created-after filter)"
    click.secho(msg, fg="green")


if __name__ == "__main__":
    main()
