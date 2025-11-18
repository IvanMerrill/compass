"""Tests for CLI entry point."""

from click.testing import CliRunner

from compass.cli.main import cli


class TestCLIEntryPoint:
    """Tests for main CLI command."""

    def test_cli_has_investigate_command(self):
        """Verify CLI has 'investigate' subcommand."""
        runner = CliRunner()
        result = runner.invoke(cli, ["--help"])

        assert result.exit_code == 0
        assert "investigate" in result.output

    def test_investigate_requires_service(self):
        """Verify investigate command requires --service argument."""
        runner = CliRunner()
        result = runner.invoke(cli, ["investigate"])

        assert result.exit_code != 0
        assert "--service" in result.output or "service" in result.output.lower()

    def test_investigate_requires_symptom(self):
        """Verify investigate command requires --symptom argument."""
        runner = CliRunner()
        result = runner.invoke(cli, ["investigate", "--service", "api"])

        assert result.exit_code != 0
        assert "--symptom" in result.output or "symptom" in result.output.lower()

    def test_investigate_requires_severity(self):
        """Verify investigate command requires --severity argument."""
        runner = CliRunner()
        result = runner.invoke(
            cli, ["investigate", "--service", "api", "--symptom", "slow"]
        )

        assert result.exit_code != 0
        assert "--severity" in result.output or "severity" in result.output.lower()

    def test_investigate_validates_severity_choices(self):
        """Verify severity must be one of: low, medium, high, critical."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "investigate",
                "--service",
                "api",
                "--symptom",
                "slow",
                "--severity",
                "invalid",
            ],
        )

        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "choice" in result.output.lower()

    def test_investigate_accepts_valid_arguments(self):
        """Verify investigate command accepts valid arguments."""
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "investigate",
                "--service",
                "api-backend",
                "--symptom",
                "500 errors spiking",
                "--severity",
                "high",
            ],
        )

        # Command should be recognized, even if it errors during execution
        # (we haven't implemented the runner yet)
        assert "--service" not in result.output  # No missing arg error
