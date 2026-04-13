"""Tests for main.py CLI."""
from click.testing import CliRunner

import sys

sys.path.insert(0, "src")


class TestClickCore:
    """Test click core functionality."""

    def test_click_group_decorator(self):
        """Test @click.group works."""
        import click

        @click.group()
        def cli():
            pass

        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0

    def test_click_command(self):
        """Test @click.command works."""
        import click

        @click.command()
        def cmd():
            click.echo("test")

        runner = CliRunner()
        result = runner.invoke(cmd)
        assert "test" in result.output

    def test_click_option(self):
        """Test @click.option works."""
        import click

        @click.command()
        @click.option("--name", default="world")
        def cmd(name):
            click.echo(f"hello {name}")

        runner = CliRunner()
        result = runner.invoke(cmd, ["--name", "test"])
        assert "hello test" in result.output

    def test_click_argument(self):
        """Test @click.argument works."""
        import click

        @click.command()
        @click.argument("name")
        def cmd(name):
            click.echo(f"name: {name}")

        runner = CliRunner()
        result = runner.invoke(cmd, ["test"])
        assert "name: test" in result.output

    def test_click_choice(self):
        """Test @click.Choice works."""
        import click

        @click.command()
        @click.option("--fruit", type=click.Choice(["apple", "banana"]))
        def cmd(fruit):
            click.echo(f"fruit: {fruit}")

        runner = CliRunner()
        result = runner.invoke(cmd, ["--fruit", "apple"])
        assert result.exit_code == 0

    def test_click_flag(self):
        """Test @click.option with is_flag works."""
        import click

        @click.command()
        @click.option("--verbose", is_flag=True)
        def cmd(verbose):
            if verbose:
                click.echo("verbose mode")
            else:
                click.echo("quiet mode")

        runner = CliRunner()
        result = runner.invoke(cmd, ["--verbose"])
        assert "verbose mode" in result.output


class TestMainModule:
    """Test main module imports."""

    def test_main_can_be_imported(self):
        """Test main can be imported."""
        import src.main

        assert src.main is not None

    def test_get_settings_import(self):
        """Test get_settings can be imported."""
        from config_manager import get_settings

        assert get_settings is not None

    def test_get_scraper_import(self):
        """Test get_scraper can be imported."""
        from src.discovery.platforms import get_scraper

        assert get_scraper is not None

    def test_list_scrapers_import(self):
        """Test list_scrapers can be imported."""
        from src.discovery.platforms import list_scrapers

        assert list_scrapers is not None

    def test_setup_logging_import(self):
        """Test setup_logging can be imported."""
        from logging_config import setup_logging

        assert setup_logging is not None

    def test_init_database_import(self):
        """Test init_database can be imported."""
        from tracking.database import init_database

        assert init_database is not None
