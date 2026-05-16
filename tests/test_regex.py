from alembic_squawk.cli import SQUAWK_IGNORE_RE


def test_squawk_ignore_re():
    # Valid formats
    assert SQUAWK_IGNORE_RE.findall("# squawk-disable rule1") == [
        "squawk-disable rule1"
    ]
    assert SQUAWK_IGNORE_RE.findall("#squawk-disable rule2") == ["squawk-disable rule2"]
    assert SQUAWK_IGNORE_RE.findall("# -- squawk-ignore-file rule3") == [
        "squawk-ignore-file rule3"
    ]
    assert SQUAWK_IGNORE_RE.findall("#--squawk-enable rule4") == ["squawk-enable rule4"]
    assert SQUAWK_IGNORE_RE.findall("#   --   squawk-ignore rule5") == [
        "squawk-ignore rule5"
    ]

    # Invalid formats (should not match)
    assert SQUAWK_IGNORE_RE.findall("    # squawk-disable indented") == []
    assert SQUAWK_IGNORE_RE.findall("op.execute() # squawk-disable inline") == []
    assert SQUAWK_IGNORE_RE.findall("## squawk-disable double-hash") == []
    assert SQUAWK_IGNORE_RE.findall("# not squawk") == []
    assert SQUAWK_IGNORE_RE.findall("-- squawk-disable pure-sql") == []
