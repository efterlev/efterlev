"""Terraform parser tests — per-file parsing, tree walking, nested-block access.

Every test writes its own `.tf` source into `tmp_path` so fixtures are visible
in-test and no shared state exists between tests.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from efterlev.errors import DetectorError
from efterlev.terraform import parse_terraform_file, parse_terraform_tree


def test_parses_single_bucket_resource(tmp_path: Path) -> None:
    tf = tmp_path / "main.tf"
    tf.write_text('resource "aws_s3_bucket" "logs" {\n  bucket = "my-logs"\n}\n')
    resources = parse_terraform_file(tf)
    assert len(resources) == 1
    r = resources[0]
    assert r.type == "aws_s3_bucket"
    assert r.name == "logs"
    assert r.body.get("bucket") == "my-logs"
    assert r.source_ref.file == tf
    assert r.source_ref.line_start == 1
    assert r.source_ref.line_end is not None
    assert r.source_ref.line_end >= 2


def test_parses_multiple_resources_with_distinct_line_ranges(tmp_path: Path) -> None:
    tf = tmp_path / "main.tf"
    tf.write_text(
        'resource "aws_s3_bucket" "a" {\n'
        '  bucket = "a"\n'
        "}\n"
        "\n"
        'resource "aws_s3_bucket" "b" {\n'
        '  bucket = "b"\n'
        "}\n"
    )
    resources = parse_terraform_file(tf)
    assert len(resources) == 2
    by_name = {r.name: r for r in resources}
    assert by_name["a"].source_ref.line_start == 1
    assert by_name["b"].source_ref.line_start == 5


def test_nested_blocks_accessible_via_get_nested(tmp_path: Path) -> None:
    tf = tmp_path / "main.tf"
    tf.write_text(
        'resource "aws_s3_bucket" "encrypted" {\n'
        '  bucket = "enc"\n'
        "  server_side_encryption_configuration {\n"
        "    rule {\n"
        "      apply_server_side_encryption_by_default {\n"
        '        sse_algorithm = "AES256"\n'
        "      }\n"
        "    }\n"
        "  }\n"
        "}\n"
    )
    [r] = parse_terraform_file(tf)
    sse = r.get_nested(
        "server_side_encryption_configuration",
        "rule",
        "apply_server_side_encryption_by_default",
    )
    assert sse == {"sse_algorithm": "AES256"}


def test_ignores_non_resource_blocks(tmp_path: Path) -> None:
    tf = tmp_path / "main.tf"
    tf.write_text(
        'variable "region" { default = "us-east-1" }\n'
        "\n"
        'data "aws_caller_identity" "current" {}\n'
        "\n"
        'resource "aws_s3_bucket" "logs" {\n'
        '  bucket = "my-logs"\n'
        "}\n"
    )
    resources = parse_terraform_file(tf)
    assert len(resources) == 1
    assert resources[0].type == "aws_s3_bucket"


def test_walks_tree_across_subdirectories(tmp_path: Path) -> None:
    (tmp_path / "main.tf").write_text('resource "aws_s3_bucket" "main" { bucket = "main" }\n')
    (tmp_path / "modules").mkdir()
    (tmp_path / "modules" / "sub.tf").write_text(
        'resource "aws_s3_bucket" "sub" { bucket = "sub" }\n'
    )
    # Non-.tf files are ignored.
    (tmp_path / "README.md").write_text("# not terraform")

    resources = parse_terraform_tree(tmp_path)
    assert {r.name for r in resources} == {"main", "sub"}


def test_bad_syntax_raises_detector_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.tf"
    bad.write_text("this is not { valid terraform")
    with pytest.raises(DetectorError, match="failed to parse"):
        parse_terraform_file(bad)


def test_nonexistent_target_dir_raises(tmp_path: Path) -> None:
    with pytest.raises(DetectorError, match="not a directory"):
        parse_terraform_tree(tmp_path / "no-such-dir")


def test_empty_dir_returns_empty_list(tmp_path: Path) -> None:
    assert parse_terraform_tree(tmp_path) == []


def test_get_nested_returns_none_on_missing_path(tmp_path: Path) -> None:
    tf = tmp_path / "main.tf"
    tf.write_text('resource "aws_s3_bucket" "plain" { bucket = "p" }\n')
    [r] = parse_terraform_file(tf)
    assert r.get_nested("does", "not", "exist") is None
