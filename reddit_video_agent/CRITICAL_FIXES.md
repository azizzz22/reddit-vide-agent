# 🔧 CRITICAL FIXES NEEDED - Implementation Plan

## Issues Identified from Testing

### ✅ **PARTIALLY FIXED**
1. Video Break Structure - Updated to include attention cue

### ⚠️ **IN PROGRESS** 
2. Caption & Image Layers Not Showing
3. Image Generation Improvements
4. Sound Effects Missing

---

## 🎯 **FIX 2: Captions & Images in Video Break Mode**

**Problem**: `_compose_with_video_breaks()` doesn't add captions/images

**Solution**: Add caption and image layers to each narration segment

**Implementation**:
```python
# In _compose_with_video_breaks(), for narration segments:

# 1. Generate captions for this segment
# Parse SRT, extract words for this time range
# Create caption clips

# 2. Add image overlays based on timeline
# Check if any images should appear during this segment
# Add as composite layers

# 3. Composite: background + images + captions
final_segment = CompositeVideoClip([bg, *image_layers, *caption_clips])
```

**Files to Edit**:
- `reddit_video_agent/agents/editor_agent.py` (line ~620-650)

---

## 🎯 **FIX 3: Image Generation with Offset & Context**

**Problem 1**: No offset → hard to remove background
**Problem 2**: Too random, not contextual

**Solution**:

### A. Add Offset to Prompts
```python
# Update prompt template:
"[OBJECT] centered on white background with 50px padding on all sides, 
isolated subject, clear separation from background"
```

### B. Add Full Context
```python
def _extract_prompts(self, text: str, full_context: Dict) -> List[str]:
    prompt = f"""
    Analisis FULL CONTEXT berikut:
    
    JUDUL: {full_context['title']}
    KONTEN: {full_context['content']}
    SCRIPT NARASI: {text}
    KOMENTAR: {full_context['comments']}
    
    Dari context lengkap ini, buat 3-5 prompt gambar yang:
    1. SESUAI dengan keseluruhan cerita (bukan hanya diksi)
    2. Punya offset 50px dari edge (untuk remove bg)
    3. Fokus pada momen kunci dari narasi
    
    Format: "[OBJECT], centered, 50px padding, white background, isolated"
    """
```

**Files to Edit**:
- `reddit_video_agent/agents/visual_agent.py` (line ~45-90)
- `reddit_video_agent/agents/director.py` (pass full context to VisualAgent)

---

## 🎯 **FIX 4: Sound Effects Integration**

**Problem**: SFX downloaded but not used

**Current State**:
- AudioAgent fetches SFX
- Stores in `audio_assets["sound_effects"]`
- But Editor doesn't use them

**Solution**:

### A. Add SFX to Timeline
```python
# In timeline_builder.py:
def add_sfx_markers(timeline, keywords):
    """
    Add SFX at specific moments:
    - "wow", "gila" → whoosh.mp3
    - "lucu", "ngakak" → laugh.mp3
    - action keywords → impact.mp3
    """
    for layer in timeline["layers"]:
        if layer["type"] == "ai_image":
            # Add whoosh when image appears
            layer["sfx"] = "whoosh"
```

### B. Apply SFX in Editor
```python
# In editor_agent.py:
if layer.get("sfx"):
    sfx_clip = AudioFileClip(f"assets/{layer['sfx']}.mp3")
    sfx_clip = sfx_clip.set_start(layer["start"])
    audio_tracks.append(sfx_clip)

# Composite all audio
final_audio = CompositeAudioClip([narration_audio, *sfx_clips])
```

**Files to Edit**:
- `reddit_video_agent/core/timeline_builder.py` (add SFX markers)
- `reddit_video_agent/agents/editor_agent.py` (apply SFX)

---

## 🎯 **FIX 5: Attention Cue Handling**

**New Flow**:
```
Segment 1: Narration Part 1 (8-12s)
  ├── Background video (darkened)
  ├── Images/captions
  └── Narration audio

Segment 2: Attention Cue (2-3s)
  ├── Background video (BRIGHT - no darken!)
  ├── NO images (focus on cue)
  └── Attention cue audio

Segment 3: Video Break (10-15s)
  ├── Original video clip (full screen)
  └── Original audio

Segment 4: Narration Part 2 (10-15s)
  ├── Background video (darkened)
  ├── Images/captions
  └── Narration audio
```

**Implementation**:
```python
# In _compose_with_video_breaks():

elif seg_type == "attention_cue":
    # ATTENTION CUE SEGMENT
    # Bright background, no overlays, just audio
    
    bg = VideoFileClip(video_path).subclip(0, duration)
    bg = bg.resize(height=self.resolution[1])
    # NO DARKENING - keep bright!
    
    # Generate audio for attention cue
    audio_clip = AudioFileClip(segment["audio_path"])
    bg = bg.set_audio(audio_clip)
    
    video_segments.append(bg)
```

**Files to Edit**:
- `reddit_video_agent/core/video_break_handler.py` (✅ Already updated)
- `reddit_video_agent/agents/director.py` (generate audio for attention cue)
- `reddit_video_agent/agents/editor_agent.py` (handle attention_cue segment type)

---

## 📋 **IMPLEMENTATION CHECKLIST**

### Priority 1 (Critical):
- [ ] Fix caption rendering in video break mode
- [ ] Fix image layers in video break mode  
- [ ] Handle attention_cue segment in Editor
- [ ] Generate separate audio for attention cue

### Priority 2 (Important):
- [ ] Add offset to image prompts
- [ ] Pass full context to VisualAgent
- [ ] Improve prompt contextuality

### Priority 3 (Nice to have):
- [ ] Integrate SFX into timeline
- [ ] Apply SFX in final composition

---

## 🚀 **NEXT STEPS**

Due to token limits, I recommend:

1. **Test current fixes** (attention cue parsing is done)
2. **Implement Priority 1** fixes manually or in next session
3. **Verify each fix** with test renders

**Estimated Time**: 2-3 hours for all fixes

---

## 📝 **NOTES**

- Attention cue parsing: ✅ DONE
- Script generation update: ✅ DONE
- Other fixes: Need implementation

The core architecture is solid. These are refinement fixes to improve quality and completeness.
