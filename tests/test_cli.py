from pathlib import Path

from click.testing import CliRunner

from alembic_squawk.cli import SqlChunk, main, split_sql_dump, write_chunks


def test_sql_chunk_has_content():
    chunk = SqlChunk("test")
    assert not chunk.has_content
    chunk.lines.append("SELECT 1;")
    assert chunk.has_content


def test_sql_chunk_is_preamble():
    chunk = SqlChunk("_preamble")
    assert chunk.is_preamble
    chunk = SqlChunk("other")
    assert not chunk.is_preamble


def test_split_sql_dump():
    dump = """BEGIN;
-- Running upgrade abc -> def
ALTER TABLE foo ADD COLUMN bar VARCHAR;
COMMIT;"""
    chunks = split_sql_dump(dump, {})
    assert len(chunks) == 1
    assert chunks[0].name == "def"
    assert "ALTER TABLE foo ADD COLUMN bar VARCHAR;" in chunks[0].lines


def test_write_chunks(tmp_path):
    chunks = [
        SqlChunk("_preamble", lines=["SET search_path TO public;"]),
        SqlChunk("def456", lines=["ALTER TABLE foo ADD COLUMN bar VARCHAR;"]),
    ]
    files, skipped = write_chunks(chunks, tmp_path, skip_preamble=False)
    assert len(files) == 2
    assert skipped == 0
    assert (tmp_path / "000_preamble.sql").exists()
    assert (tmp_path / "def456.sql").exists()


def test_cli_help():
    runner = CliRunner()
    result = runner.invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "Extracts raw SQL from Alembic" in result.output


def test_cli_integration(tmp_path, monkeypatch):
    """
    Test the CLI end-to-end using the test migrations in tests/example_migration.
    """
    tests_dir = Path(__file__).parent / "example_migration"
    monkeypatch.chdir(tests_dir)

    runner = CliRunner()
    result = runner.invoke(main, ["--out-dir", str(tmp_path)])

    assert result.exit_code == 0, f"CLI failed: {result.output}"

    # 3 migrations + 1 preamble (if not skipped, but by default it is skipped)
    assert (tmp_path / "1_rev1.sql").exists()
    assert (tmp_path / "2_rev2.sql").exists()
    assert (tmp_path / "3_rev3.sql").exists()

    # Verify squawk ignores are properly translated to SQL comments
    rev1_sql = (tmp_path / "1_rev1.sql").read_text()
    assert "-- squawk-ignore-file ban-drop-column" in rev1_sql
    assert "CREATE TABLE users" in rev1_sql

    rev2_sql = (tmp_path / "2_rev2.sql").read_text()
    assert "-- squawk-disable require-concurrent-index-creation" in rev2_sql
    assert "-- squawk-ignore-file ban-add-column-default" in rev2_sql
    assert "ALTER TABLE users ADD COLUMN email VARCHAR(255)" in rev2_sql

    rev3_sql = (tmp_path / "3_rev3.sql").read_text()
    assert "squawk-ignore-file" not in rev3_sql
    assert "CREATE INDEX idx_users_email ON users (email)" in rev3_sql


def test_cli_created_after(tmp_path, monkeypatch):
    tests_dir = Path(__file__).parent / "example_migration"
    monkeypatch.chdir(tests_dir)

    runner = CliRunner()
    # 2026-03-02 should include rev2 and rev3, but skip rev1
    result = runner.invoke(
        main, ["--out-dir", str(tmp_path), "--created-after", "2026-03-02"]
    )

    assert result.exit_code == 0
    assert "skipped by --created-after filter" in result.output
    assert not (tmp_path / "1_rev1.sql").exists()
    assert (tmp_path / "2_rev2.sql").exists()
    assert (tmp_path / "3_rev3.sql").exists()


def test_cli_lint_preamble(tmp_path, monkeypatch):
    tests_dir = Path(__file__).parent / "example_migration"
    monkeypatch.chdir(tests_dir)

    runner = CliRunner()
    result = runner.invoke(main, ["--out-dir", str(tmp_path), "--lint-preamble"])

    assert result.exit_code == 0
    assert (tmp_path / "000_preamble.sql").exists()


def test_cli_revisions(tmp_path, monkeypatch):
    tests_dir = Path(__file__).parent / "example_migration"
    monkeypatch.chdir(tests_dir)

    runner = CliRunner()
    # Just run rev1 to rev2
    result = runner.invoke(
        main, ["--out-dir", str(tmp_path), "--revisions", "rev1:rev2"]
    )

    assert result.exit_code == 0
    # Should only generate rev2 (as it's applying the diff from rev1 to rev2)
    assert not (tmp_path / "1_rev1.sql").exists()
    assert (tmp_path / "2_rev2.sql").exists()
    assert not (tmp_path / "3_rev3.sql").exists()


def test_cli_verbose(tmp_path, monkeypatch):
    tests_dir = Path(__file__).parent / "example_migration"
    monkeypatch.chdir(tests_dir)

    runner = CliRunner()
    result = runner.invoke(main, ["--out-dir", str(tmp_path), "--verbose"])

    assert result.exit_code == 0
    assert "$ alembic upgrade base:head --sql" in result.output


def test_missing_dependencies(tmp_path, monkeypatch):
    # Remove alembic from PATH
    monkeypatch.delenv("PATH", raising=False)
    runner = CliRunner()
    result = runner.invoke(main, ["--out-dir", str(tmp_path)])

    assert result.exit_code != 0
    assert "Missing required executables in PATH" in result.output


def test_alembic_failure(tmp_path, monkeypatch):
    import subprocess

    # Mock subprocess.run to simulate an alembic failure
    def mock_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="Alembic encountered a mocked error.",
        )

    monkeypatch.setattr(subprocess, "run", mock_run)
    runner = CliRunner()
    result = runner.invoke(main, ["--out-dir", str(tmp_path), "--verbose"])

    assert result.exit_code != 0
    assert "Alembic failed with exit code 1" in result.output
    assert "Alembic encountered a mocked error." in result.output
