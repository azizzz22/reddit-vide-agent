# Future Enhancements

## 1. TikTok-Style Word Highlighting Agent

### Concept
Create a dedicated `CaptionStyleAgent` that transforms standard SRT captions into TikTok-style animated captions with word-level highlighting.

### Features
- **Word-Level Timing:** Parse SRT and estimate timing for each word
- **Dynamic Highlighting:** Highlight current word being spoken (bold/color/offset)
- **Smooth Transitions:** Animate highlight moving from word to word
- **Customizable Styles:** Support multiple highlight styles (bold, color, scale, glow)

### Architecture
```python
class CaptionStyleAgent(BaseAgent):
    async def execute(self, captions_srt_path: str, style: str = "tiktok") -> List[VideoClip]:
        """
        Transform SRT captions into styled video clips.
        
        Args:
            captions_srt_path: Path to SRT file
            style: "tiktok" | "youtube" | "karaoke"
        
        Returns:
            List of TextClip objects ready for compositing
        """
        # 1. Parse SRT
        # 2. Estimate word-level timing
        # 3. Create composite clips with highlighting
        # 4. Return ready-to-use clips
```

### Implementation Notes
- Use Whisper word-level timestamps if available (future Whisper API upgrade)
- Fallback to duration-based estimation (current approach)
- Create separate method for each style (modular)
- Non-invasive: EditorAgent just calls this agent if enabled

### Benefits
- ✅ Modular (doesn't touch existing code)
- ✅ Reusable (can be toggled on/off)
- ✅ Extensible (easy to add new styles)
- ✅ Professional (TikTok-level engagement)

### Priority
**Medium-High** - Significant engagement boost for viral videos

---

## 2. Context-Aware Asset Placement (IMPLEMENTED ✅)
- Factual vs Ambiguous visual markers
- Expectation management in narration

## 3. Advanced Audio Ducking (IMPLEMENTED ✅)
- 90% base volume, 30% during overlap
- Tempo-aware caption synchronization
