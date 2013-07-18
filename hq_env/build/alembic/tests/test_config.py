from alembic import config
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic import util
from alembic.script import ScriptDirectory
from tests import eq_, capture_db, assert_raises_message

def test_config_no_file_main_option():
    cfg = config.Config()
    cfg.set_main_option("url", "postgresql://foo/bar")

    eq_(cfg.get_main_option("url"), "postgresql://foo/bar")


def test_config_no_file_section_option():
    cfg = config.Config()
    cfg.set_section_option("foo", "url", "postgresql://foo/bar")

    eq_(cfg.get_section_option("foo", "url"), "postgresql://foo/bar")

    cfg.set_section_option("foo", "echo", "True")
    eq_(cfg.get_section_option("foo", "echo"), "True")


def test_standalone_op():
    eng, buf = capture_db()

    env = MigrationContext.configure(eng)
    op = Operations(env)

    op.alter_column("t", "c", nullable=True)
    eq_(buf, ['ALTER TABLE t ALTER COLUMN c DROP NOT NULL'])

def test_no_script_error():
    cfg = config.Config()
    assert_raises_message(
        util.CommandError,
        "No 'script_location' key found in configuration.",
        ScriptDirectory.from_config, cfg
    )
