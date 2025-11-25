# Implementation Plan: Major System Improvements

## User Feedback Summary

User meminta beberapa perbaikan kritis dan fitur baru:

### 1. **Visual/Image Generation Improvements**
**Problem:**
- Style terlalu  generic (Semi-Comic Anime untuk semua)
- Diksi kurang tepat dan tidak familiar
- Tidak menangkap punchline (contoh: "Red Bull" seharusnya jadi highlight)

**Solution:**
- ✅ Analisis konteks konten untuk menentukan style yang sesuai
- ✅ AI memilih diksi yang familiar dan tepat
- ✅ Identifikasi punchline/brand mentions

**Implementation:**
```python
# New VisualAgent._extract_prompts()
1. Analyze post context (extreme sports, funny, tech, etc.)
2. Determine appropriate style:
   - Extreme sports → Realistic action photography style
   - Funny/meme → Cartoon/comic style
   - Tech → Minimalist/modern style
3. Extract familiar terms (brand names, popular references)
4. Identify punchlines/key moments
5. Generate context-aware prompts
```

---

### 2. **Screenshot Frame Issue** ⚠️ **CRITICAL**
**Problem:**
- Thumbnail masih di layer ATAS (menutupi screenshot)
- Belum menjadi frame/bingkai yang benar

**Current State:**
```
Layer order:
1. Background video (looped, darkened)
2. Post screenshot (0-5s)  ← ISSUE: ini overlay di atas video
3. Other visuals
4. Captions
```

**Desired State:**
```
Layer order (0-5s intro):
1. Video thumbnail (extracted frame) ← BOTTOM
2. Post screenshot with "video player area" as frame ← TOP (frame only)
3. Captions
```

**Challenge:**
- Post screenshot adalah PNG solid (tidak transparan di area video player)
- Tidak bisa langsung "mask" area tanpa image processing

**Solution Options:**

**Option A: Remove Post Screenshot (Simplest)**
- Just show video full screen from start
- No framing issue
- ❌ User wants frame effect

**Option B: Composite with Mask (Complex)**
- Detect video player area in screenshot
- Create mask
- Composite video underneath
- ✅ Achieves desired effect
- ⚠️ Requires OpenCV/PIL masking

**Option C: Two-Layer Approach (Recommended)**
- Layer 1: Video thumbnail (full screen, 0-5s)
- Layer 2: Post screenshot with reduced opacity in center (0.3-0.5 opacity)
- Creates "frame" effect without perfect masking
- ✅ Easier to implement
- ✅ Visual effect similar to desired

**Recommended: Option C** - Partial transparency approach

---

### 3. **Audio Speed 1.2x** ✅ **COMPLETED**
- Implemented with pydub
- Added to requirements.txt

---

### 4. **Caption Accuracy Validation**
**Problem:**
- SRT kata-per-kata tidak akurat dengan audio aktual
- Whisper transcription bisa salah

**Solution:**
- Validate SRT against original script
- Use Gemini to align SRT dengan script
- Correct mismatches

**Implementation:**
```python
# New method in AudioAgent or separate CaptionValidator
def validate_captions(srt_path, script_text):
    1. Parse SRT file
    2. Extract all words from SRT
    3. Compare with script words
    4. Use Gemini to align:
       - "Script says 'Red Bull' but SRT says 'red ball'"
       - Fix to 'Red Bull'
    5. Generate corrected SRT
    6. Save as captions_validated.srt
```

---

### 5. **Video Break System** 🆕 **MAJOR FEATURE**
**Concept:**
- Beri waktu penonton untuk nonton video asli
- Narasi memiliki jeda: "Mari kita lihat videonya..."
- Director memotong audio, sisipkan video (dengan audio asli)
- Lanjutkan narasi setelah video selesai

**Example Flow:**
```
[0-10s] Narasi intro
[10-11s] "Mari kita lihat aksinya..." (cue phrase)
[11-25s] VIDEO ASLI dengan AUDIO ASLI (no narration)
[25-45s] Narasi lanjutan "Luar biasa kan? Sekarang..."
```

**Implementation Steps:**

**Step 1: Script Generation with Break Markers**
```python
# ScriptwriterAgent enhancement
prompt = """
Generate script WITH video break markers.

Format:
Intro narration...
[VIDEO_BREAK: 10-15s - show main action]
Continuation narration...

Example:
"Gila guys, ada orang jalan di tali setinggi 1.6 mil!
[VIDEO_BREAK: 0:10-0:25 - tunjukkan aksi slacklining]
Luar biasa kan? Dia berhasil sampai ke basket!"
```

**Step 2: Audio Cutting**
```python
# New AudioBreakHandler
def create_audio_with_breaks(voiceover_path, script_with_markers):
    1. Parse markers from script
    2. Generate voiceover for narration parts only (no video break parts)
    3. Split audio at break points
    4. Return:
       - audio_part1.mp3 (0-10s narration)
       - [BREAK 10s duration]
       - audio_part2.mp3 (continues from 10s mark)
```

**Step 3: Director Assembly**
```python
# Director.execute() enhancement
1. Detect VIDEO_BREAK markers in script
2. Get video clips for break sections
3. Audio timeline:
   - [0-10s] narration audio
   - [10-25s] original video audio
   - [25-45s] narration audio continues
4. Video timeline:
   - [0-10s] background + overlays + captions
   - [10-25s] FULL SCREEN original video (no overlays)
   - [25-45s] background + overlays + captions
```

**Challenges:**
- Voiceover API doesn't support mid-generation breaks
- Need to generate multiple separate voiceovers
- Need to stitch audio timeline
- Need to sync exactly with video

**Solution:**
```
1. Split script into parts before/after breaks
2. Generate separate voiceovers:
   - call TTS("Intro narration") → audio1
   - ...video break happens here...
   - call TTS("Continuation narration") → audio2
3. Director creates composite:
   - AudioComposite([audio1, video_audio, audio2, ...])
```

---

## Implementation Priority

1. ✅ **Audio Speed 1.2x** (Done)
2. 🔧 **Screenshot Frame Fix** (In Progress - Option C)
3. 🔧 **Caption Validation** (Medium complexity)
4. 🔧 **Visual Prompt Improvements** (Medium complexity)
5. 🔧 **Video Break System** (High complexity - requires major refactor)

---

## Next Steps

### Immediate (This Session):
1. Fix screenshot frame (Option C implementation)
2. Implement caption validation
3. Improve visual prompts with context awareness

### Future (Next Session):
4. Video break system (requires architectural changes)
   - Refactor ScriptwriterAgent
   - Refactor VoiceoverAgent (multiple calls)
   - Refactor Director (audio stitching)
   - Refactor Editor (video break sections)

---

## Questions for User

1. **Screenshot Frame**: Apakah Option C (partial transparency approach) acceptable? Atau harus perfect masking (lebih kompleks)?

2. **Video Break**: Berapa panjang ideal untuk video break? 10-20 seconds? Atau flexible berdasarkan konten?

3. **Visual Style**: Apakah ada preference untuk style mapping? Misal:
   - Extreme sports → realistic photography
   - Funny → cartoon
   - Tech → minimalist
   Atau biarkan AI decide sepenuhnya?

4. **Caption Validation**: Apakah cukup validasi otomatis dengan Gemini, atau perlu manual review option?
