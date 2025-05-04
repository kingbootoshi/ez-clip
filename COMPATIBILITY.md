# PySide6 Compatibility Notes

The EZ-CLIP application has been updated to handle different versions of PySide6, which has undergone significant API changes between versions.

## Known Compatibility Issues

### QMediaPlaylist Removal
In newer versions of PySide6, the `QMediaPlaylist` class has been removed. The application includes a fallback mechanism that will:
- Use `QMediaPlaylist` if available (older PySide6 versions)
- Fall back to loading individual clips for newer versions

### API Changes
Several Qt classes have been moved between modules:
- `QAction` moved from `QtWidgets` to `QtGui`
- Audio handling (`QAudioOutput`) has been refactored
- Media loading methods have changed from `setMedia()` to `setSource()`

## If You Experience Issues

If you encounter compatibility problems:

1. Try installing a specific version of PySide6:
   ```
   pip install PySide6==6.3.1
   ```

2. Alternatively, use our compatibility shims which should handle most common issues
   across different PySide6 versions.

3. Report any persistent issues with details about your PySide6 version.