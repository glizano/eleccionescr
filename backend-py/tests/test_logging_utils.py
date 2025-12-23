"""Tests for logging utilities with security safeguards."""

import pytest

from app.utils.logging import sanitize_for_log


class TestSanitizeForLog:
    """Test cases for sanitize_for_log function."""

    def test_normal_text(self):
        """Test that normal text passes through unchanged."""
        assert sanitize_for_log("normal text") == "normal text"

    def test_remove_newlines(self):
        """Test that newlines are replaced with spaces."""
        assert sanitize_for_log("text\nwith\nnewlines") == "text with newlines"

    def test_remove_carriage_returns(self):
        """Test that carriage returns are replaced with spaces."""
        assert sanitize_for_log("text\rwith\rcarriage\rreturns") == "text with carriage returns"

    def test_remove_tabs(self):
        """Test that tabs are replaced with spaces."""
        assert sanitize_for_log("text\twith\ttabs") == "text with tabs"

    def test_remove_control_characters(self):
        """Test that control characters are replaced with spaces."""
        # Test null byte
        assert sanitize_for_log("text\x00with\x00null") == "text with null"
        # Test other control characters
        assert sanitize_for_log("text\x01\x02\x03") == "text"

    def test_multiple_spaces_collapsed(self):
        """Test that multiple spaces are collapsed to single space."""
        assert sanitize_for_log("text  with   multiple    spaces") == "text with multiple spaces"

    def test_strip_whitespace(self):
        """Test that leading and trailing whitespace is removed."""
        assert sanitize_for_log("  text with spaces  ") == "text with spaces"

    def test_empty_string(self):
        """Test that empty string returns empty string."""
        assert sanitize_for_log("") == ""

    def test_none_value(self):
        """Test that None returns empty string."""
        assert sanitize_for_log(None) == ""

    def test_whitespace_only(self):
        """Test that whitespace-only string returns empty string."""
        assert sanitize_for_log("   \n\r\t   ") == ""

    def test_log_injection_attempt(self):
        """Test that log injection attempts are neutralized."""
        # Simulate attempt to inject fake log entries
        malicious = "user input\n2024-01-01 00:00:00 - ERROR - Fake error message"
        sanitized = sanitize_for_log(malicious)
        assert "\n" not in sanitized
        assert sanitized == "user input 2024-01-01 00:00:00 - ERROR - Fake error message"

    def test_crlf_injection(self):
        """Test that CRLF injection is prevented."""
        malicious = "test\r\nInjected: malicious content"
        sanitized = sanitize_for_log(malicious)
        assert "\r" not in sanitized
        assert "\n" not in sanitized
        assert sanitized == "test Injected: malicious content"

    def test_unicode_characters_preserved(self):
        """Test that valid unicode characters are preserved."""
        assert sanitize_for_log("¡Hola! ¿Cómo estás?") == "¡Hola! ¿Cómo estás?"
        assert sanitize_for_log("你好世界") == "你好世界"
        assert sanitize_for_log("مرحبا بالعالم") == "مرحبا بالعالم"

    def test_mixed_content(self):
        """Test with mixed content including control chars and unicode."""
        text = "Question:\nWhat is Costa Rica?\rParty: PAC\tCandidate: José María"
        expected = "Question: What is Costa Rica? Party: PAC Candidate: José María"
        assert sanitize_for_log(text) == expected

    def test_numeric_conversion(self):
        """Test that numeric values are converted to strings."""
        assert sanitize_for_log(12345) == "12345"
        assert sanitize_for_log(123.45) == "123.45"

    def test_ansi_escape_codes(self):
        """Test that ANSI escape codes control characters are removed."""
        # ANSI color codes contain control characters (\x1b)
        ansi_text = "\x1b[31mRed Text\x1b[0m"
        sanitized = sanitize_for_log(ansi_text)
        # The \x1b control character should be removed, but the rest remains
        assert "\x1b" not in sanitized
        assert "Red" in sanitized and "Text" in sanitized
