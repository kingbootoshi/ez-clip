~~1. we have full transcript and segments. but segments don't give us word level timestamps, which we'll need for editing

    - create another tab + sql schema DB structure for word level timestamps

    I believe this is going to be required to have some sort of descript like FFMPEG service that can:
        - play the video with word level timestamp cuts
        - let us splice and combine clips
        - let us delete words to make the clip better
        - return the final clip transcript + timestamps that allow our editors to see exactly when, and where to edit. since i'm the content expert,
        their focus should be not on trying to figure out how to make the clip make sense, but to take a clip that already makes sense
        and make it much more entertaining and engaging
    
    - We should be able to correct individual words as well (which will then edit the segment + transcript)~~ (DONE)

~~2. once we have the above, then i want to be able to have the media be displayed on the top left (where it says select media file)
    - if we already processed the transcript, since we save the location of the media, as long as it doesn't move then just load it in from our file system (otherwise, fall back, allow us to choose the new location of media if needed, but still display the processed transcript)

- we should be able to have some sort of editor segment that will:
    a. play the video clip
    b. when we click on segments, take us to that direct segment
    c. when we click on words, take us to that exact level in the timestamp
    d. an editor that allows us to splice/combine different segments (whether it's in the past or in the future relative to the current timestamp),
        and play the edited segments to preview the edit in real time (JUST like descript)
        - perhaps it would be nice if we could even export that edited video + transcript + segment/word level timestamped directions that allow our editors to find it themselves and clip it

        ultimately the goal is, we CANNOT alter the words of the clip, but because we track words on a timestamped level basis, we should be able to edit videos simply by deleting words, splicing segments together, even splicing words together, to create clips that make sense. just like descript~~ (DONE)

3. finally we need a chat part of the GUI, where we can select a video transcript we processed from the library. then open the chat interface
this chat interface should:
    - The system prompt should be a preset one we create that CLEARLY defines the rules of: 
        1. Do NOT ever edit words, or adjust them. The transcript MUST stay 1:1 accurate and absolute at a word level basis in order to ensure the editing works
    - The first message in the system prompt must be hardcoded to show our FULL transcript, I think optimal here is full transcript + segment level timestamps (word level isn't really needed because it gets the job done, our editors can remove filler words)
    - Allow us to select the model
    - Allow us to open different chat history/tabs to switch between attached to that specific video
    - Allow us to edit/delete chat history

bug fixes
- there's no way to upload new media when we select a media thats in the playback, simple gui fix
- we have to split up the desktop_gui into much smaller multiple files, its too big