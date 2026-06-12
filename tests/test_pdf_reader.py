import pytest
from unittest.mock import MagicMock
from utils.pdf_reader import extract_text_from_pdf, get_file_hash


def make_mock_file(content: bytes) -> MagicMock:
    mock = MagicMock()
    mock.read.return_value = content
    return mock


def test_invalid_file_header():
    """Non-PDF file should return error"""
    mock_file = make_mock_file(b"not a pdf content here")
    text, error, hash_ = extract_text_from_pdf(mock_file)
    assert text is None
    assert "Invalid file" in error
    assert hash_ is None


def test_file_too_large():
    """File over 10MB should return error"""
    large_content = b'%PDF' + b'x' * (11 * 1024 * 1024)
    mock_file = make_mock_file(large_content)
    text, error, hash_ = extract_text_from_pdf(mock_file)
    assert text is None
    assert "too large" in error
    assert hash_ is None


def test_always_returns_3_tuple():
    """Should always return exactly 3 values — no matter what"""
    mock_file = make_mock_file(b"not a pdf")
    result = extract_text_from_pdf(mock_file)
    assert len(result) == 3


def test_file_hash_consistency():
    """Same content should always produce same hash"""
    content = b"test content for hashing"
    assert get_file_hash(content) == get_file_hash(content)


def test_different_files_different_hash():
    """Different content must produce different hash"""
    assert get_file_hash(b"file one content") != get_file_hash(b"file two content")


def test_error_tuple_structure():
    """On any error, text and hash must be None, error must be string"""
    mock_file = make_mock_file(b"garbage data not pdf")
    text, error, hash_ = extract_text_from_pdf(mock_file)
    assert text is None
    assert isinstance(error, str)
    assert len(error) > 0
    assert hash_ is None