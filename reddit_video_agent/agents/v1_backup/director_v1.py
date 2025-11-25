import os
import json
import asyncio
from typing import Dict, Any, List
from moviepy.editor import VideoFileClip, AudioFileClip
import srt
import google.generativeai as genai
from .base_agent import BaseAgent
from ..core.config import Config
from .scraper_agent import ScraperAgent
from .scriptwriter_agent import ScriptwriterAgent
from .voiceover_agent import VoiceoverAgent
from .audio_agent import AudioAgent
from .visual_agent import VisualAgent
from .editor_agent import EditorAgent
from .clipper_agent import ClipperAgent
from .composer_agent import VideoComposerAgent

class Director(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = Config.get_gemini_key()
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(Config.DIRECTOR_MODEL)
        
        # Initialize sub-agents
        self.scraper = ScraperAgent(config)
        self.scriptwriter = ScriptwriterAgent(config)
        self.voiceover = VoiceoverAgent(config)
        self.audio = AudioAgent(config)
        self.visual = VisualAgent(config)
        self.editor = EditorAgent(config)
        self.clipper = ClipperAgent(config)
        self.composer = VideoComposerAgent(config)  # NEW!

    async def execute(self, url: str) -> str:
        """
        Orchestrates the entire video creation process with fine-tuned timeline.
        """
        print(f"🎬 Director: Starting production for {url}")
        
        try:
            # 1. Pre-Production: Gathering Raw Materials
            print("\n--- Phase 1: Pre-Production ---")
            raw_data = await self.scraper.execute(url)
            
            # 2. Scripting
            print("\n--- Phase 2: Scripting ---")
            script = await self.scriptwriter.execute(raw_data)
            print(f"📝 Script generated ({len(script)} chars)")
            
            # 3. Audio Production - SINGLE TTS for Full Script
            print("\n--- Phase 3: Audio Production (Single TTS) ---")
            
            # Parse script for video breaks
            from ..core.video_break_handler import VideoBreakHandler
            break_handler = VideoBreakHandler()
            parsed_script = break_handler.parse_script(script)
            
            if parsed_script["has_breaks"]:
                print(f"   📹 Detected {sum(1 for s in parsed_script['segments'] if s['type'] == 'video_break')} video break(s)")
                print("   Cleaning script for TTS (removing markers)...")
            else:
                print("   No video breaks detected - standard voiceover")
            
            # CLEAN script for TTS (remove VIDEO_BREAK markers)
            clean_script = self._clean_script_for_tts(script)
            print(f"   Original script: {len(script)} chars")
            print(f"   Clean script: {len(clean_script)} chars")
            
            # Generate ONE voiceover for CLEAN script (no markers!)
            voiceover_path = await self.voiceover.execute(clean_script)
            if not voiceover_path:
                raise Exception("Voiceover generation failed")
            
            # Generate captions from full audio
            audio_assets = await self.audio.execute(voiceover_path)
            captions_path = audio_assets["captions_path"]
            
            # Validate captions against full script
            print("   Validating captions against script...")
            from ..core.caption_validator import CaptionValidator
            validator = CaptionValidator(self.api_key)
            validated_captions_path = validator.validate_and_correct(captions_path, script)
            captions_path = validated_captions_path
            audio_assets["captions_path"] = validated_captions_path
            
            # 4. Visual Production (Clips & Images)
            print("\n--- Phase 4: Visual Production ---")
            
            # Prepare full context for VisualAgent
            full_context = {
                "title": raw_data.get("title"),
                "content": raw_data.get("content"),
                "comments": raw_data.get("comments")
            }
            
            # A. Video Clips (if video exists)
            video_clips = {}
            if raw_data.get("video_path"):
                video_clips = await self.clipper.execute(raw_data["video_path"])
            
            # B. AI Images
            generated_images = await self.visual.execute(
                script=script, 
                video_path=raw_data.get("video_path"),
                full_context=full_context
            )
            
            # 5. AUDIO-DRIVEN TIMELINE (Keyword-Based)
            print("\n--- Phase 5: Audio-Driven Timeline Generation ---")
            
            from ..core.timeline_builder import AudioDrivenTimelineBuilder
            
            builder = AudioDrivenTimelineBuilder()
            
            # Get audio duration
            if os.path.exists(voiceover_path):
                audio = AudioFileClip(voiceover_path)
                audio_duration = audio.duration
                audio.close()
            else:
                audio_duration = 60.0  # Fallback
            
            # Prepare assets dict for builder
            builder_assets = {
                "post_screenshot": raw_data.get("post_screenshot"),
                "comment_screenshots": raw_data.get("comment_screenshots", []),
                "images": generated_images,
                "video_clips": video_clips,
                "video_path": raw_data.get("video_path")
            }
            
            # Build timeline based on SRT keywords
            timeline = builder.build_timeline(
                srt_path=captions_path,
                assets=builder_assets,
                total_duration=audio_duration
            )
            
            # Add SFX markers
            timeline = builder.add_sfx_markers(timeline, [])  # Keywords not used yet, but method signature requires it
            
            # Save timeline for debugging
            timeline_path = os.path.join(Config.ASSETS_DIR, "timeline.json")
            with open(timeline_path, 'w') as f:
                json.dump(timeline, f, indent=2)
            print(f"   ✅ Timeline saved to {timeline_path}")
            
            # 6. Video Composition (Multi-Track Timeline)
            print("\n--- Phase 6: Video Composition ---")
            
            # Prepare assets for VideoComposerAgent
            composer_assets = {
                "script": script,
                "parsed_script": parsed_script,
                "voiceover_path": voiceover_path,
                "captions_path": captions_path,
                "video_clips": video_clips,
                "images": generated_images,
                "timeline": timeline  # Visual timeline from TimelineBuilder
            }
            
            # Build multi-track timeline
            composer_timeline = await self.composer.execute(composer_assets)
            
            # 7. Final Edit (Render from Timeline)
            print("\n--- Phase 7: Final Edit ---")
            
            # Prepare assets dict for Editor
            assets = {
                "video_path": raw_data.get("video_path"),
                "voiceover_path": voiceover_path,
                "captions_path": captions_path,
                "images": generated_images,
                "post_screenshot": raw_data.get("post_screenshot"),
                "comment_screenshots": raw_data.get("comment_screenshots", []),
                "video_clips": video_clips,
                "sound_effects": audio_assets.get("sound_effects", []),
                "timeline": timeline,  # Visual timeline
                "composer_timeline": composer_timeline,  # Multi-track timeline (NEW!)
                # Keep for backward compatibility
                "has_video_breaks": parsed_script["has_breaks"],
                "parsed_script": parsed_script
            }
            
            final_video = await self.editor.execute(assets)
            
            print(f"\n✅ Production Complete! Video: {final_video}")
            return final_video

        except Exception as e:
            print(f"❌ Director Error: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def _stage1_inventory_assets(
        self, raw_data: Dict, video_clips: Dict, images: List[str], 
        voiceover_path: str, captions_path: str
    ) -> Dict:
        """
        Stage 1: Create detailed inventory of all available assets with metadata.
        """
        inventory = {
            "video_clips": [],
            "screenshots": [],
            "ai_images": [],
            "audio": {},
            "caption_segments": []
        }
        
        # Video Clips
        for clip_type, clip_info in video_clips.items():
            # Handle new format: {path, description, duration}
            if isinstance(clip_info, dict):
                clip_path = clip_info.get("path")
                description = clip_info.get("description", f"{clip_type} clip")
                clip_duration = clip_info.get("duration", 0)
            else:
                # Old format fallback (just path string)
                clip_path = clip_info
                description = f"{clip_type} clip"
                clip_duration = 0
            
            if clip_path and os.path.exists(clip_path):
                try:
                    if clip_duration == 0:
                        # Get duration from file if not provided
                        clip = VideoFileClip(clip_path)
                        clip_duration = clip.duration
                        clip.close()
                    
                    inventory["video_clips"].append({
                        "name": clip_type,
                        "path": clip_path,
                        "duration": clip_duration,
                        "description": description
                    })
                except Exception as e:
                    print(f"   ⚠️ Failed to process clip {clip_type}: {e}")
        
        # Screenshots
        if raw_data.get("post_screenshot"):
            inventory["screenshots"].append({
                "name": "post_screenshot",
                "path": raw_data["post_screenshot"],
                "type": "post",
                "description": "Main Reddit post screenshot"
            })
        
        for i, comment_shot in enumerate(raw_data.get("comment_screenshots", [])):
            if os.path.exists(comment_shot):
                inventory["screenshots"].append({
                    "name": f"comment_thread_{i}",
                    "path": comment_shot,
                    "type": "comment",
                    "description": f"Comment thread {i+1}"
                })
        
        # AI Images
        for i, img_path in enumerate(images):
            if os.path.exists(img_path):
                inventory["ai_images"].append({
                    "name": f"ai_image_{i}",
                    "path": img_path,
                    "description": f"AI generated image {i+1}"
                })
        
        # Audio
        if os.path.exists(voiceover_path):
            audio = AudioFileClip(voiceover_path)
            # Account for 1.2x speed
            actual_duration = audio.duration / 1.2
            inventory["audio"] = {
                "path": voiceover_path,
                "original_duration": audio.duration,
                "playback_duration": actual_duration,
                "speed": 1.2
            }
            audio.close()
        
        # Caption Segments
        if os.path.exists(captions_path):
            with open(captions_path, 'r') as f:
                subs = list(srt.parse(f.read()))
                for sub in subs:
                    # Adjust for 1.2x speed
                    start = sub.start.total_seconds() / 1.2
                    end = sub.end.total_seconds() / 1.2
                    inventory["caption_segments"].append({
                        "text": sub.content,
                        "start": start,
                        "end": end,
                        "duration": end - start
                    })
        
        return inventory

    async def _stage2_analyze_narrative(self, script: str, captions_path: str) -> Dict:
        """
        Stage 2: Analyze script to identify narrative beats and key moments.
        """
        # Get caption text for context
        caption_text = ""
        if os.path.exists(captions_path):
            with open(captions_path, 'r') as f:
                subs = list(srt.parse(f.read()))
                caption_text = " ".join([sub.content for sub in subs])
        
        prompt = f"""
        Analyze this viral video script and identify key narrative beats.
        
        SCRIPT:
        {script}
        
        CAPTION TEXT (for timing reference):
        {caption_text}
        
        TASK:
        Identify 4-6 key narrative moments/beats in this script. For each beat, specify:
        1. Type: "hook", "setup", "action", "punchline", "comment_reaction", "outro"
        2. Description: What happens in this beat
        3. Keywords: Important words/phrases that appear in this beat
        4. Suggested_visual: What type of visual would work best (video_clip, screenshot, ai_image)
        
        Return JSON array:
        [
            {{
                "type": "hook",
                "description": "Opening statement to grab attention",
                "keywords": ["gila", "guys", "liat"],
                "suggested_visual": "post_screenshot"
            }},
            ...
        ]
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            beats = json.loads(response.text)
            return {"beats": beats}
        except Exception as e:
            print(f"   ⚠️ Narrative analysis failed: {e}")
            return {"beats": []}

    async def _stage3_generate_timeline(
        self, script: str, inventory: Dict, narrative: Dict, captions_path: str
    ) -> Dict:
        """
        Stage 3: Generate precise timeline mapping assets to exact timestamps.
        """
        # Prepare comprehensive context for Gemini
        context = f"""
        SCRIPT:
        {script}
        
        AVAILABLE ASSETS:
        
        Video Clips ({len(inventory['video_clips'])}):
        {json.dumps(inventory['video_clips'], indent=2)}
        
        Screenshots ({len(inventory['screenshots'])}):
        {json.dumps(inventory['screenshots'], indent=2)}
        
        AI Images ({len(inventory['ai_images'])}):
        {json.dumps(inventory['ai_images'], indent=2)}
        
        Caption Segments ({len(inventory['caption_segments'])}):
        {json.dumps(inventory['caption_segments'][:10], indent=2)}  # First 10 for brevity
        
        Narrative Beats:
        {json.dumps(narrative['beats'], indent=2)}
        
        Audio Duration: {inventory['audio']['playback_duration']:.2f}s (at 1.2x speed)
        """
        
        prompt = f"""
        You are a professional video editor. Create a PRECISE timeline for this viral short video.
        
        {context}
        
        RULES:
        1. Post screenshot should appear ONLY in intro (0-5s)
        2. Video clips should be used at appropriate narrative moments (NOT just looped background)
        3. Comment screenshots should appear when narrator mentions comments
        4. AI images should fill gaps and emphasize key points
        5. NO overlapping visual elements (except captions which are always on top)
        6. Each asset must have exact start/end times
        
        Return JSON timeline with layers:
        {{
            "total_duration": {inventory['audio']['playback_duration']},
            "layers": [
                {{
                    "type": "screenshot",
                    "asset_name": "post_screenshot",
                    "asset_path": "...",
                    "start": 0.0,
                    "end": 5.0,
                    "position": "center_top",
                    "reason": "Intro context"
                }},
                {{
                    "type": "video_clip",
                    "asset_name": "clip_intro",
                    "asset_path": "...",
                    "start": 0.0,
                    "end": 3.2,
                    "position": "center",
                    "reason": "Matches opening narration"
                }},
                ...
            ]
        }}
        
        IMPORTANT: Use actual asset names and paths from the inventory above.
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            timeline = json.loads(response.text)
            return timeline
        except Exception as e:
            print(f"   ⚠️ Timeline generation failed: {e}")
            # Fallback: Simple timeline
            return self._create_fallback_timeline(inventory)

    async def _stage4_validate_timeline(self, timeline: Dict, inventory: Dict) -> Dict:
        """
        Stage 4: Validate timeline for conflicts and optimize.
        """
        if not timeline.get("layers"):
            return timeline
        
        validated_layers = []
        total_duration = timeline.get("total_duration", 15.0)
        
        # Sort layers by start time
        layers = sorted(timeline["layers"], key=lambda x: x.get("start", 0))
        
        # Check for conflicts and gaps
        for i, layer in enumerate(layers):
            # Validate times
            start = max(0, float(layer.get("start", 0)))
            end = min(total_duration, float(layer.get("end", start + 2)))
            
            if end <= start:
                continue  # Skip invalid layers
            
            # Validate asset exists
            asset_path = layer.get("asset_path")
            if asset_path and not os.path.exists(asset_path):
                print(f"   ⚠️ Asset not found: {asset_path}, skipping layer")
                continue
            
            layer["start"] = start
            layer["end"] = end
            validated_layers.append(layer)
        
        timeline["layers"] = validated_layers
        return timeline

    def _create_fallback_timeline(self, inventory: Dict) -> Dict:
        """
        Create a simple fallback timeline if Gemini fails.
        """
        duration = inventory["audio"]["playback_duration"]
        layers = []
        
        # Post screenshot intro
        if inventory["screenshots"]:
            post_shot = next((s for s in inventory["screenshots"] if s["type"] == "post"), None)
            if post_shot:
                layers.append({
                    "type": "screenshot",
                    "asset_name": post_shot["name"],
                    "asset_path": post_shot["path"],
                    "start": 0.0,
                    "end": 5.0,
                    "position": "center_top",
                    "reason": "Intro"
                })
        
        # Distribute AI images
        if inventory["ai_images"]:
            interval = duration / (len(inventory["ai_images"]) + 1)
            for i, img in enumerate(inventory["ai_images"]):
                layers.append({
                    "type": "ai_image",
                    "asset_name": img["name"],
                    "asset_path": img["path"],
                    "start": (i + 1) * interval,
                    "end": (i + 1) * interval + 2.0,
                    "position": "center",
                    "reason": "Visual emphasis"
                })
        
        return {"total_duration": duration, "layers": layers}

    def _clean_script_for_tts(self, script: str) -> str:
        """
        Remove VIDEO_BREAK markers from script for clean TTS generation.
        
        Example:
        Input:  "Judulnya Float... [VIDEO_BREAK: duration=15s, clip=action] Musuhnya udah..."
        Output: "Judulnya Float... Musuhnya udah..."
        """
        import re
        
        # Remove [VIDEO_BREAK: ...] markers
        clean = re.sub(r'\[VIDEO_BREAK:.*?\]', '', script)
        
        # Clean up multiple spaces
        clean = re.sub(r'\s+', ' ', clean)
        
        # Clean up spaces around punctuation
        clean = re.sub(r'\s+([.,!?])', r'\1', clean)
        
        return clean.strip()
