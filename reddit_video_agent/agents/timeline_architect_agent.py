"""
TimelineArchitectAgent - Builds professional multi-track timeline
Handles beat detection, asset placement, transitions, and layer management
"""

import os
from typing import Dict, List, Any, Tuple
from .base_agent import BaseAgent
from moviepy.editor import AudioFileClip
import srt
import re

class TimelineArchitectAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        
    async def execute(self, assets: Dict) -> Dict:
        """
        Build professional multi-track timeline.
        
        Args:
            assets: {
                "script": str,
                "parsed_script": Dict,
                "asset_catalog": Dict (from AssetManager),
                "strategy": Dict (from CompositionStrategy)
            }
        
        Returns:
            Professional timeline with all tracks and transitions
        """
        print("TimelineArchitectAgent: Building timeline...")
        
        script = assets.get("script", "")
        parsed_script = assets.get("parsed_script", {})
        catalog = assets.get("asset_catalog", {}).get("catalog", {})
        strategy = assets.get("strategy", {})
        
        # Detect beats in narration
        beats = await self._detect_beats(catalog.get("narration", {}), strategy)
        
        # Build timeline structure
        timeline = self._build_timeline_structure(
            parsed_script,
            catalog,
            strategy,
            beats
        )
        
        # Place assets optimally
        timeline = self._place_assets(timeline, catalog, strategy, beats)
        
        # Plan transitions
        timeline = self._plan_transitions(timeline, strategy)
        
        # Add metadata
        timeline["metadata"] = {
            "total_duration": timeline.get("total_duration", 0),
            "strategy": strategy.get("strategy_name", "storytelling"),
            "segments": len(parsed_script.get("segments", [])),
            "beats": len(beats),
            "asset_count": self._count_timeline_assets(timeline)
        }
        
        print(f"   ✅ Built timeline: {timeline['metadata']['total_duration']:.1f}s")
        print(f"   Segments: {timeline['metadata']['segments']}, Beats: {timeline['metadata']['beats']}")
        
        return timeline
    
    async def _detect_beats(self, narration: Dict, strategy: Dict) -> List[Dict]:
        """
        Detect natural beats/pauses in narration for asset placement.
        """
        if not narration.get("available"):
            return []
        
        captions_path = narration.get("captions_path")
        if not captions_path or not os.path.exists(captions_path):
            return []
        
        # Load SRT
        with open(captions_path, 'r', encoding='utf-8') as f:
            captions = list(srt.parse(f.read()))
        
        beats = []
        
        # Detect beats based on punctuation and pauses
        for i, caption in enumerate(captions):
            text = caption.content
            start_time = caption.start.total_seconds()
            end_time = caption.end.total_seconds()
            
            # Beat at sentence endings
            if any(p in text for p in ['.', '!', '?']):
                beats.append({
                    "time": end_time,
                    "type": "sentence_end",
                    "text": text,
                    "strength": 0.8
                })
            
            # Beat at long pauses (gap between captions)
            if i < len(captions) - 1:
                next_start = captions[i + 1].start.total_seconds()
                gap = next_start - end_time
                
                if gap > 0.3:  # 300ms pause
                    beats.append({
                        "time": end_time,
                        "type": "pause",
                        "gap": gap,
                        "strength": min(1.0, gap / 0.5)
                    })
        
        # Remove duplicate beats (keep strongest)
        unique_beats = {}
        for beat in beats:
            time_key = round(beat["time"], 1)
            if time_key not in unique_beats or beat["strength"] > unique_beats[time_key]["strength"]:
                unique_beats[time_key] = beat
        
        return sorted(unique_beats.values(), key=lambda x: x["time"])
    
    def _build_timeline_structure(
        self,
        parsed_script: Dict,
        catalog: Dict,
        strategy: Dict,
        beats: List[Dict]
    ) -> Dict:
        """Build basic timeline structure from script segments."""
        
        timeline = {
            "total_duration": 0.0,
            "tracks": {
                "audio": {
                    "narration": [],
                    "clips": [],
                    "sfx": []
                },
                "video": {
                    "background": [],
                    "clips": [],
                    "images": []
                },
                "text": {
                    "captions": [],
                    "titles": []
                }
            },
            "transitions": []
        }
        
        # Get narration info
        narration = catalog.get("narration", {})
        if not narration.get("available"):
            return timeline
        
        narration_path = narration["path"]
        narration_duration = narration["duration"]
        captions_path = narration.get("captions_path")
        
        # Get strategy pacing
        tempo = strategy.get("pacing", {}).get("tempo", 1.0)
        
        current_time = 0.0
        audio_position = 0.0
        
        segments = parsed_script.get("segments", [])
        
        for i, segment in enumerate(segments):
            seg_type = segment["type"]
            
            if seg_type in ["narration", "attention_cue"]:
                # Calculate segment duration from SRT
                text = segment["text"]
                duration = self._estimate_duration_from_text(text, captions_path, audio_position)
                
                # Apply tempo
                actual_duration = duration / tempo
                
                # Add narration audio track
                timeline["tracks"]["audio"]["narration"].append({
                    "source": narration_path,
                    "source_start": audio_position,
                    "source_end": audio_position + duration,
                    "timeline_start": current_time,
                    "timeline_end": current_time + actual_duration,
                    "speed": tempo,
                    "volume": 1.0,
                    "segment_type": seg_type,
                    "segment_index": i
                })
                
                # Add background video
                bg = catalog.get("background", {})
                if bg.get("available"):
                    timeline["tracks"]["video"]["background"].append({
                        "source": bg["path"],
                        "timeline_start": current_time,
                        "timeline_end": current_time + actual_duration,
                        "loop": True,
                        "effects": ["darken_0.6"] if seg_type == "narration" else []
                    })
                
                current_time += actual_duration
                audio_position += duration
                
            elif seg_type == "video_break":
                clip_type = segment.get("break_type", "action")
                clip_duration = segment.get("duration", 10.0)
                
                # Get video clip
                video_clips = catalog.get("video_clips", {})
                clip_info = None
                
                if clip_type in video_clips and video_clips[clip_type].get("available"):
                    clip_info = video_clips[clip_type]
                else:
                    # Fallback to any available clip
                    for vtype, vinfo in video_clips.items():
                        if vinfo.get("available"):
                            clip_info = vinfo
                            break
                
                if clip_info:
                    clip_path = clip_info["path"]
                    actual_clip_duration = min(clip_duration, clip_info.get("duration", clip_duration))
                    
                    # Calculate overlap
                    overlap_pct = strategy.get("audio", {}).get("overlap_percentage", 0.5)
                    overlap_duration = actual_clip_duration * overlap_pct
                    
                    # Add clip video
                    timeline["tracks"]["video"]["clips"].append({
                        "source": clip_path,
                        "source_start": 0.0,
                        "source_end": actual_clip_duration,
                        "timeline_start": current_time,
                        "timeline_end": current_time + actual_clip_duration,
                        "z_index": 10,
                        "segment_index": i
                    })
                    
                    # Add clip audio with ducking (User Request: 90% base, 30% overlap for contrast)
                    duck_volume = 0.3  # 30% during overlap (High Contrast)
                    timeline["tracks"]["audio"]["clips"].append({
                        "source": clip_path,
                        "source_start": 0.0,
                        "source_end": actual_clip_duration,
                        "timeline_start": current_time,
                        "timeline_end": current_time + actual_clip_duration,
                        "volume": 0.9,  # 90% base volume
                        "ducking": {
                            "enabled": True,
                            "start": current_time + (actual_clip_duration - overlap_duration),
                            "end": current_time + actual_clip_duration,
                            "target_volume": duck_volume,
                            "curve": strategy.get("audio", {}).get("ducking_curve", "smooth")
                        },
                        "segment_index": i
                    })
                    
                    # Move timeline forward (minus overlap)
                    current_time += (actual_clip_duration - overlap_duration)
        
        # Build audio-to-timeline mapping for caption synchronization
        audio_timeline_map = []
        for narr_track in timeline["tracks"]["audio"]["narration"]:
            audio_timeline_map.append({
                "audio_start": narr_track["source_start"],
                "audio_end": narr_track["source_end"],
                "timeline_start": narr_track["timeline_start"],
                "timeline_end": narr_track["timeline_end"],
                "tempo": narr_track.get("speed", 1.0)
            })
        
        # Add captions with accurate timing adjustment
        if captions_path and os.path.exists(captions_path):
            try:
                with open(captions_path, 'r', encoding='utf-8') as f:
                    captions = list(srt.parse(f.read()))
                
                for caption in captions:
                    audio_start = caption.start.total_seconds()
                    audio_end = caption.end.total_seconds()
                    
                    # Find matching narration segment
                    for segment in audio_timeline_map:
                        if segment["audio_start"] <= audio_start < segment["audio_end"]:
                            # Map audio time to timeline time with tempo adjustment
                            offset_in_audio = audio_start - segment["audio_start"]
                            offset_in_timeline = offset_in_audio / segment["tempo"]
                            timeline_start = segment["timeline_start"] + offset_in_timeline
                            
                            # Same for end time
                            offset_in_audio_end = min(audio_end, segment["audio_end"]) - segment["audio_start"]
                            offset_in_timeline_end = offset_in_audio_end / segment["tempo"]
                            timeline_end = segment["timeline_start"] + offset_in_timeline_end
                            
                            timeline["tracks"]["text"]["captions"].append({
                                "text": caption.content,
                                "timeline_start": timeline_start,
                                "timeline_end": timeline_end,
                                "z_index": 100
                            })
                            break
                
                print(f"   ✅ Added {len(timeline['tracks']['text']['captions'])} captions with tempo adjustment")
            except Exception as e:
                print(f"   ⚠️ Error adding captions: {e}")

        timeline["total_duration"] = current_time
        return timeline
    
    def _place_assets(
        self,
        timeline: Dict,
        catalog: Dict,
        strategy: Dict,
        beats: List[Dict]
    ) -> Dict:
        """Place images, screenshots, and SFX at optimal positions."""
        
        # Place Post Screenshot (Intro)
        screenshots = catalog.get("screenshots", {})
        if screenshots.get("post"):
            timeline["tracks"]["video"]["images"].append({
                "source": screenshots["post"]["path"],
                "timeline_start": 0.0,
                "timeline_end": 5.0,
                "z_index": 5,
                "position": "center",
                "scale": 0.9,
                "animation": {"type": "static"}
            })
            
        # Place images at beats
        images = catalog.get("images", [])
        if images and beats:
            image_duration = strategy.get("visual", {}).get("image_duration", 2.0)
            placement_style = strategy.get("visual", {}).get("image_placement", "beat_synchronized")
            
            # Select beats for image placement (not too close together)
            selected_beats = self._select_image_beats(beats, len(images), image_duration)
            
            for i, (beat, img) in enumerate(zip(selected_beats, images)):
                beat_time = beat["time"]
                
                timeline["tracks"]["video"]["images"].append({
                    "source": img["path"],
                    "timeline_start": beat_time,
                    "timeline_end": beat_time + image_duration,
                    "z_index": 5,
                    "position": "center",
                    "scale": 0.8,
                    "animation": {
                        "type": "ken_burns",
                        "zoom": 1.1,
                        "pan": ["left_to_right", "right_to_left"][i % 2]
                    },
                    "transition_in": {"type": "fade", "duration": 0.3},
                    "transition_out": {"type": "fade", "duration": 0.3}
                })
        
        # Place SFX at video break starts
        sfx_list = catalog.get("sound_effects", [])
        if sfx_list:
            for clip in timeline["tracks"]["video"]["clips"]:
                if sfx_list:
                    sfx = sfx_list[0]  # Use first SFX for now
                    timeline["tracks"]["audio"]["sfx"].append({
                        "source": sfx["path"],
                        "timeline_start": clip["timeline_start"],
                        "volume": 0.7,
                        "trigger": "video_break_start"
                    })
        
        return timeline
    
    def _plan_transitions(self, timeline: Dict, strategy: Dict) -> Dict:
        """Plan transitions between segments."""
        
        transition_style = strategy.get("visual", {}).get("transition_style", "smooth_fades")
        
        # Add transitions between narration segments and video clips
        narration_segments = timeline["tracks"]["audio"]["narration"]
        video_clips = timeline["tracks"]["video"]["clips"]
        
        for clip in video_clips:
            clip_start = clip["timeline_start"]
            
            # Find narration segment before this clip
            prev_narration = None
            for narr in narration_segments:
                if narr["timeline_end"] <= clip_start:
                    prev_narration = narr
            
            if prev_narration:
                # Add transition
                timeline["transitions"].append({
                    "type": "crossfade" if "fade" in transition_style else "cut",
                    "from_segment": prev_narration["segment_index"],
                    "to_segment": clip["segment_index"],
                    "timeline_start": prev_narration["timeline_end"],
                    "duration": 0.5 if "fade" in transition_style else 0.0
                })
        
        return timeline
    
    def _estimate_duration_from_text(self, text: str, captions_path: str, start_position: float) -> float:
        """Estimate duration from text using SRT."""
        if not captions_path or not os.path.exists(captions_path):
            # Fallback: estimate from word count
            words = len(text.split())
            return (words / 150) * 60  # 150 words per minute
        
        # Load SRT and find matching captions
        with open(captions_path, 'r', encoding='utf-8') as f:
            captions = list(srt.parse(f.read()))
        
        # Find captions that match this text
        text_words = set(text.lower().split())
        matching_captions = []
        
        for caption in captions:
            if caption.start.total_seconds() >= start_position:
                caption_words = set(caption.content.lower().split())
                if text_words & caption_words:  # Has common words
                    matching_captions.append(caption)
                    
                    # Check if we've covered most of the text
                    covered_text = " ".join([c.content for c in matching_captions])
                    if len(covered_text) >= len(text) * 0.8:
                        last_caption = matching_captions[-1]
                        return last_caption.end.total_seconds() - start_position
        
        # Fallback
        words = len(text.split())
        return (words / 150) * 60
    
    def _select_image_beats(self, beats: List[Dict], image_count: int, image_duration: float) -> List[Dict]:
        """Select beats for image placement (avoid overlap)."""
        if not beats:
            return []
        
        selected = []
        last_time = -image_duration * 2  # Ensure first beat is selected
        
        for beat in beats:
            if beat["time"] - last_time >= image_duration * 0.8:  # 80% of duration as minimum gap
                selected.append(beat)
                last_time = beat["time"]
                
                if len(selected) >= image_count:
                    break
        
        return selected
    
    def _count_timeline_assets(self, timeline: Dict) -> int:
        """Count total assets in timeline."""
        count = 0
        for track_type in timeline["tracks"].values():
            for track in track_type.values():
                count += len(track)
        return count
