"""
Audio-Driven Timeline Builder
Builds precise timeline based on SRT word timestamps and keyword mapping.
"""

import os
import re
import srt
from typing import Dict, List, Any
from datetime import timedelta

class AudioDrivenTimelineBuilder:
    def __init__(self):
        # Keyword to asset type mapping
        self.keyword_map = {
            # Weapon/Action keywords
            r'bokken|pedang|katana|sword': 'sword_visual',
            r'potong|slice|iris|cut|tebas': 'action_clip',
            
            # Comment keywords
            r'komentar|netizen|comment|kata|bilang': 'comment_screenshot',
            
            # Reaction keywords
            r'gila|wow|gokil|sumpah|anjay|keren': 'reaction_image',
            
            # Physics/Technical
            r'fisika|physics|geometri|geometry|sudut|angle': 'technical_image',
            
            # Intro/Outro
            r'^(gila|wow|halo|guys|kalian)': 'intro_hook',  # First words
            r'(subscribe|like|comment|jangan lupa)': 'outro_cta',  # CTA words
        }
    
    def parse_srt_to_words(self, srt_path: str) -> List[Dict]:
        """
        Parse SRT file to get word-level timestamps.
        Returns: [{"word": "gila", "start": 0.5, "end": 0.8}, ...]
        """
        words = []
        
        with open(srt_path, 'r', encoding='utf-8') as f:
            srt_content = f.read()
        
        subtitles = list(srt.parse(srt_content))
        
        for sub in subtitles:
            # Split subtitle into words
            text_words = sub.content.split()
            word_count = len(text_words)
            
            if word_count == 0:
                continue
            
            # Calculate time per word
            sub_duration = (sub.end - sub.start).total_seconds()
            time_per_word = sub_duration / word_count
            
            for i, word in enumerate(text_words):
                start_time = sub.start.total_seconds() + (i * time_per_word)
                end_time = start_time + time_per_word
                
                words.append({
                    "word": word.lower(),
                    "original": word,
                    "start": start_time,
                    "end": end_time
                })
        
        return words
    
    def match_keywords(self, words: List[Dict]) -> List[Dict]:
        """
        Match keywords in words to asset types.
        Returns: [{"keyword": "bokken", "asset_type": "sword_visual", "timestamp": 5.2}, ...]
        """
        matches = []
        
        for word_info in words:
            word = word_info["word"]
            
            for pattern, asset_type in self.keyword_map.items():
                if re.search(pattern, word, re.IGNORECASE):
                    matches.append({
                        "keyword": word,
                        "asset_type": asset_type,
                        "timestamp": word_info["start"],
                        "word_info": word_info
                    })
        
        return matches
    
    def build_timeline(
        self, 
        srt_path: str, 
        assets: Dict[str, Any],
        total_duration: float
    ) -> Dict:
        """
        Build timeline based on audio timestamps and available assets.
        """
        print("🎯 Building Audio-Driven Timeline...")
        
        # Parse SRT
        words = self.parse_srt_to_words(srt_path)
        print(f"   Parsed {len(words)} words from SRT")
        
        # Match keywords
        keyword_matches = self.match_keywords(words)
        print(f"   Found {len(keyword_matches)} keyword matches")
        
        # Build timeline layers
        timeline = {
            "total_duration": total_duration,
            "layers": []
        }
        
        # Rule 1: Post screenshot ALWAYS at intro (0-5s)
        if assets.get("post_screenshot"):
            timeline["layers"].append({
                "type": "screenshot",
                "asset_name": "post_screenshot",
                "asset_path": assets["post_screenshot"],
                "start": 0.0,
                "end": 5.0,
                "position": "center_top",
                "reason": "Intro context (fixed rule)"
            })
        
        # Rule 2: Map keyword matches to assets
        used_assets = set()
        
        for match in keyword_matches:
            asset_type = match["asset_type"]
            timestamp = match["timestamp"]
            
            # Determine which asset to use
            asset_path = None
            asset_name = None
            
            if asset_type == "sword_visual":
                # Use AI image of sword
                sword_images = [img for img in assets.get("images", []) if "bokken" in img.lower() or "sword" in img.lower()]
                if sword_images and sword_images[0] not in used_assets:
                    asset_path = sword_images[0]
                    asset_name = os.path.basename(asset_path)
                    used_assets.add(asset_path)
            
            elif asset_type == "action_clip":
                # Use action video clip
                if "action" in assets.get("video_clips", {}):
                    clip_info = assets["video_clips"]["action"]
                    asset_path = clip_info.get("path") if isinstance(clip_info, dict) else clip_info
                    asset_name = "clip_action"
            
            elif asset_type == "comment_screenshot":
                # Use next available comment screenshot
                comment_shots = assets.get("comment_screenshots", [])
                available = [c for c in comment_shots if c not in used_assets]
                if available:
                    asset_path = available[0]
                    asset_name = os.path.basename(asset_path)
                    used_assets.add(asset_path)
            
            elif asset_type == "reaction_image":
                # Use shocked face image
                reaction_images = [img for img in assets.get("images", []) if "shock" in img.lower() or "face" in img.lower()]
                if reaction_images and reaction_images[0] not in used_assets:
                    asset_path = reaction_images[0]
                    asset_name = os.path.basename(asset_path)
                    used_assets.add(asset_path)
            
            elif asset_type == "technical_image":
                # Use technical/physics image
                tech_images = [img for img in assets.get("images", []) if img not in used_assets]
                if tech_images:
                    asset_path = tech_images[0]
                    asset_name = os.path.basename(asset_path)
                    used_assets.add(asset_path)
            
            # Add to timeline if asset found
            if asset_path:
                # Place asset 0.5s BEFORE keyword is spoken (anticipation)
                start = max(5.0, timestamp - 0.5)  # Don't overlap with intro
                end = min(total_duration, start + 4.0)  # Show for 4 seconds
                
                # Determine layer type
                if "clip" in asset_name:
                    layer_type = "video_clip"
                elif "comment" in asset_name or "screenshot" in asset_name:
                    layer_type = "screenshot"
                else:
                    layer_type = "ai_image"
                
                # INTELLIGENT TRANSITION SELECTION based on keyword context
                transition = self._select_transition(match['keyword'], asset_type)
                
                timeline["layers"].append({
                    "type": layer_type,
                    "asset_name": asset_name,
                    "asset_path": asset_path,
                    "start": start,
                    "end": end,
                    "position": "center",
                    "transition": transition,  # Director's choice!
                    "reason": f"Triggered by keyword '{match['keyword']}' at {timestamp:.1f}s"
                })
        
        # Rule 3: Fill remaining gaps with unused assets
        timeline = self._fill_gaps(timeline, assets, used_assets)
        
        # Rule 4: Validate and resolve conflicts
        timeline = self._validate_timeline(timeline)
        
        print(f"   ✅ Built timeline with {len(timeline['layers'])} layers")
        return timeline
    
    def add_sfx_markers(self, timeline: Dict, keywords: List[Dict]):
        """
        Add SFX markers to timeline layers.
        """
        print("   🔊 Adding SFX markers...")
        
        # 1. Transition SFX (Whoosh) for every image
        for layer in timeline["layers"]:
            if layer["type"] == "ai_image":
                layer["sfx"] = "whoosh"
                
        # 2. Keyword-based SFX
        # Map keywords to SFX types
        sfx_map = {
            "wow": "impact",
            "gila": "impact",
            "boom": "impact",
            "lucu": "funny",
            "kocak": "funny",
            "ngakak": "funny",
            "pop": "pop",
            "muncul": "pop"
        }
        
        # Check keywords against map
        # This is a simplified implementation. Ideally we'd check timestamps.
        # For now, we'll just add some random SFX for variety if keywords match
        
        return timeline
    
    def _fill_gaps(self, timeline: Dict, assets: Dict, used_assets: set) -> Dict:
        """Fill gaps in timeline with unused assets."""
        layers = timeline["layers"]
        total_duration = timeline["total_duration"]
        
        # Sort layers by start time
        layers.sort(key=lambda x: x["start"])
        
        # Find gaps
        gaps = []
        current_time = 5.0  # After intro
        
        for layer in layers:
            if layer["start"] > current_time + 2.0:  # Gap of at least 2s
                gaps.append((current_time, layer["start"]))
            current_time = max(current_time, layer["end"])
        
        # Add final gap if exists
        if current_time < total_duration - 2.0:
            gaps.append((current_time, total_duration))
        
        # Fill gaps with unused images
        unused_images = [img for img in assets.get("images", []) if img not in used_assets]
        
        for i, (gap_start, gap_end) in enumerate(gaps):
            if i < len(unused_images):
                gap_duration = gap_end - gap_start
                display_duration = min(gap_duration, 3.0)
                
                layers.append({
                    "type": "ai_image",
                    "asset_name": os.path.basename(unused_images[i]),
                    "asset_path": unused_images[i],
                    "start": gap_start,
                    "end": gap_start + display_duration,
                    "position": "center",
                    "reason": f"Fill gap {gap_start:.1f}s-{gap_end:.1f}s"
                })
        
        timeline["layers"] = layers
        return timeline
    
    def _validate_timeline(self, timeline: Dict) -> Dict:
        """Validate timeline and resolve conflicts."""
        layers = timeline["layers"]
        
        # Sort by start time
        layers.sort(key=lambda x: x["start"])
        
        # Remove overlaps (keep first layer, trim second)
        validated = []
        
        for i, layer in enumerate(layers):
            if i == 0:
                validated.append(layer)
                continue
            
            prev_layer = validated[-1]
            
            # Check overlap
            if layer["start"] < prev_layer["end"]:
                # Trim current layer to start after previous
                layer["start"] = prev_layer["end"]
                
                # Skip if too short
                if layer["end"] - layer["start"] < 1.0:
                    continue
            
            validated.append(layer)
        
        timeline["layers"] = validated
        return timeline
    
    def _select_transition(self, keyword: str, asset_type: str) -> str:
        """
        Intelligently select transition based on keyword context.
        
        Transition mapping:
        - shake: Action, impact, surprise (gila, wow, anjay)
        - spin: Extreme surprise, mind-blown (sumpah, gokil)
        - wobble: Funny, awkward, relatable (toxic trait, gagal)
        - zoom_in: Focus, emphasis (fisika, geometri, teknik)
        - popup: Sudden appearance (komentar, netizen)
        - bounce_in: Playful, energetic (default for most)
        - fade_in: Calm, informative (default fallback)
        """
        keyword_lower = keyword.lower()
        
        # Action/Impact keywords -> shake
        if any(word in keyword_lower for word in ['potong', 'iris', 'tebas', 'slice', 'cut']):
            return 'shake'
        
        # Extreme surprise -> spin
        if any(word in keyword_lower for word in ['gila', 'sumpah', 'gokil', 'anjay', 'wow']):
            return 'spin'
        
        # Funny/awkward -> wobble
        if any(word in keyword_lower for word in ['toxic', 'gagal', 'fail', 'awkward', 'lucu']):
            return 'wobble'
        
        # Technical/focus -> zoom_in
        if any(word in keyword_lower for word in ['fisika', 'geometri', 'physics', 'geometry', 'sudut', 'angle']):
            return 'zoom_in'
        
        # Comments/social -> popup
        if any(word in keyword_lower for word in ['komentar', 'netizen', 'comment', 'kata', 'bilang']):
            return 'popup'
        
        # Default: bounce_in (energetic and safe)
        return 'bounce_in'
