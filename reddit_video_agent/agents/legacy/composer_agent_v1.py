"""
Video Composer Agent - Builds multi-track timeline for video composition
Handles overlap, audio ducking, and layer management
"""

import os
from typing import Dict, List, Any
from .base_agent import BaseAgent
from moviepy.editor import AudioFileClip
import srt
from datetime import timedelta

class VideoComposerAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
        # Composition settings
        self.overlap_strategy = "dynamic"  # fixed, percentage, dynamic
        self.overlap_percentage = 0.5
        self.overlap_max_duration = 10.0
        self.clip_audio_duck_volume = 0.3
        self.fade_duration = 0.5
    
    async def execute(self, assets: Dict) -> Dict:
        """
        Build multi-track timeline from assets.
        
        Args:
            assets: {
                "script": str,
                "parsed_script": Dict (from VideoBreakHandler),
                "voiceover_path": str,
                "captions_path": str (SRT),
                "video_clips": Dict,
                "images": List[str],
                "timeline": Dict (from TimelineBuilder)
            }
        
        Returns:
            Multi-track timeline structure
        """
        print("VideoComposerAgent: Building multi-track timeline...")
        
        parsed_script = assets["parsed_script"]
        voiceover_path = assets["voiceover_path"]
        captions_path = assets["captions_path"]
        video_clips = assets.get("video_clips", {})
        visual_timeline = assets.get("timeline", {})
        
        # Load SRT for timing reference
        srt_entries = self._load_srt(captions_path)
        
        # Build layered timeline
        timeline = self._build_layered_timeline(
            parsed_script,
            srt_entries,
            voiceover_path,
            video_clips,
            visual_timeline
        )
        
        print(f"   ✅ Built timeline with {len(timeline['tracks'])} tracks")
        print(f"   Total duration: {timeline['total_duration']:.1f}s")
        
        return timeline
    
    def _load_srt(self, srt_path: str) -> List:
        """Load and parse SRT file."""
        if not os.path.exists(srt_path):
            return []
        
        with open(srt_path, 'r', encoding='utf-8') as f:
            return list(srt.parse(f.read()))
    
    def _build_layered_timeline(
        self,
        parsed_script: Dict,
        srt_entries: List,
        voiceover_path: str,
        video_clips: Dict,
        visual_timeline: Dict
    ) -> Dict:
        """
        Build multi-track timeline with overlap support.
        """
        timeline = {
            "total_duration": 0.0,
            "tracks": {
                "narration_audio": [],
                "narration_video": [],
                "clip_audio": [],
                "clip_video": [],
                "captions": []
            }
        }
        
        current_time = 0.0
        audio_position = 0.0  # Position in voiceover.mp3
        
        segments = parsed_script["segments"]
        
        for i, segment in enumerate(segments):
            seg_type = segment["type"]
            
            if seg_type in ["narration", "attention_cue"]:
                # Get text and find duration from SRT
                text = segment["text"]
                duration = self._get_duration_from_srt(text, srt_entries, audio_position)
                
                # Get actual audio duration to prevent overflow
                try:
                    audio_file = AudioFileClip(voiceover_path)
                    actual_audio_duration = audio_file.duration
                    audio_file.close()
                    
                    # Cap duration if it exceeds available audio
                    if audio_position + duration > actual_audio_duration:
                        duration = actual_audio_duration - audio_position
                        print(f"   ⚠️ Capping segment duration to {duration:.1f}s (audio limit)")
                except Exception as e:
                    print(f"   ⚠️ Could not get audio duration: {e}")
                
                print(f"   Segment {i+1} ({seg_type}): {duration:.1f}s at timeline {current_time:.1f}s")
                
                # Add narration audio track
                timeline["tracks"]["narration_audio"].append({
                    "source": voiceover_path,
                    "source_start": audio_position,
                    "source_end": audio_position + duration,
                    "timeline_start": current_time,
                    "timeline_end": current_time + duration,
                    "volume": 1.0,
                    "speed": 1.2  # Speed up
                })
                
                # Add narration video track (background + images)
                timeline["tracks"]["narration_video"].append({
                    "type": "composite",
                    "segment_type": seg_type,  # narration or attention_cue
                    "text": text,
                    "srt_start": audio_position,
                    "srt_end": audio_position + duration,
                    "timeline_start": current_time,
                    "timeline_end": current_time + duration,
                    "visual_timeline": self._extract_visuals_for_range(
                        visual_timeline,
                        audio_position,
                        audio_position + duration
                    )
                })
                
                # Add captions track
                captions = self._extract_captions_for_range(
                    srt_entries,
                    audio_position,
                    audio_position + duration
                )
                
                for caption in captions:
                    timeline["tracks"]["captions"].append({
                        "text": caption.content,
                        "timeline_start": current_time + (caption.start.total_seconds() - audio_position),
                        "timeline_end": current_time + (caption.end.total_seconds() - audio_position),
                        "style": "normal"
                    })
                
                # Advance timeline
                current_time += duration
                audio_position += duration
                
            elif seg_type == "video_break":
                clip_type = segment.get("break_type", "action")
                clip_duration = segment["duration"]
                
                # Get video clip path with fallback
                clip_path = None
                if clip_type in video_clips:
                    clip_info = video_clips[clip_type]
                    clip_path = clip_info.get("path") if isinstance(clip_info, dict) else clip_info
                    print(f"   Found clip '{clip_type}': {clip_path}")
                else:
                    # Fallback: Use full video if clip not found
                    print(f"   ⚠️ Clip '{clip_type}' not found in video_clips")
                    print(f"   Available clips: {list(video_clips.keys())}")
                    
                    # Try to use any available clip
                    if video_clips:
                        clip_type = list(video_clips.keys())[0]
                        clip_info = video_clips[clip_type]
                        clip_path = clip_info.get("path") if isinstance(clip_info, dict) else clip_info
                        print(f"   Using fallback clip '{clip_type}': {clip_path}")
                    else:
                        print(f"   ⚠️ No video clips available, skipping video break")
                        continue
                
                # Verify clip exists
                if not clip_path or not os.path.exists(clip_path):
                    print(f"   ⚠️ Clip file not found: {clip_path}, skipping")
                    continue
                
                # Calculate overlap
                overlap_duration = self._calculate_overlap(clip_duration)
                
                print(f"   Segment {i+1} (video_break): {clip_duration:.1f}s with {overlap_duration:.1f}s overlap")
                
                # Add original clip audio track
                timeline["tracks"]["clip_audio"].append({
                    "source": clip_path,
                    "source_start": 0.0,
                    "source_end": clip_duration,
                    "timeline_start": current_time,
                    "timeline_end": current_time + clip_duration,
                    "volume": 1.0,  # Full volume initially
                    "duck_volume": self.clip_audio_duck_volume,
                    "duck_start": current_time + (clip_duration - overlap_duration),
                    "duck_end": current_time + clip_duration,
                    "fade_duration": self.fade_duration
                })
                
                # Add original clip video track
                timeline["tracks"]["clip_video"].append({
                    "source": clip_path,
                    "source_start": 0.0,
                    "source_end": clip_duration,
                    "timeline_start": current_time,
                    "timeline_end": current_time + clip_duration,
                    "z_index": 10  # On top
                })
                
                # Move timeline forward (minus overlap)
                current_time += (clip_duration - overlap_duration)
                
                # Audio position stays the same (we continue from same point)
        
        timeline["total_duration"] = current_time
        return timeline
    
    def _get_duration_from_srt(self, text: str, srt_entries: List, start_position: float) -> float:
        """
        Find duration of text segment from SRT entries.
        """
        # Find first SRT entry that matches start position
        matching_entries = []
        
        for entry in srt_entries:
            entry_start = entry.start.total_seconds()
            entry_end = entry.end.total_seconds()
            
            # Check if this entry is within our range
            if entry_start >= start_position:
                matching_entries.append(entry)
                
                # Check if we've covered the full text
                combined_text = " ".join([e.content for e in matching_entries])
                if len(combined_text) >= len(text) * 0.8:  # 80% match
                    last_entry = matching_entries[-1]
                    duration = last_entry.end.total_seconds() - start_position
                    return duration
        
        # Fallback: estimate based on text length (150 words per minute)
        words = len(text.split())
        estimated_duration = (words / 150) * 60
        return estimated_duration
    
    def _calculate_overlap(self, clip_duration: float) -> float:
        """
        Calculate optimal overlap duration based on strategy.
        """
        if self.overlap_strategy == "fixed":
            return min(5.0, clip_duration)
        
        elif self.overlap_strategy == "percentage":
            return clip_duration * self.overlap_percentage
        
        elif self.overlap_strategy == "dynamic":
            # Short clips (< 10s): 30% overlap
            if clip_duration < 10:
                return clip_duration * 0.3
            # Medium clips (10-20s): 50% overlap
            elif clip_duration < 20:
                return clip_duration * 0.5
            # Long clips (> 20s): Max 10s overlap
            else:
                return min(self.overlap_max_duration, clip_duration * 0.4)
        
        return 0.0
    
    def _extract_visuals_for_range(
        self,
        visual_timeline: Dict,
        start_time: float,
        end_time: float
    ) -> List[Dict]:
        """
        Extract visual layers (images) that fall within time range.
        """
        if not visual_timeline or "layers" not in visual_timeline:
            return []
        
        visuals = []
        for layer in visual_timeline["layers"]:
            if layer.get("type") == "ai_image":
                layer_start = layer.get("start", 0)
                layer_end = layer.get("end", 0)
                
                # Check if layer overlaps with our range
                if layer_start < end_time and layer_end > start_time:
                    # Adjust timestamps to be relative to segment
                    adjusted_layer = layer.copy()
                    adjusted_layer["start"] = max(0, layer_start - start_time)
                    adjusted_layer["end"] = min(end_time - start_time, layer_end - start_time)
                    visuals.append(adjusted_layer)
        
        return visuals
    
    def _extract_captions_for_range(
        self,
        srt_entries: List,
        start_time: float,
        end_time: float
    ) -> List:
        """
        Extract SRT entries that fall within time range.
        """
        captions = []
        for entry in srt_entries:
            entry_start = entry.start.total_seconds()
            entry_end = entry.end.total_seconds()
            
            # Check if entry overlaps with our range
            if entry_start < end_time and entry_end > start_time:
                captions.append(entry)
        
        return captions
