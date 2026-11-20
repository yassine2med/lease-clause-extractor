from pathlib import Path

import pytest

from lease_clauses import core
from lease_clauses.cli import main

DATA = Path(__file__).resolve().parents[1] / "data"


def test_parse_date_formats():
    assert core.parse_date("on March 1, 2024 and later") == "2024-03-01"
    assert core.parse_date("07/01/2025") == "2025-07-01"
    assert core.parse_date("ends 2028-06-30") == "2028-06-30"
    assert core.parse_date("Sept. 5, 2026") == "2026-09-05"


def test_parse_date_rejects_impossible_and_missing():
    assert core.parse_date("February 30, 2026") is None
    assert core.parse_date("no date here") is None


def test_parse_money():
    assert core.parse_money("rent of $12,500.00 per month") == 12500.0
    assert core.parse_money("deposit $33,000") == 33000.0
    assert core.parse_money("nothing") is None


def test_parse_days():
    assert core.parse_days("at least 180 days before") == 180
    assert core.parse_days("ninety (90) days written notice") == 90
    assert core.parse_days("no period") is None


def test_full_lease_extraction():
    found = core.extract((DATA / "lease_suite_100.txt").read_text())
    assert found["commencement_date"].value == "2024-03-01"
    assert found["expiration_date"].value == "2029-02-28"
    assert found["monthly_rent"].value == 12500.0
    assert found["security_deposit"].value == 25000.0
    assert found["annual_increase_pct"].value == 3.0
    assert found["renewal_notice_days"].value == 180
    assert found["termination_notice_days"].value == 90


def test_annual_rent_is_converted_to_monthly():
    found = core.extract((DATA / "lease_warehouse_b.txt").read_text())
    assert found["monthly_rent"].value == 16500.0
    assert found["annual_increase_pct"].value == 2.5
    assert found["termination_notice_days"].value == 60


def test_missing_fields_are_none_not_guessed():
    found = core.extract((DATA / "lease_storefront_c.txt").read_text())
    assert found["security_deposit"] is None and found["renewal_notice_days"] is None
    assert found["monthly_rent"].value == 4200.0


def test_empty_text():
    assert all(v is None for v in core.extract("").values())


def test_deposit_sentence_is_not_read_as_rent():
    found = core.extract("The security deposit is $5,000 and rent is not stated.")
    assert found["monthly_rent"] is None and found["security_deposit"].value == 5000.0


def test_source_sentence_is_kept():
    found = core.extract((DATA / "lease_suite_100.txt").read_text())
    assert "180 days" in found["renewal_notice_days"].source


def test_cli_table_json_csv(tmp_path, capsys):
    out = tmp_path / "o.csv"
    assert main([str(DATA / "lease_suite_100.txt"), "--csv", str(out), "--show-source"]) == 0
    text = capsys.readouterr().out
    assert "monthly_rent" in text and "from:" in text
    assert out.read_text().splitlines()[0].startswith("file,commencement_date")
    assert main([str(DATA / "lease_storefront_c.txt"), "--json"]) == 0
    assert '"security_deposit": null' in capsys.readouterr().out


def test_cli_missing_file(capsys):
    assert main(["missing.txt"]) == 1
