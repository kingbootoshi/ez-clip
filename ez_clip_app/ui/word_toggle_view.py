"""
WordToggleView for text-driven editing functionality.

This module defines a QTextBrowser subclass that displays words with toggleable
keep/cut states for editing in the EZ CLIP app.
"""
from typing import List
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTextBrowser
from PySide6.QtGui import QMouseEvent, QKeyEvent

from ez_clip_app.core import EditMask


class WordToggleView(QTextBrowser):
    """Interactive view that allows toggling words between keep/cut states.
    
    Displays transcript words as clickable spans that can be toggled between
    "keep" (default) and "cut" states with visual styling.
    
    Signals:
        wordToggled: Emitted when a word is toggled with (index, keep) parameters
    """
    wordToggled = Signal(int, bool)  # index, keep
    
    def __init__(self, parent=None):
        """Initialize the WordToggleView.
        
        Args:
            parent: Optional parent widget
        """
        super().__init__(parent)
        self.setOpenLinks(False)
        self.setReadOnly(True)
        
        # Custom CSS for keep/cut states with improved styling
        self.document().setDefaultStyleSheet("""
            a.keep { color: #fff; text-decoration: none; cursor: pointer; }
            a.cut { color: #888; text-decoration: line-through; cursor: pointer; background: #922; }
        """)
        
        # Track words and mask
        self.words = []
        self.mask = None
        
    def set_mask(self, mask: EditMask) -> None:
        """Set and display the current edit mask.
        
        Args:
            mask: The EditMask to display
        """
        self.mask = mask
        self._rebuild_html()
        
    def set_words(self, words: List) -> None:
        """Set the list of words to display.
        
        Args:
            words: List of Word objects from the transcript
        """
        self.words = words
        
        # If we have a mask but it doesn't match words count, create a new one
        if self.mask and len(self.mask.keep) != len(words):
            self.mask.keep = [True] * len(words)
        
        self._rebuild_html()
    
    def _rebuild_html(self) -> None:
        """Rebuild the HTML content based on current words and mask."""
        if not self.words or not self.mask:
            return
            
        html = ["<html><body>"]
        
        # Merge words from same speakers into paragraphs
        current_speaker = None
        
        for i, word in enumerate(self.words):
            # Get keep state from mask
            keep = self.mask.keep[i]
            
            # Extract speaker from word's segment (if available)
            speaker = getattr(word, "speaker", None)
            
            # Start new paragraph for new speaker
            if speaker != current_speaker:
                if current_speaker is not None:
                    html.append("</p>")
                html.append(f"<p><b>{speaker or 'Speaker'}:</b> ")
                current_speaker = speaker
            
            # Add word as a real hyperlink so anchorAt() works
            css_class = "keep" if keep else "cut"
            html.append(f'<a href="{i}" class="{css_class}">{word.w}</a> ')
        
        # Close last paragraph
        if current_speaker is not None:
            html.append("</p>")
            
        html.append("</body></html>")
        self.setHtml("".join(html))
    
    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Handle mouse click events to toggle words.
        
        Args:
            event: Mouse event
        """
        super().mousePressEvent(event)
        
        # Get clicked element - now returns the href attribute value
        anchor = self.anchorAt(event.pos())
        
        # Check if it's a valid digit (word index)
        if anchor.isdigit():
            try:
                word_index = int(anchor)
                # Toggle the keep state
                new_state = not self.mask.keep[word_index]
                self.mask.keep[word_index] = new_state
                # Emit signal
                self.wordToggled.emit(word_index, new_state)
                # Update display
                self._rebuild_html()
            except (ValueError, IndexError):
                pass
    
    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle key press events for editing.
        
        Implements Del/Backspace to mark selected words as cut.
        
        Args:
            event: Key event
        """
        # Check if Delete or Backspace was pressed
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            # Get selected text indices
            cursor = self.textCursor()
            
            # If no selection, process key normally
            if cursor.hasSelection():
                # Get HTML and parse out the selected word indices
                html = self.toHtml()
                selected_html = cursor.selectedText()
                
                # Find all links in the selection
                import re
                # Get indices of all links in the selection
                indices = []
                for match in re.finditer(r'<a href="(\d+)"', html):
                    idx = int(match.group(1))
                    # Check if this index is within the selection
                    if match.start() >= cursor.selectionStart() and match.end() <= cursor.selectionEnd():
                        indices.append(idx)
                
                # Mark all selected words as cut
                changed = False
                for idx in indices:
                    if idx < len(self.mask.keep) and self.mask.keep[idx]:
                        self.mask.keep[idx] = False
                        self.wordToggled.emit(idx, False)
                        changed = True
                
                # Update display if needed
                if changed:
                    self._rebuild_html()
                return
        
        # Otherwise, let the parent handle the key press
        super().keyPressEvent(event)