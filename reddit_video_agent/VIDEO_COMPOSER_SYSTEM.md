# 🎬 Video Composer Agent - Multi-Track Timeline System

## Overview
**VideoComposerAgent** adalah agent baru yang bertanggung jawab untuk membangun **multi-track timeline** seperti di professional video editor (Adobe Premiere, DaVinci Resolve). Agent ini menangani:

- ✅ **Overlap timing** antara narration dan video clips
- ✅ **Audio ducking** untuk smooth transitions
- ✅ **Caption placement** yang tetap muncul selama overlap
- ✅ **Layer management** untuk video, audio, dan captions

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    DIRECTOR AGENT                            │
│  - Orchestrates all agents                                   │
│  - Single TTS generation (full script)                       │
│  - Passes data to VideoComposerAgent                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│              VIDEO COMPOSER AGENT (NEW!)                     │
│  - Builds multi-track timeline                               │
│  - Calculates overlaps (dynamic/fixed/percentage)            │
│  - Manages audio ducking with fade                           │
│  - Handles caption placement across all segments             │
│  - Adjusts visual timeline for each segment                  │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    EDITOR AGENT                              │
│  - Renders multi-track timeline to video                     │
│  - Handles MoviePy composition                               │
│  - Applies audio ducking curves                              │
│  - Exports final video                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## Timeline Structure

### Multi-Track Timeline Format

```python
{
    "total_duration": 40.0,  # Total video duration
    "tracks": {
        # AUDIO TRACKS
        "narration_audio": [
            {
                "source": "voiceover.mp3",
                "source_start": 0.0,      # Start position in source file
                "source_end": 20.0,       # End position in source file
                "timeline_start": 0.0,    # Start position in final video
                "timeline_end": 20.0,     # End position in final video
                "volume": 1.0,
                "speed": 1.2              # Speed multiplier
            },
            {
                "source": "voiceover.mp3",
                "source_start": 20.0,     # Continue from cut point
                "source_end": 35.0,
                "timeline_start": 25.0,   # ← OVERLAP! Starts during video clip
                "timeline_end": 40.0,
                "volume": 1.0,
                "speed": 1.2
            }
        ],
        
        "clip_audio": [
            {
                "source": "action_clip.mp4",
                "source_start": 0.0,
                "source_end": 15.0,
                "timeline_start": 20.0,
                "timeline_end": 35.0,
                "volume": 1.0,
                "duck_volume": 0.3,       # Volume during overlap
                "duck_start": 25.0,       # When to start ducking
                "duck_end": 35.0,         # When to end ducking
                "fade_duration": 0.5      # Fade in/out duration
            }
        ],
        
        # VIDEO TRACKS
        "narration_video": [
            {
                "type": "composite",
                "segment_type": "narration",  # or "attention_cue"
                "text": "Judulnya Float...",
                "srt_start": 0.0,
                "srt_end": 20.0,
                "timeline_start": 0.0,
                "timeline_end": 20.0,
                "visual_timeline": [...]  # Images for this segment
            },
            {
                "type": "composite",
                "segment_type": "narration",
                "text": "Musuhnya udah...",
                "srt_start": 20.0,
                "srt_end": 35.0,
                "timeline_start": 25.0,   # ← OVERLAP!
                "timeline_end": 40.0,
                "visual_timeline": [...]
            }
        ],
        
        "clip_video": [
            {
                "source": "action_clip.mp4",
                "source_start": 0.0,
                "source_end": 15.0,
                "timeline_start": 20.0,
                "timeline_end": 35.0,
                "z_index": 10             # On top of narration video
            }
        ],
        
        # CAPTION TRACK
        "captions": [
            {
                "text": "Judulnya",
                "timeline_start": 0.0,
                "timeline_end": 1.0,
                "style": "normal"
            },
            {
                "text": "Float like a butterfly",
                "timeline_start": 1.0,
                "timeline_end": 2.5,
                "style": "normal"
            },
            # ... captions continue during overlap
            {
                "text": "Musuhnya udah",
                "timeline_start": 25.0,   # ← During overlap!
                "timeline_end": 26.5,
                "style": "normal"
            }
        ]
    }
}
```

---

## Visual Timeline Example

```
TIME:     0s    5s    10s   15s   20s   25s   30s   35s   40s
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NARRATION AUDIO:
[████████████████████]              [████████████████████]
 0s - 20s (source)                   20s - 35s (source)
 0s - 20s (timeline)                 25s - 40s (timeline)
                                      ↑ OVERLAP START!

CLIP AUDIO:
                    [███████████████]
                     0s - 15s (source)
                     20s - 35s (timeline)
                     Volume: 100% → 30% → 100%
                              ↑ Duck  ↑ Fade up

NARRATION VIDEO:
[████████████████████]              [████████████████████]
 BG + Images + Captions               BG + Images + Captions
 0s - 20s                             25s - 40s

CLIP VIDEO:
                    [███████████████]
                     Full Screen
                     20s - 35s
                     z-index: 10 (on top)

CAPTIONS (Always visible):
[████████████████████████████████████████████████████████]
 0s - 40s (continuous, on top of everything)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VIEWER EXPERIENCE:
- 0s-20s: Narration with captions
- 20s-25s: Video clip ONLY (no narration audio, but captions continue!)
- 25s-35s: Video clip + Narration OVERLAP (both visible, clip audio ducked)
- 35s-40s: Narration with captions
```

---

## Overlap Strategies

### 1. Fixed Overlap
```python
overlap_strategy = "fixed"
overlap_duration = 5.0  # Always 5 seconds
```

### 2. Percentage Overlap
```python
overlap_strategy = "percentage"
overlap_percentage = 0.5  # 50% of clip duration
```

### 3. Dynamic Overlap (Recommended)
```python
overlap_strategy = "dynamic"

# Logic:
if clip_duration < 10s:
    overlap = clip_duration * 0.3  # 30%
elif clip_duration < 20s:
    overlap = clip_duration * 0.5  # 50%
else:
    overlap = min(10s, clip_duration * 0.4)  # Max 10s
```

---

## Audio Ducking

### Ducking Curve

```
Volume
100% ┤─────┐                    ┌─────
     │     │                    │
     │     └──────────────┐     │
 30% │                    └─────┘
     │
  0% └────────────────────────────────► Time
          ↑         ↑         ↑
       Duck      Ducked    Fade
       Start               Up
```

### Implementation

```python
def volume_curve(t):
    if t < duck_start:
        return 1.0  # Full volume
    elif t < duck_start + fade_duration:
        # Fade down
        progress = (t - duck_start) / fade_duration
        return 1.0 - (1.0 - duck_volume) * progress
    elif t < duck_end - fade_duration:
        return duck_volume  # Ducked
    elif t < duck_end:
        # Fade up
        progress = (t - (duck_end - fade_duration)) / fade_duration
        return duck_volume + (1.0 - duck_volume) * progress
    else:
        return 1.0  # Full volume
```

---

## Caption Behavior

### During Overlap
```
✅ Captions TETAP MUNCUL selama overlap
✅ Captions di-layer paling atas (z-index tertinggi)
✅ Captions mengikuti narration audio timing
✅ Captions tidak terpengaruh oleh video clip
```

### Example
```
20s-25s: Video clip playing, NO narration audio
         → Captions TIDAK muncul (no audio to caption)

25s-35s: Video clip + Narration overlap
         → Captions MUNCUL (following narration audio)
         → Video clip visible in background
         → Captions on top of video clip
```

---

## Usage

### In Director Agent

```python
from .composer_agent import VideoComposerAgent

# Initialize
composer = VideoComposerAgent(config)

# Build timeline
composer_timeline = await composer.execute({
    "script": full_script,
    "parsed_script": parsed_script,
    "voiceover_path": voiceover_path,
    "captions_path": captions_path,
    "video_clips": video_clips,
    "images": generated_images,
    "timeline": visual_timeline
})

# Pass to Editor
assets["composer_timeline"] = composer_timeline
final_video = await editor.execute(assets)
```

---

## Configuration

```python
# In VideoComposerAgent.__init__()
self.overlap_strategy = "dynamic"      # fixed, percentage, dynamic
self.overlap_percentage = 0.5          # For percentage strategy
self.overlap_max_duration = 10.0       # Max overlap in seconds
self.clip_audio_duck_volume = 0.3      # Volume during duck (30%)
self.fade_duration = 0.5               # Fade in/out duration
```

---

## Benefits

### 1. Professional Quality
- Smooth transitions like professional editors
- No awkward silences
- Engaging viewer experience

### 2. Better Pacing
- Continuous audio flow
- Visual and audio overlap
- More dynamic storytelling

### 3. Flexibility
- Configurable overlap strategies
- Adjustable ducking levels
- Easy to modify timing

### 4. Maintainability
- Clean separation of concerns
- Easy to debug timeline
- Modular architecture

---

## Next Steps

1. ✅ Implement VideoComposerAgent
2. ✅ Update EditorAgent to render from timeline
3. ⏳ Integrate into Director
4. ⏳ Test with Muhammad Ali video
5. ⏳ Fine-tune overlap and ducking parameters

---

## Example Output

```
Input Script:
"Judulnya 'Float like a butterfly', tapi liat videonya! 
Ini orang bukan manusia, tapi BELUT DIKASIH OLI SAMPING! LICIN PARAH!
[VIDEO_BREAK: duration=15s, clip=action]
Musuhnya udah ngeluarin kombo maut, tapi hasilnya? ZONK!"

Timeline Generated:
- 0s-20s: Narration 1 (with captions)
- 20s-35s: Video clip (15s, with original audio)
- 25s-40s: Narration 2 (overlaps with clip, with captions)

Total Duration: 40s
Overlap: 10s (25s-35s)
```
