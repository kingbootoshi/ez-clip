"""
Tests for the WordToggleView widget.
"""
import importlib.util
import pytest
from unittest.mock import MagicMock
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QApplication
try:
    from PySide6.QtTest import QTest
except ImportError:
    # Create a placeholder for testing environments without QTest
    class QTest:
        @staticmethod
        def mouseClick(*args, **kwargs): 
            pass
from PySide6.QtGui import QMouseEvent

from ez_clip_app.core import EditMask
from ez_clip_app.core.models import Word
from ez_clip_app.ui import WordToggleView


# Mark all tests in this file as GUI tests that will be skipped in CI
pytestmark = pytest.mark.gui

# Skip these tests if no QApplication, no pytest-qt, or headless environment
def has_qt_display():
    """Check if we have a working Qt environment for testing."""
    try:
        if QApplication.instance() is None:
            # Create a temporary app to test if we can
            QApplication([])
        return True
    except Exception:
        return False

# Additional local skip if we don't have the Qt display or pytest-qt
if not has_qt_display() or not importlib.util.find_spec("pytest_qt"):
    pytestmark = pytest.mark.skip(reason="GUI tests require pytest-qt and a working display")


@pytest.fixture
def toggle_view(qtbot):
    """Create a WordToggleView for testing."""
    view = WordToggleView()
    qtbot.addWidget(view)
    return view


def test_set_mask(toggle_view):
    """Test setting a mask on the view."""
    mask = EditMask(media_id=1, keep=[True, False, True])
    toggle_view.set_mask(mask)
    assert toggle_view.mask == mask


def test_set_words(toggle_view):
    """Test setting words on the view."""
    words = [
        Word(w="Hello", s=0.0, e=0.5),
        Word(w="world", s=0.6, e=0.9)
    ]
    toggle_view.set_words(words)
    assert toggle_view.words == words
    
    # Test that it creates a mask automatically if needed
    mask = EditMask(media_id=1, keep=[True, True])
    toggle_view.set_mask(mask)
    
    # Add more words than in the mask
    words.append(Word(w="test", s=1.0, e=1.5))
    toggle_view.set_words(words)
    
    # Mask should now have 3 elements
    assert len(toggle_view.mask.keep) == 3
    assert toggle_view.mask.keep == [True, True, True]


def test_word_toggled_signal(toggle_view, qtbot):
    """Test that clicking a word emits the wordToggled signal."""
    words = [
        Word(w="Hello", s=0.0, e=0.5),
        Word(w="world", s=0.6, e=0.9)
    ]
    mask = EditMask(media_id=1, keep=[True, True])
    toggle_view.set_words(words)
    toggle_view.set_mask(mask)
    
    # Use a mock to capture signal emissions
    with qtbot.waitSignal(toggle_view.wordToggled, timeout=500) as blocker:
        # Since we can't directly click on spans, simulate it by handling mousePressEvent
        toggle_view.anchorAt = MagicMock(return_value="data-i=0")
        event = QMouseEvent(
            QMouseEvent.MouseButtonPress,
            QPoint(10, 10),
            Qt.LeftButton,
            Qt.LeftButton,
            Qt.NoModifier
        )
        toggle_view.mousePressEvent(event)
    
    # Check signal parameters
    assert blocker.args == [0, False]  # Word 0 toggled to False
    assert toggle_view.mask.keep == [False, True]  # Mask should be updated