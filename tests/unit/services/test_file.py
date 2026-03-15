import pytest
from unittest.mock import MagicMock
from pathlib import Path
from app.services.file import FileService

@pytest.fixture
def file_service():
    return FileService()

def test_extract_textual_content_pdf(file_service, mocker):
    mock_fitz = mocker.patch("app.services.file.fitz.open")
    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = "PDF Text"
    mock_doc.pages.return_value = [mock_page]
    mock_doc.__len__.return_value = 1
    mock_fitz.return_value = mock_doc
    
    res = file_service.extract_textual_content(Path("test.pdf"))
    assert len(res) == 1
    assert res[0].text == "PDF Text"

def test_extract_textual_content_html(file_service, mocker):
    mocker.patch("builtins.open", mocker.mock_open(read_data="<html><body>HTML Text</body></html>"))
    res = file_service.extract_textual_content(Path("test.html"))
    assert len(res) == 1
    assert res[0].text == "HTML Text"

def test_extract_visual_content_pdf(file_service, mocker):
    mocker.patch("app.services.file.convert_from_path", return_value=[MagicMock(), MagicMock()])
    mocker.patch("app.services.file.pytesseract.image_to_string", return_value="OCR Text")
    res = file_service.extract_visual_content(Path("test.pdf"))
    assert len(res) == 2
    assert res[0].text == "OCR Text"

def test_extract_visual_content_unsupported(file_service):
    res = file_service.extract_visual_content(Path("test.txt"))
    assert res == []
