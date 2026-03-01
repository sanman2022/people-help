"""Tests for RAG chunking logic (no external deps — pure functions only)."""

from services.rag import chunk_text


class TestChunkText:
    def test_single_short_paragraph(self):
        text = "This is a short paragraph."
        chunks = chunk_text(text, max_chars=800)
        assert len(chunks) == 1
        assert chunks[0] == text

    def test_multiple_paragraphs_fit_in_one_chunk(self):
        text = "Para one.\n\nPara two.\n\nPara three."
        chunks = chunk_text(text, max_chars=800)
        assert len(chunks) == 1

    def test_paragraphs_split_across_chunks(self):
        p1 = "A" * 400
        p2 = "B" * 400
        p3 = "C" * 400
        text = f"{p1}\n\n{p2}\n\n{p3}"
        chunks = chunk_text(text, max_chars=500)
        assert len(chunks) >= 2
        # Each chunk should be within the limit (roughly)
        for chunk in chunks:
            assert len(chunk) <= 900  # some slack from paragraph concatenation

    def test_empty_paragraphs_ignored(self):
        text = "Para one.\n\n\n\n\n\nPara two."
        chunks = chunk_text(text, max_chars=800)
        assert len(chunks) == 1
        assert "Para one." in chunks[0]
        assert "Para two." in chunks[0]

    def test_very_long_single_paragraph(self):
        text = "X" * 2000
        chunks = chunk_text(text, max_chars=800)
        # Should produce at least 1 chunk
        assert len(chunks) >= 1

    def test_preserves_content(self):
        text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        chunks = chunk_text(text, max_chars=800)
        joined = " ".join(chunks)
        assert "First paragraph." in joined
        assert "Second paragraph." in joined
        assert "Third paragraph." in joined

    def test_small_max_chars(self):
        text = "Short one.\n\nShort two.\n\nShort three."
        chunks = chunk_text(text, max_chars=20)
        assert len(chunks) >= 2
