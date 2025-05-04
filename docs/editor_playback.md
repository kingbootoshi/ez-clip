# EZ-CLIP Playback and Editor Documentation

This document explains how the playback and editor features work in the EZ-CLIP application, including the technical details of how timestamps synchronize between the transcript and the media player.

## Overview

EZ-CLIP combines precise timestamp-based navigation with interactive editing capabilities. The system includes:

1. **Media Player** - PySide6's QMediaPlayer with custom transport controls
2. **Transcript Navigation** - Segment and word-level navigation 
3. **Interactive Editor** - Word-level toggles for keeping or cutting content

## Media Playback System

### Components

The media playback functionality is implemented through a layered architecture:

- **PlayerWidget** - Core video display using PySide6's QVideoWidget and QMediaPlayer
- **TransportBar** - Custom controls (play/pause button and position slider)
- **MediaPane** - Container that integrates PlayerWidget and TransportBar

### How Navigation Works

The application enables precise seeking within media files:

1. **Signal Flow:**
   - Segments/words store timestamps (seconds) from the original transcription
   - When a segment/word is clicked, it emits the timestamp to the MediaPane
   - MediaPane converts seconds to milliseconds and instructs the player to seek
   
2. **Code Path for Segment Navigation:**
   ```python
   # In desktop_gui.py
   def on_segment_clicked(self, row, _col):
       segment_id = self.segments_table.item(row, 0).data(Qt.UserRole)
       seg: Segment = self.db.get_segment(segment_id)
       self.mediaPane.seek(seg.start_sec)  # Seeks to exact time position
   ```

3. **Word-Level Navigation:**
   ```python
   # In desktop_gui.py
   def on_word_clicked(self, row, _col):
       start_sec = float(self.words_table.item(row, 1).text())
       self.mediaPane.seek(start_sec)  # Even more precise seeking
   ```

## Interactive Editor

The Editor tab provides a way to visually select which words to keep or cut from the final output.

### How It Works

1. **Word Representation:**
   - Words are rendered as hyperlinks (`<a>` tags) with classes for "keep" or "cut" status
   - The `WordToggleView` class maintains an `EditMask` tracking which words to keep

2. **Click Handling:**
   - When a word is clicked, the `href` attribute provides the word index
   - The corresponding entry in the EditMask is toggled (true = keep, false = cut)
   - The view is immediately updated with new styling (strikethrough for cut words)
   - A signal is emitted to rebuild the preview

   ```python
   # In word_toggle_view.py
   def mousePressEvent(self, event):
       anchor = self.anchorAt(event.pos())
       if anchor.isdigit():
           word_index = int(anchor)
           new_state = not self.mask.keep[word_index]
           self.mask.keep[word_index] = new_state
           self.wordToggled.emit(word_index, new_state)
           self._rebuild_html()
   ```

3. **Keyboard Support:**
   - Delete/Backspace keys mark selected words as cut
   - The selection can span multiple words

## Preview Generation

When edits are made, a preview is automatically generated:

1. The `PreviewRebuilder` extracts time ranges from the EditMask
2. For each keep=true range, a segment is extracted using ffmpeg
3. These segments are combined into a playlist for seamless playback

```python
# Simplified flow
ranges = mask.build_ranges(words)
for start, end in ranges:
    extract_clip(media_path, output, start, end)
# Build playlist from extracted clips
```

## Database Integration

The editing state is preserved between sessions:

1. EditMasks are serialized to JSON and stored in the `edit_masks` table
2. Each media file can have one associated EditMask
3. When loading a transcript, the corresponding EditMask is loaded automatically

## UI Design Considerations

1. **Visual Feedback:**
   - Words change appearance (color, strikethrough) on toggle
   - Cursor changes to pointer over clickable words
   - Play/pause button toggles icon based on state

2. **Efficient Editing:**
   - Batch selection with keyboard shortcuts
   - Instant visual feedback
   - Automatic preview rebuilding (debounced to prevent excessive processing)

## Known Issues

- FFmpeg warning: `[aac @ 0x...] Could not update timestamps for skipped samples.` 
  - This is a console warning related to audio stream handling during clip generation
  - It doesn't affect functionality but will be addressed in future updates

## Technical Implementation Details

### Signal Chain

The following signal chain ensures that all components stay synchronized:

1. Word toggle → `wordToggled(index, keep)` → MainWindow
2. MainWindow → `save_edit_mask()` → Database
3. MainWindow → `schedule_preview_rebuild()` → PreviewRebuilder
4. PreviewRebuilder → ffmpeg clip extraction → QMediaPlaylist

### PySide6 Compatibility

The code uses compatibility wrappers to support different versions of PySide6:

- Recent versions removed QMediaPlaylist and changed various APIs
- The application detects which version is running and adapts accordingly
- See COMPATIBILITY.md for details