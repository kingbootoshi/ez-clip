# EZ-CLIP User Guide: Interactive Editor & Media Navigation

This guide shows how to use EZ-CLIP's interactive editor and media navigation features to create precisely edited clips.

## Media Navigation

EZ-CLIP offers multiple ways to navigate through your media files with high precision.

### Using the Transport Controls

![Transport Controls](transport_controls.png)

The transport bar appears directly below the video player and offers:

- **Play/Pause Button**: Toggle playback with a single click
- **Position Slider**: Drag to quickly scrub through the media
  
### Navigating by Segments

The "Segments" tab displays the transcript broken down by speaker segments.

1. Click on any segment row in the table
2. The media player will instantly jump to the start time of that segment
3. Press the Play button to hear the selected segment

This is helpful for quickly navigating between different speakers or topics.

### Word-Level Navigation

For the most precise navigation:

1. Go to the "Words" tab
2. Click on any word in the list
3. The player jumps to the exact timestamp of that word

This feature is invaluable when you need to verify specific words or make fine-grained edits.

## Interactive Editor

The "Editor" tab allows you to decide which words to keep or remove from your final clip.

### Basic Word Editing

1. Navigate to the "Editor" tab
2. **Click on any word** to toggle its state:
   - Normal text = word will be kept
   - Red, strikethrough text = word will be removed
3. As you make selections, the preview automatically updates

### Bulk Editing

To edit multiple words at once:

1. Select a range of text by clicking and dragging
2. Press **Delete** or **Backspace**
3. All selected words will be marked for removal

### Preview Changes

After making edits:

1. The preview is automatically regenerated (this may take a moment)
2. Use the transport controls to play the preview
3. The video will only show the sections you've chosen to keep

### Tips for Effective Editing

- **Speaker Grouping**: Words are grouped by speaker, making it easy to remove entire speaker sections if needed
- **Context Awareness**: The system smartly merges adjacent kept words, avoiding choppy edits
- **Visual Scanning**: The clear visual difference between kept and cut words makes it easy to review your decisions

## Exporting Your Edited Clip

Once you're satisfied with your edits:

1. Go to **File > Export Clip...**
2. Choose a destination and filename
3. Click Save

The system will:
- Extract only the segments you've chosen to keep
- Concatenate them into a single file
- Create accompanying SRT subtitles that match your edits
- Save a JSON file with edit information for future reference

## Troubleshooting

- If you see console warnings about "skipped samples" - these are harmless and don't affect your output
- If the preview seems inconsistent with your edits, try switching to another tab and back to refresh the view
- For very large files, editing may have a slight delay; be patient during preview generation

## Keyboard Shortcuts

- **Delete/Backspace**: Remove selected words
- **Space** (when video player has focus): Toggle play/pause

---

*This interactive editing system combines the precision of text-based editing with the context of video playback, allowing you to create professional-quality clips with minimal effort.*