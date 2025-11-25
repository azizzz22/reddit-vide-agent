"""
Video Break Handler - Parses script with VIDEO_BREAK markers and manages audio splitting
"""

import re
from typing import List, Dict, Tuple

class VideoBreakHandler:
    def __init__(self):
        pass
    
    def parse_script(self, script: str) -> Dict:
        """
        Parse script with VIDEO_BREAK markers and ATTENTION CUES.
        
        Attention cue = last sentence before VIDEO_BREAK (usually ends with ! or ?)
        
        Returns:
        {
            "has_breaks": bool,
            "segments": [
                {"type": "narration", "text": "Main narration...", "order": 0},
                {"type": "attention_cue", "text": "Coba lihat ini!", "order": 1},
                {"type": "video_break", "duration": 15, "break_type": "action", "order": 2},
                {"type": "narration", "text": "Continuation...", "order": 3}
            ]
        }
        """
        # Find all VIDEO_BREAK markers
        break_pattern = r'\[VIDEO_BREAK:\s*duration=(\d+(?:-\d+)?s?),\s*(?:clip|type)=(\w+)\]'
        breaks = list(re.finditer(break_pattern, script))
        
        if not breaks:
            # No breaks found
            return {
                "has_breaks": False,
                "segments": [{"type": "narration", "text": script.strip(), "order": 0}]
            }
        
        # Split script by breaks
        segments = []
        last_end = 0
        order = 0
        
        for i, match in enumerate(breaks):
            # Get narration before this break
            narration_text = script[last_end:match.start()].strip()
            
            if narration_text:
                # Split attention cue from main narration
                # Attention cue = last sentence (ends with ! or ?)
                sentences = re.split(r'([.!?]+\s*)', narration_text)
                
                # Reconstruct sentences
                full_sentences = []
                for j in range(0, len(sentences)-1, 2):
                    if j+1 < len(sentences):
                        full_sentences.append(sentences[j] + sentences[j+1])
                
                if len(full_sentences) > 1:
                    # Last sentence = attention cue
                    attention_cue = full_sentences[-1].strip()
                    main_narration = ''.join(full_sentences[:-1]).strip()
                    
                    # Add main narration
                    if main_narration:
                        segments.append({
                            "type": "narration",
                            "text": main_narration,
                            "order": order
                        })
                        order += 1
                    
                    # Add attention cue
                    segments.append({
                        "type": "attention_cue",
                        "text": attention_cue,
                        "order": order
                    })
                    order += 1
                else:
                    # Only one sentence, treat as narration
                    segments.append({
                        "type": "narration",
                        "text": narration_text,
                        "order": order
                    })
                    order += 1
            
            # Parse break duration
            duration_str = match.group(1)
            # Handle range like "10-15s"
            if '-' in duration_str:
                # Take middle value
                parts = duration_str.replace('s', '').split('-')
                duration = (int(parts[0]) + int(parts[1])) // 2
            else:
                duration = int(duration_str.replace('s', ''))
            
            break_type = match.group(2)
            
            # Add video break
            segments.append({
                "type": "video_break",
                "duration": duration,
                "break_type": break_type,
                "order": order
            })
            order += 1
            
            last_end = match.end()
        
        # Add final narration after last break
        final_narration = script[last_end:].strip()
        if final_narration:
            segments.append({
                "type": "narration",
                "text": final_narration,
                "order": order
            })
        
        return {
            "has_breaks": True,
            "segments": segments
        }
    
    def get_narration_parts(self, parsed_script: Dict) -> List[Dict]:
        """
        Extract narration AND attention_cue parts (for TTS generation).
        Returns list of dicts with type and text.
        """
        parts = []
        for segment in parsed_script["segments"]:
            if segment["type"] in ["narration", "attention_cue"]:
                parts.append({
                    "type": segment["type"],
                    "text": segment["text"]
                })
        return parts
    
    def build_timeline_info(self, parsed_script: Dict, narration_audio_paths: List[str], 
                           video_clips: Dict) -> Dict:
        """
        Build timeline information for Director.
        
        Args:
            parsed_script: Parsed script with segments
            narration_audio_paths: List of audio file paths for each narration segment
            video_clips: Dict of video clips (intro, action, punchline)
        
        Returns:
            Timeline info with audio and video placement
        """
        timeline = {
            "segments": [],
            "total_duration": 0
        }
        
        current_time = 0
        narration_index = 0
        
        for segment in parsed_script["segments"]:
            if segment["type"] in ["narration", "attention_cue"]:
                # Get corresponding audio file
                if narration_index < len(narration_audio_paths):
                    audio_path = narration_audio_paths[narration_index]
                    
                    # Get audio duration
                    from moviepy.editor import AudioFileClip
                    try:
                        audio = AudioFileClip(audio_path)
                        duration = audio.duration
                        audio.close()
                    except:
                        duration = 5.0  # Fallback
                    
                    timeline["segments"].append({
                        "type": segment["type"],  # narration or attention_cue
                        "audio_path": audio_path,
                        "start": current_time,
                        "end": current_time + duration,
                        "duration": duration
                    })
                    
                    current_time += duration
                    narration_index += 1
            
            elif segment["type"] == "video_break":
                # Determine which video clip to use
                break_type = segment["break_type"]
                clip_key = break_type if break_type in video_clips else "action"
                
                if clip_key in video_clips:
                    clip_info = video_clips[clip_key]
                    clip_path = clip_info.get("path") if isinstance(clip_info, dict) else clip_info
                    
                    # Get video duration (use specified duration or actual clip duration)
                    from moviepy.editor import VideoFileClip
                    try:
                        vid = VideoFileClip(clip_path)
                        actual_duration = vid.duration
                        vid.close()
                        
                        # Use min of specified duration and actual duration
                        duration = min(segment["duration"], actual_duration)
                    except:
                        duration = segment["duration"]
                    
                    timeline["segments"].append({
                        "type": "video_break",
                        "video_path": clip_path,
                        "start": current_time,
                        "end": current_time + duration,
                        "duration": duration,
                        "break_type": break_type
                    })
                    
                    current_time += duration
        
        timeline["total_duration"] = current_time
        return timeline
