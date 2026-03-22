from ghud.cli import parse_args


def test_default_args():
    args = parse_args([])
    assert args.command is None  # default = dashboard
    assert args.all is False
    assert args.days == 7


def test_all_flag():
    args = parse_args(["--all"])
    assert args.all is True


def test_days_flag():
    args = parse_args(["--days", "14"])
    assert args.days == 14


def test_discover_subcommand():
    args = parse_args(["discover"])
    assert args.command == "discover"


def test_discover_dry_run():
    args = parse_args(["discover", "--dry-run"])
    assert args.command == "discover"
    assert args.dry_run is True
