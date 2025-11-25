from reddit_video_agent.core.video_break_handler import VideoBreakHandler
import json

handler = VideoBreakHandler()

# Mock script with Video Break and Attention Cue
script = """
This is the first part of the narration. It goes on for a bit.
And then I say something to get your attention!
[VIDEO_BREAK: duration=10s, clip=action]
This is the second part of the narration. It continues after the break.
"""

print("--- Parsing Script ---")
parsed = handler.parse_script(script)
print(json.dumps(parsed, indent=2))

print("\n--- Extracting Narration Parts ---")
parts = handler.get_narration_parts(parsed)
print(json.dumps(parts, indent=2))

print("\n--- Building Timeline Info ---")
# Mock audio paths (3 parts)
audio_paths = ["/path/to/narration1.mp3", "/path/to/attention.mp3", "/path/to/narration2.mp3"]
# Mock video clips
video_clips = {
    "action": {"path": "/path/to/action.mp4", "start": 0, "end": 10}
}

timeline = handler.build_timeline_info(parsed, audio_paths, video_clips)
print(json.dumps(timeline, indent=2))
