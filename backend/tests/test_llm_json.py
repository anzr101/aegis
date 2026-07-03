"""Tests for the JSON-extraction fallback chain in the LLM client."""
import pytest

from app.services.llm import extract_json


def test_plain_json():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_fenced_json():
    text = 'Here you go:\n```json\n{"a": 1, "b": [2, 3]}\n```\nDone.'
    assert extract_json(text) == {"a": 1, "b": [2, 3]}


def test_json_embedded_in_prose():
    text = 'After searching the web, my analysis: {"result": {"nested": true}} — done.'
    assert extract_json(text) == {"result": {"nested": True}}


def test_picks_largest_balanced_object():
    text = 'ignore {"small": 1} but use {"big": {"x": 1, "y": 2}}'
    assert extract_json(text) == {"big": {"x": 1, "y": 2}}


def test_no_json_raises():
    with pytest.raises(ValueError):
        extract_json("there is no json here at all")
