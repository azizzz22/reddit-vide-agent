import os
import re
import subprocess
from typing import Dict, Any, List, Tuple
from moviepy.editor import (VideoFileClip, AudioFileClip, ImageClip, TextClip, 
                            CompositeVideoClip, CompositeAudioClip, concatenate_videoclips, ColorClip)
from moviepy.video.fx.all import fadein, fadeout, resize
import srt
from datetime import timedelta
from .base_agent import BaseAgent
from ..core.config import Config

class EditorAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.assets_dir = Config.ASSETS_DIR
        self.output_dir = Config.OUTPUT_DIR
        self.resolution = (720, 1280)  # 9:16 vertical (720p for testing)
        self.fps = 24

    async def execute(self, assets: Dict[str, Any]) -> str:
        """
        Composes and renders the final video with advanced effects.
        """
        print("EditorAgent: Composing video...")
        
        try:
            # CHECK FOR V2 PROFESSIONAL TIMELINE FIRST (NEWEST METHOD)
            if assets.get("professional_timeline"):
                print("   🎬 V2 PROFESSIONAL TIMELINE MODE: Rendering with beat-synchronized composition")
                return await self._render_from_professional_timeline(assets)
            
            # CHECK FOR V1 COMPOSER TIMELINE (OLD METHOD)
            elif assets.get("composer_timeline"):
                print("   🎬 V1 MULTI-TRACK TIMELINE MODE: Rendering from composer")
                return await self._render_from_timeline(assets)
            
            # CHECK FOR VIDEO BREAKS (LEGACY METHOD - FALLBACK)
            elif assets.get("has_video_breaks") and assets.get("video_break_timeline"):
                print("   🎬 VIDEO BREAK MODE: Stitching narration + original video")
                return await self._compose_with_video_breaks(assets)
            
            # STANDARD MODE (no video breaks)
            # 1. Get audio duration and speed it up to 1.2x
            audio_path = assets.get("voiceover_path")
            if not audio_path or not os.path.exists(audio_path):
                print("❌ No voiceover audio found!")
                return None
            
            # Load audio and speed up to 1.2x using ffmpeg
            import subprocess
            temp_audio_path = os.path.join(os.path.dirname(audio_path), "voiceover_1.2x.mp3")
            
            # Use ffmpeg atempo filter
            cmd = [
                'ffmpeg', '-y', '-i', audio_path,
                '-filter:a', 'atempo=1.2',
                '-vn', temp_audio_path
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True)
                audio = AudioFileClip(temp_audio_path)
                duration = audio.duration
                print(f"   Audio duration (1.2x speed): {duration:.2f}s")
            except Exception as e:
                print(f"   ⚠️ Audio speed adjustment failed: {e}, using original")
                audio = AudioFileClip(audio_path)
                duration = audio.duration
                print(f"   Audio duration (original speed): {duration:.2f}s")
            
            # 2. Check if we have a timeline from Director
            timeline = assets.get("timeline")
            
            if timeline and timeline.get("layers"):
                # Use Director's precise timeline
                print("   Using Director's timeline for composition")
                background_clips = self._create_background_from_timeline(timeline, assets, duration)
                visual_layers = self._create_layers_from_timeline(timeline, duration)
            else:
                # Fallback to simple distribution
                print("   Using fallback distribution (no timeline)")
                background_clips = self._create_background_layer(assets, duration)
                visual_layers = []
                
                # Add images and screenshots with simple distribution
                images = assets.get("images", [])
                if images:
                    visual_layers.extend(self._create_dynamic_image_overlays(images, captions_path, duration))
                
                comment_screenshots = assets.get("comment_screenshots", [])
                if comment_screenshots:
                    visual_layers.extend(self._create_comment_overlays(comment_screenshots, duration))
            
            # 3. Parse captions (SRT) for per-word display with BOUNCE effect
            captions_path = assets.get("captions_path")
            caption_clips = []
            if captions_path and os.path.exists(captions_path):
                caption_clips = self._create_per_word_captions(captions_path, duration)
                print(f"   Created {len(caption_clips)} caption clips")
            
            # 6. Composite all layers
            # Order: Background -> Visual Layers (from timeline) -> Captions
            all_clips = background_clips + visual_layers + caption_clips
            
            # Set audio
            final_video = CompositeVideoClip(all_clips, size=self.resolution).set_audio(audio)
            final_video = final_video.set_duration(duration)
            
            # 7. Render
            output_filename = "final_video.mp4"
            output_path = os.path.join(self.output_dir, output_filename)
            
            print(f"   Rendering to {output_path}...")
            final_video.write_videofile(
                output_path,
                fps=self.fps,
                codec="libx264",
                audio_codec="aac",
                threads=4,
                preset="medium",
                bitrate="2500k" # Increased bitrate
            )
            
            print(f"✅ Video rendered successfully!")
            return output_path

        except Exception as e:
            print(f"❌ Error composing video: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _create_background_layer(self, assets: Dict, duration: float) -> List[VideoFileClip]:
        """
        Creates the background stack.
        Strategy:
        1. Base: Solid Color or Blurred Video
        2. Post Screenshot: Centered (Top half)
        3. Video Playback: Overlayed ON TOP of the screenshot's video area (if applicable)
        """
        clips = []
        
        video_path = assets.get("video_path")
        post_screenshot = assets.get("post_screenshot")
        
        # 1. Base Background
        if video_path and os.path.exists(video_path):
            bg = VideoFileClip(video_path)
            if bg.duration < duration:
                bg = bg.loop(duration=duration)
            else:
                bg = bg.subclip(0, duration)
            
            # Blur and darken for background
            bg = bg.resize(height=self.resolution[1])
            bg = bg.crop(x1=bg.w/2 - self.resolution[0]/2, width=self.resolution[0])
            # Note: Blur is expensive in MoviePy, let's just darken it
            bg = bg.fl_image(lambda image: 0.3 * image) # Darken
            clips.append(bg)
        else:
            bg = ColorClip(size=self.resolution, color=(20, 20, 30), duration=duration)
            clips.append(bg)
            
        # 2. Post Screenshot (Intro Only - 5 seconds)
        if post_screenshot and os.path.exists(post_screenshot):
            shot = ImageClip(post_screenshot)
            shot = shot.resize(width=int(self.resolution[0] * 0.9))
            shot = shot.set_position(('center', 150)) # Top area
            shot = shot.set_start(0)
            shot = shot.set_duration(5.0) # Only show for intro
            shot = shot.crossfadeout(0.5) # Fade out at end
            
            clips.append(shot)
            
            # 3. Video Overlay (Inside Screenshot)
            if video_path and os.path.exists(video_path):
                # We need to position the video roughly where the placeholder is.
                # Heuristic: Below the title.
                # Screenshot is at y=150. Title is usually top 100px of screenshot.
                # Let's place video at y=150 + 100 (relative to screen) = 250?
                # And resize it to fit width of screenshot.
                
                vid = VideoFileClip(video_path)
                # Loop if needed
                if vid.duration < duration:
                    vid = vid.loop(duration=duration)
                
                # Resize to fit inside screenshot width (with padding)
                target_width = int(self.resolution[0] * 0.9 * 0.95) # 95% of screenshot width
                vid = vid.resize(width=target_width)
                
                # Position: Center horizontally, and slightly below the top of screenshot
                # This is a guess. A better way is to use the ClipperAgent to detect the box, 
                # but for now manual heuristic.
                vid_y = 150 + 120 # Header offset
                vid = vid.set_position(('center', vid_y))
                vid = vid.set_start(0)
                vid = vid.set_duration(duration) # Play throughout
                
                clips.append(vid)
                
        elif video_path and os.path.exists(video_path):
            # If no screenshot, just show video centered
            vid = VideoFileClip(video_path)
            if vid.duration < duration:
                vid = vid.loop(duration=duration)
            vid = vid.resize(width=self.resolution[0])
            vid = vid.set_position('center')
            vid = vid.set_start(0)
            vid = vid.set_duration(duration)
            clips.append(vid)
            
        return clips

    def _create_per_word_captions(self, srt_path: str, duration: float) -> List[TextClip]:
        """Create per-word caption clips with POPUP BOUNCE animation"""
        caption_clips = []
        
        try:
            with open(srt_path, 'r', encoding='utf-8') as f:
                srt_content = f.read()
            
            subtitles = list(srt.parse(srt_content))
            
            for sub in subtitles:
                words = sub.content.split()
                word_count = len(words)
                if word_count == 0: continue
                
                sub_duration = (sub.end - sub.start).total_seconds()
                time_per_word = sub_duration / word_count
                
                for i, word in enumerate(words):
                    start_time = sub.start.total_seconds() + (i * time_per_word)
                    
                    # Create text clip with TikTok-style font
                    # Try Impact first, fallback to Arial-Bold
                    try:
                        txt_clip = TextClip(
                            word,
                            fontsize=80, # Larger for impact
                            color='yellow', # High visibility
                            font='Impact',
                            stroke_color='black',
                            stroke_width=5,
                            method='caption',
                            size=(self.resolution[0] - 100, None)
                        )
                    except:
                        # Fallback if Impact not available
                        txt_clip = TextClip(
                            word,
                            fontsize=80,
                            color='yellow',
                            font='Arial-Bold',
                            stroke_color='black',
                            stroke_width=5,
                            method='caption',
                            size=(self.resolution[0] - 100, None)
                        )
                    
                    txt_clip = txt_clip.set_position(('center', self.resolution[1] * 0.70))
                    txt_clip = txt_clip.set_start(start_time)
                    txt_clip = txt_clip.set_duration(time_per_word)
                    
                    # Simple fade (bounce disabled due to OpenCV compatibility)
                    txt_clip = txt_clip.crossfadein(0.05).crossfadeout(0.05)
                    
                    caption_clips.append(txt_clip)
            
        except Exception as e:
            print(f"   ⚠️  Error creating captions: {e}")
        
        return caption_clips

    def _create_dynamic_image_overlays(self, images: List[str], srt_path: str, duration: float) -> List[ImageClip]:
        """Create image overlays with ZOOM BOUNCE animation"""
        image_clips = []
        if not images: return []
        
        # Simple distribution for Phase 1 (Director should handle this in Phase 2)
        segment_duration = duration / (len(images) + 1)
        
        for i, img_path in enumerate(images):
            if not os.path.exists(img_path): continue
            
            start_time = (i + 1) * segment_duration
            img_duration = 2.0 # Show for 2 seconds
            
            img_clip = ImageClip(img_path).resize(height=400)
            img_clip = img_clip.set_position(('center', 'center'))
            img_clip = img_clip.set_start(start_time)
            img_clip = img_clip.set_duration(img_duration)
            
            # ZOOM BOUNCE
            # We can use `resize` here as images are fewer than caption words
            def bounce_resize(t):
                if t < 0.3:
                    return 0.1 + 0.9 * (t / 0.3) # 0.1 -> 1.0 (Zoom in)
                return 1.0
                
            img_clip = img_clip.resize(bounce_resize)
            
            image_clips.append(img_clip)
            
        return image_clips

    def _create_comment_overlays(self, screenshots: List[str], duration: float) -> List[ImageClip]:
        """Show comment screenshots"""
        clips = []
        if not screenshots: return []
        
        # Show them in the last 3rd of the video?
        start_base = duration * 0.6
        interval = (duration - start_base) / len(screenshots)
        
        for i, shot_path in enumerate(screenshots):
            if not os.path.exists(shot_path): continue
            
            shot = ImageClip(shot_path).resize(width=int(self.resolution[0] * 0.85))
            shot = shot.set_position(('center', 'bottom')) # Bottom half
            
            start = start_base + i * interval
            shot = shot.set_start(start)
            shot = shot.set_duration(interval - 0.5)
            
            # Slide in from bottom
            def slide_in(t):
                h = self.resolution[1]
                if t < 0.5:
                    y = h - (h * 0.4) * (t / 0.5) # Slide up
                    return ('center', int(y))
                return ('center', int(h * 0.6)) # Stay
                
            # shot = shot.set_position(slide_in) # Complex positioning
            # Simple fade for now
            shot = shot.crossfadein(0.3)
            
            clips.append(shot)
            
        return clips

    def _create_background_from_timeline(self, timeline: Dict, assets: Dict, duration: float) -> List:
        """
        Create background layer using timeline information.
        Strategy: Always use looped main video as base, then overlay specific clips at designated times.
        """
        clips = []
        video_path = assets.get("video_path")
        video_clips_dict = assets.get("video_clips", {})
        
        # 1. ALWAYS create base looped video background (no blank spaces)
        if video_path and os.path.exists(video_path):
            bg = VideoFileClip(video_path)
            
            # Loop to fill entire duration
            if bg.duration < duration:
                # Calculate how many loops needed
                loops_needed = int(duration / bg.duration) + 1
                bg = bg.loop(n=loops_needed)
            
            # Trim to exact duration
            bg = bg.subclip(0, duration)
            
            # Resize to fit screen
            bg = bg.resize(height=self.resolution[1])
            if bg.w > self.resolution[0]:
                bg = bg.crop(x1=bg.w/2 - self.resolution[0]/2, width=self.resolution[0])
            
            # Darken slightly so overlays stand out
            bg = bg.fl_image(lambda image: 0.6 * image)
            
            clips.append(bg)
            print(f"   ✅ Added looped background video (full duration)")
        else:
            # Fallback to solid color if no video
            bg = ColorClip(size=self.resolution, color=(20, 20, 30), duration=duration)
            clips.append(bg)
        
        # 2. Overlay specific video clips at designated times (from timeline)
        video_layers = [l for l in timeline.get("layers", []) if l.get("type") == "video_clip"]
        
        for layer in video_layers:
            clip_name = layer.get("asset_name")
            clip_path = layer.get("asset_path")
            start = layer.get("start", 0)
            end = layer.get("end", start + 2)
            
            if clip_path and os.path.exists(clip_path):
                try:
                    vid = VideoFileClip(clip_path)
                    
                    # Resize to full screen
                    vid = vid.resize(width=self.resolution[0])
                    vid = vid.set_position('center')
                    vid = vid.set_start(start)
                    vid = vid.set_duration(min(end - start, vid.duration))
                    
                    # Add fade transitions
                    vid = vid.crossfadein(0.3).crossfadeout(0.3)
                    
                    clips.append(vid)
                    print(f"   ✅ Overlaid video clip '{clip_name}' at {start:.1f}s-{end:.1f}s")
                except Exception as e:
                    print(f"   ⚠️ Failed to load clip {clip_name}: {e}")
        
        return clips

    def _create_layers_from_timeline(self, timeline: Dict, duration: float) -> List:
        """
        Create all visual layers (screenshots, images) from timeline.
        """
        layers = []
        
        for layer_spec in timeline.get("layers", []):
            layer_type = layer_spec.get("type")
            asset_path = layer_spec.get("asset_path")
            start = layer_spec.get("start", 0)
            end = layer_spec.get("end", start + 2)
            position = layer_spec.get("position", "center")
            asset_name = layer_spec.get("asset_name", "")
            
            if not asset_path or not os.path.exists(asset_path):
                continue
            
            try:
                if layer_type == "screenshot":
                    # Screenshot layer
                    clip = ImageClip(asset_path)
                    
                    # Special handling for post_screenshot (it's now a TRANSPARENT FRAME!)
                    if "post_screenshot" in asset_name:
                        # This is a frame with transparent video player area
                        # We need to place video thumbnail UNDERNEATH it
                        
                        # Get video path for thumbnail
                        video_path = None
                        if "video_path" in dir(self) or hasattr(self, 'current_video_path'):
                            video_path = getattr(self, 'current_video_path', None)
                        
                        # Try to find video in assets
                        if not video_path:
                            import glob
                            video_files = glob.glob(os.path.join(os.path.dirname(asset_path), "video_*.mp4"))
                            if video_files:
                                video_path = video_files[0]
                        
                        if video_path and os.path.exists(video_path):
                            # Extract thumbnail from video
                            from moviepy.editor import VideoFileClip
                            try:
                                vid = VideoFileClip(video_path)
                                frame_time = min(1.0, vid.duration / 2)
                                
                                # Create thumbnail clip
                                thumbnail_clip = vid.to_ImageClip(t=frame_time)
                                
                                # Resize thumbnail to match frame size
                                # Read frame info if available
                                frame_info_path = asset_path.replace('.png', '_frame_info.txt')
                                if os.path.exists(frame_info_path):
                                    with open(frame_info_path, 'r') as f:
                                        coords = f.read().strip().split(',')
                                        player_left, player_top, player_right, player_bottom = map(int, coords)
                                        player_width = player_right - player_left
                                        player_height = player_bottom - player_top
                                        
                                        # Resize thumbnail to fit player area
                                        thumbnail_clip = thumbnail_clip.resize((player_width, player_height))
                                        thumbnail_clip = thumbnail_clip.set_position((player_left, player_top))
                                else:
                                    # Fallback: resize to 85% of frame width
                                    thumbnail_clip = thumbnail_clip.resize(width=int(self.resolution[0] * 0.85))
                                    thumbnail_clip = thumbnail_clip.set_position('center')
                                
                                thumbnail_clip = thumbnail_clip.set_start(start)
                                thumbnail_clip = thumbnail_clip.set_duration(end - start)
                                
                                # Add thumbnail to layers FIRST (bottom layer)
                                layers.insert(0, thumbnail_clip)
                                print(f"   ✅ Added video thumbnail underneath frame")
                                
                                vid.close()
                            except Exception as e:
                                print(f"   ⚠️ Could not extract thumbnail: {e}")
                        
                        # Now add the frame on top
                        clip = clip.resize(width=int(self.resolution[0] * 0.95))
                        clip = clip.set_position(('center', 50))
                        
                    else:
                        # Comment screenshots - normal overlay
                        clip = clip.resize(width=int(self.resolution[0] * 0.9))
                        
                        # Position mapping
                        if position == "center_top":
                            clip = clip.set_position(('center', 150))
                        elif position == "bottom":
                            clip = clip.set_position(('center', 'bottom'))
                        else:
                            clip = clip.set_position('center')
                    
                    clip = clip.set_start(start)
                    clip = clip.set_duration(end - start)
                    clip = clip.crossfadein(0.3).crossfadeout(0.3)
                    layers.append(clip)
                    print(f"   Added screenshot at {start:.1f}s-{end:.1f}s")
                
                elif layer_type == "ai_image":
                    # AI Image layer with CONTEXT-AWARE TRANSITIONS
                    clip = ImageClip(asset_path)
                    
                    img_duration = end - start
                    
                    # Get transition from timeline (Director's choice) or random
                    transition_type = layer_spec.get("transition", None)
                    
                    if not transition_type:
                        # Fallback to random if Director didn't specify
                        import random
                        transition_type = random.choice([
                            "zoom_in", "popup", "bounce_in", "fade_in",
                            "shake", "spin", "wobble"
                        ])
                    
                    # Resize first to avoid issues
                    clip = clip.resize(height=400)
                    clip = clip.set_position('center')
                    
                    # Apply transition based on type
                    if transition_type == "zoom_in":
                        # Quick zoom in (0.3s)
                        def zoom_resize(t):
                            if t < 0.3:
                                return 0.3 + 0.7 * (t / 0.3)
                            return 1.0
                        clip = clip.resize(zoom_resize)
                    
                    elif transition_type == "popup":
                        # Pop from small to normal (0.2s)
                        def popup_resize(t):
                            if t < 0.2:
                                return 0.5 + 0.5 * (t / 0.2)
                            return 1.0
                        clip = clip.resize(popup_resize)
                    
                    elif transition_type == "bounce_in":
                        # Bounce effect (0.25s)
                        def bounce_resize(t):
                            if t < 0.15:
                                return t / 0.15 * 1.2
                            elif t < 0.25:
                                return 1.2 - 0.2 * ((t - 0.15) / 0.1)
                            return 1.0
                        clip = clip.resize(bounce_resize)
                    
                    elif transition_type == "shake":
                        # Shake effect (0.3s) - rapid position changes
                        import math
                        def shake_pos(t):
                            if t < 0.3:
                                # Shake with decreasing amplitude
                                amplitude = 20 * (1 - t / 0.3)
                                offset_x = int(amplitude * math.sin(t * 50))
                                offset_y = int(amplitude * math.cos(t * 50))
                                return (self.resolution[0]//2 + offset_x, self.resolution[1]//2 + offset_y)
                            return ('center', 'center')
                        clip = clip.set_position(shake_pos)
                    
                    elif transition_type == "spin":
                        # Spin effect (0.4s) - 360 degree rotation
                        def spin_rotate(t):
                            if t < 0.4:
                                return 360 * (t / 0.4)  # 0 to 360 degrees
                            return 0
                        clip = clip.rotate(spin_rotate)
                    
                    elif transition_type == "wobble":
                        # Wobble effect (0.5s) - back and forth rotation
                        import math
                        def wobble_rotate(t):
                            if t < 0.5:
                                # Wobble: -15 to +15 degrees
                                return 15 * math.sin(t * 12)
                            return 0
                        clip = clip.rotate(wobble_rotate)
                    
                    elif transition_type == "fade_in":
                        # Simple fade (most stable)
                        clip = clip.crossfadein(0.3)
                    
                    clip = clip.set_start(start)
                    clip = clip.set_duration(img_duration)
                    
                    layers.append(clip)
                    print(f"   Added AI image at {start:.1f}s-{end:.1f}s (transition: {transition_type})")
                
            except Exception as e:
                print(f"   ⚠️ Failed to create layer {layer_type}: {e}")
        
        return layers

    async def _compose_with_video_breaks(self, assets: Dict) -> str:
        """
        Compose video with VIDEO BREAKS - stitches narration and original video segments.
        
        Timeline structure:
        [Narration 1] → [Original Video with Audio] → [Narration 2] → ...
        """
        from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip, TextClip, CompositeVideoClip, concatenate_videoclips, CompositeAudioClip
        from pydub import AudioSegment
        
        vb_timeline = assets["video_break_timeline"]
        segments = vb_timeline["segments"]
        
        print(f"   Building {len(segments)} segments...")
        
        video_segments = []
        current_time = 0
        
        for i, segment in enumerate(segments):
            seg_type = segment["type"]
            duration = segment["duration"]
            
            if seg_type == "narration":
                # NARRATION SEGMENT
                audio_path = segment["audio_path"]
                
                # Speed up audio 1.2x using ffmpeg (more reliable than pydub)
                import subprocess
                temp_path = audio_path.replace(".mp3", "_1.2x.mp3")
                
                # Use ffmpeg atempo filter for speed adjustment
                cmd = [
                    'ffmpeg', '-y', '-i', audio_path,
                    '-filter:a', 'atempo=1.2',
                    '-vn', temp_path
                ]
                
                try:
                    subprocess.run(cmd, check=True, capture_output=True)
                    audio_clip = AudioFileClip(temp_path)
                    actual_duration = audio_clip.duration
                except Exception as e:
                    print(f"   ⚠️ Audio speed adjustment failed: {e}, using original")
                    audio_clip = AudioFileClip(audio_path)
                    actual_duration = audio_clip.duration
                
                # Create visual composition for narration
                # Use looped background video
                video_path = assets.get("video_path")
                if video_path and os.path.exists(video_path):
                    bg = VideoFileClip(video_path)
                    if bg.duration < actual_duration:
                        bg = bg.loop(duration=actual_duration)
                    else:
                        bg = bg.subclip(0, actual_duration)
                    bg = bg.resize(height=self.resolution[1])
                    if bg.w > self.resolution[0]:
                        bg = bg.crop(x1=bg.w/2 - self.resolution[0]/2, width=self.resolution[0])
                    bg = bg.fl_image(lambda image: 0.6 * image)  # Darken
                else:
                    # Solid color fallback
                    from moviepy.editor import ColorClip
                    bg = ColorClip(size=self.resolution, color=(20, 20, 30), duration=actual_duration)
                
                # ADD CAPTIONS for this segment
                caption_clips = []
                captions_path = assets.get("captions_path")
                if captions_path and os.path.exists(captions_path):
                    try:
                        import srt
                        with open(captions_path, 'r', encoding='utf-8') as f:
                            subtitles = list(srt.parse(f.read()))
                        
                        # Filter captions for this time range
                        for sub in subtitles:
                            sub_start = sub.start.total_seconds()
                            sub_end = sub.end.total_seconds()
                            
                            # Check if this caption falls within current segment time
                            if current_time <= sub_start < current_time + actual_duration:
                                # Create caption clip
                                txt = TextClip(
                                    sub.content,
                                    fontsize=50,
                                    color='white',
                                    font='Arial-Bold',
                                    stroke_color='black',
                                    stroke_width=2,
                                    method='caption',
                                    size=(self.resolution[0] - 100, None)
                                )
                                txt = txt.set_position(('center', self.resolution[1] - 150))
                                txt = txt.set_start(sub_start - current_time)
                                txt = txt.set_duration(sub_end - sub_start)
                                txt = txt.crossfadein(0.1).crossfadeout(0.1)
                                caption_clips.append(txt)
                    except Exception as e:
                        print(f"   ⚠️ Caption error: {e}")
                
                # ADD IMAGE OVERLAYS from timeline
                image_clips = []
                sfx_clips = []  # Track SFX clips
                timeline = assets.get("timeline")
                if timeline:
                    for layer in timeline.get("layers", []):
                        if layer.get("type") == "ai_image":
                            layer_start = layer.get("start", 0)
                            layer_end = layer.get("end", 0)
                            
                            # Check if image should appear in this segment
                            if current_time <= layer_start < current_time + actual_duration:
                                asset_path = layer.get("asset_path")
                                if asset_path and os.path.exists(asset_path):
                                    try:
                                        img = ImageClip(asset_path)
                                        img = img.resize(height=400)
                                        img = img.set_position('center')
                                        img = img.set_start(layer_start - current_time)
                                        img = img.set_duration(min(layer_end - layer_start, actual_duration - (layer_start - current_time)))
                                        
                                        # Simple fade transition
                                        img = img.crossfadein(0.3).crossfadeout(0.3)
                                        image_clips.append(img)
                                        
                                        # Add SFX if marker exists
                                        if layer.get("sfx"):
                                            sfx_name = layer.get("sfx")
                                            # Find SFX file
                                            sfx_path = None
                                            for sfx in assets.get("sound_effects", []):
                                                if sfx_name in sfx.lower():
                                                    sfx_path = sfx
                                                    break
                                            
                                            if sfx_path and os.path.exists(sfx_path):
                                                try:
                                                    sfx_clip = AudioFileClip(sfx_path)
                                                    sfx_clip = sfx_clip.set_start(layer_start - current_time)
                                                    # Lower volume for SFX
                                                    sfx_clip = sfx_clip.volumex(0.5)
                                                    sfx_clips.append(sfx_clip)
                                                except Exception as e:
                                                    print(f"   ⚠️ SFX error: {e}")
                                                    
                                    except Exception as e:
                                        print(f"   ⚠️ Image overlay error: {e}")
                
                # COMPOSITE: background + images + captions
                all_clips = [bg] + image_clips + caption_clips
                if len(all_clips) > 1:
                    composite = CompositeVideoClip(all_clips, size=self.resolution)
                else:
                    composite = bg
                
                # Set audio (Narration + SFX)
                if sfx_clips:
                    final_audio = CompositeAudioClip([audio_clip] + sfx_clips)
                    composite = composite.set_audio(final_audio)
                else:
                    composite = composite.set_audio(audio_clip)
                
                video_segments.append(composite)
                current_time += actual_duration  # Update timeline
                print(f"   ✅ Segment {i+1}: Narration ({actual_duration:.1f}s)")
                
            elif seg_type == "attention_cue":
                # ATTENTION CUE SEGMENT - Bright, no overlays, just audio cue
                audio_path = segment.get("audio_path")
                
                if audio_path and os.path.exists(audio_path):
                    # Speed up audio 1.2x
                    import subprocess
                    temp_path = audio_path.replace(".mp3", "_1.2x.mp3")
                    cmd = ['ffmpeg', '-y', '-i', audio_path, '-filter:a', 'atempo=1.2', '-vn', temp_path]
                    
                    try:
                        subprocess.run(cmd, check=True, capture_output=True)
                        audio_clip = AudioFileClip(temp_path)
                        actual_duration = audio_clip.duration
                    except:
                        audio_clip = AudioFileClip(audio_path)
                        actual_duration = audio_clip.duration
                    
                    # Bright background (NO darkening)
                    video_path = assets.get("video_path")
                    if video_path and os.path.exists(video_path):
                        bg = VideoFileClip(video_path).subclip(0, min(actual_duration, VideoFileClip(video_path).duration))
                        bg = bg.resize(height=self.resolution[1])
                        if bg.w > self.resolution[0]:
                            bg = bg.crop(x1=bg.w/2 - self.resolution[0]/2, width=self.resolution[0])
                        # NO DARKENING - keep bright to draw attention!
                    else:
                        from moviepy.editor import ColorClip
                        bg = ColorClip(size=self.resolution, color=(50, 50, 70), duration=actual_duration)
                    
                    bg = bg.set_audio(audio_clip)
                    video_segments.append(bg)
                    current_time += actual_duration
                    print(f"   ✅ Segment {i+1}: ATTENTION CUE ({actual_duration:.1f}s)")
                
            elif seg_type == "video_break":
                # VIDEO BREAK SEGMENT - Full screen original video WITH audio
                video_path = segment["video_path"]
                
                if video_path and os.path.exists(video_path):
                    vid = VideoFileClip(video_path)
                    
                    # Use specified duration or full clip
                    if duration < vid.duration:
                        vid = vid.subclip(0, duration)
                    
                    # Resize to full screen
                    vid = vid.resize(width=self.resolution[0])
                    vid = vid.set_position('center')
                    
                    # Keep original audio!
                    # No darkening, no overlays - pure original video
                    
                    video_segments.append(vid)
                    current_time += vid.duration
                    print(f"   ✅ Segment {i+1}: VIDEO BREAK ({vid.duration:.1f}s) - Original video with audio")
                else:
                    print(f"   ⚠️ Video break clip not found: {video_path}")
        
        final_video = concatenate_videoclips(video_segments, method="compose")
        
        # Render
        output_path = os.path.join(self.output_dir, "final_video.mp4")
        print(f"   Rendering to {output_path}...")
        
        final_video.write_videofile(
            output_path,
            fps=30,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            threads=4
        )
        
        print("✅ Video rendered successfully!")
        return output_path

    async def _render_from_timeline(self, assets: Dict) -> str:
        """
        Renders video from a multi-track timeline structure using Z-Index sorting.
        """
        timeline = assets["composer_timeline"]
        total_duration = timeline["total_duration"]
        
        print(f"   Rendering from multi-track timeline ({total_duration:.1f}s)...")
        
        # === BUILD VIDEO LAYERS WITH Z-INDEX ===
        all_visual_clips = []  # List of (z_index, clip)
        
        # 1. Narration Video (Background) - Z=0
        for clip_info in timeline["tracks"]["narration_video"]:
            composite = self._create_narration_composite_v2(clip_info, assets)
            if composite:
                composite = composite.set_start(clip_info["timeline_start"])
                composite = composite.set_duration(
                    clip_info["timeline_end"] - clip_info["timeline_start"]
                )
                all_visual_clips.append((0, composite))
        
        # 2. Overlay Images (Screenshots/Images) - Z=5 (Default)
        if "overlay_images" in timeline["tracks"]:
            for img_info in timeline["tracks"]["overlay_images"]:
                try:
                    if os.path.exists(img_info["source"]):
                        img = ImageClip(img_info["source"])
                        
                        # Resize logic (fit to screen with padding)
                        img_w, img_h = img.size
                        target_w, target_h = self.resolution
                        scale = min(target_w / img_w, target_h / img_h) * img_info.get("scale", 0.8)
                        img = img.resize(scale)
                        
                        img = img.set_position(img_info.get("position", "center"))
                        img = img.set_start(img_info["timeline_start"])
                        img = img.set_duration(img_info["timeline_end"] - img_info["timeline_start"])
                        
                        # Animations (Simple Fade)
                        img = img.crossfadein(0.3).crossfadeout(0.3)
                        
                        z_index = img_info.get("z_index", 5)
                        all_visual_clips.append((z_index, img))
                        print(f"   Added overlay image (z={z_index})")
                except Exception as e:
                    print(f"   ⚠️ Overlay image error: {e}")

        # 3. Video Clips - Z=10 (Default)
        for clip_info in timeline["tracks"]["clip_video"]:
            try:
                clip = VideoFileClip(clip_info["source"])
                clip = clip.subclip(clip_info["source_start"], clip_info["source_end"])
                clip = clip.resize(width=self.resolution[0])
                clip = clip.set_position("center")
                clip = clip.set_start(clip_info["timeline_start"])
                clip = clip.without_audio()  # We'll handle audio separately
                
                z_index = clip_info.get("z_index", 10)
                all_visual_clips.append((z_index, clip))
                print(f"   Added video clip at {clip_info['timeline_start']:.1f}s (z={z_index})")
            except Exception as e:
                print(f"   ⚠️ Failed to load video clip: {e}")
        
        # 4. Captions - Z=100
        print(f"   Adding {len(timeline['tracks']['captions'])} captions...")
        for caption_info in timeline["tracks"]["captions"]:
            try:
                txt = TextClip(
                    caption_info["text"],
                    fontsize=50,
                    color='white',
                    font='Arial-Bold',
                    stroke_color='black',
                    stroke_width=2,
                    method='caption',
                    size=(self.resolution[0] - 100, None)
                )
                txt = txt.set_position(('center', int(self.resolution[1] * 2/3)))
                txt = txt.set_start(caption_info["timeline_start"])
                txt = txt.set_duration(
                    caption_info["timeline_end"] - caption_info["timeline_start"]
                )
                txt = txt.crossfadein(0.1).crossfadeout(0.1)
                
                all_visual_clips.append((100, txt))
            except Exception as e:
                print(f"   ⚠️ Caption error: {e}")
        
        # Sort by Z-Index and Extract
        all_visual_clips.sort(key=lambda x: x[0])
        video_layers = [c[1] for c in all_visual_clips]
        
        print(f"   Compositing {len(video_layers)} visual layers...")
        
        # Composite all video layers
        final_video = CompositeVideoClip(
            video_layers,
            size=self.resolution
        ).set_duration(total_duration)
        
        # === BUILD AUDIO LAYERS ===
        audio_layers = []
        
        # Track 1: Narration audio (with speed-up)
        for clip_info in timeline["tracks"]["narration_audio"]:
            try:
                audio = AudioFileClip(clip_info["source"])
                audio = audio.subclip(clip_info["source_start"], clip_info["source_end"])
                
                # Speed up using ffmpeg
                if clip_info.get("speed", 1.0) != 1.0:
                    audio = self._speed_up_audio_segment_v2(
                        audio,
                        clip_info["source_start"],
                        clip_info["source_end"],
                        clip_info["speed"]
                    )
                
                audio = audio.volumex(clip_info["volume"])
                audio = audio.set_start(clip_info["timeline_start"])
                audio_layers.append(audio)
                print(f"   Added narration audio at {clip_info['timeline_start']:.1f}s")
            except Exception as e:
                print(f"   ⚠️ Narration audio error: {e}")
        
        # Track 2: Original clip audio (with ducking during overlap)
        for clip_info in timeline["tracks"]["clip_audio"]:
            try:
                clip = VideoFileClip(clip_info["source"])
                if clip.audio:
                    audio = clip.audio
                    audio = audio.subclip(clip_info["source_start"], clip_info["source_end"])
                    
                    # Apply ducking if specified
                    if "duck_start" in clip_info:
                        audio = self._apply_audio_ducking_v2(
                            audio,
                            clip_info["timeline_start"],
                            clip_info["duck_start"],
                            clip_info["duck_end"],
                            clip_info["duck_volume"],
                            clip_info.get("fade_duration", 0.5)
                        )
                    else:
                        audio = audio.volumex(clip_info["volume"])
                    
                    audio = audio.set_start(clip_info["timeline_start"])
                    audio_layers.append(audio)
                    print(f"   Added clip audio at {clip_info['timeline_start']:.1f}s (ducked)")
            except Exception as e:
                print(f"   ⚠️ Clip audio error: {e}")
        
        # Track 3: SFX audio (NEW!)
        if "sfx" in timeline["tracks"]:
            for sfx_info in timeline["tracks"]["sfx"]:
                try:
                    if os.path.exists(sfx_info["source"]):
                        audio = AudioFileClip(sfx_info["source"])
                        audio = audio.volumex(sfx_info.get("volume", 0.7))
                        audio = audio.set_start(sfx_info["timeline_start"])
                        audio_layers.append(audio)
                        print(f"   Added SFX at {sfx_info['timeline_start']:.1f}s")
                    else:
                        print(f"   ⚠️ SFX file not found: {sfx_info['source']}")
                except Exception as e:
                    print(f"   ⚠️ SFX error: {e}")
        
        # Composite all audio layers
        if audio_layers:
            final_audio = CompositeAudioClip(audio_layers)
            final_video = final_video.set_audio(final_audio)
        
        # === RENDER ===
        output_filename = "final_video.mp4"
        output_path = os.path.join(self.output_dir, output_filename)
        
        print(f"   Rendering to {output_path}...")
        final_video.write_videofile(
            output_path,
            fps=self.fps,
            codec='libx264',
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            threads=4
        )
        
        print("✅ Video rendered successfully!")
        return output_path
    
    def _create_narration_composite_v2(self, clip_info: Dict, assets: Dict) -> VideoFileClip:
        """
        Create composite for narration segment (background + images).
        """
        duration = clip_info["timeline_end"] - clip_info["timeline_start"]
        segment_type = clip_info.get("segment_type", "narration")
        
        # Create background
        video_path = assets.get("video_path")
        if video_path and os.path.exists(video_path):
            bg = VideoFileClip(video_path)
            if bg.duration < duration:
                bg = bg.loop(duration=duration)
            else:
                bg = bg.subclip(0, duration)
            bg = bg.resize(height=self.resolution[1])
            if bg.w > self.resolution[0]:
                bg = bg.crop(x1=bg.w/2 - self.resolution[0]/2, width=self.resolution[0])
            
            # Darken for narration, bright for attention_cue
            if segment_type == "attention_cue":
                # NO DARKENING for attention cue
                pass
            else:
                bg = bg.fl_image(lambda image: 0.6 * image)
        else:
            # Solid color fallback
            color = (50, 50, 70) if segment_type == "attention_cue" else (20, 20, 30)
            bg = ColorClip(size=self.resolution, color=color, duration=duration)
        
        # Add images from visual timeline
        layers = [bg]
        visual_timeline = clip_info.get("visual_timeline", [])
        
        for visual in visual_timeline:
            if visual.get("type") == "ai_image":
                asset_path = visual.get("asset_path")
                if asset_path and os.path.exists(asset_path):
                    try:
                        img = ImageClip(asset_path)
                        img = img.resize(height=400)
                        img = img.set_position('center')
                        img = img.set_start(visual["start"])
                        img = img.set_duration(visual["end"] - visual["start"])
                        img = img.crossfadein(0.3).crossfadeout(0.3)
                        layers.append(img)
                    except Exception as e:
                        print(f"   ⚠️ Image error: {e}")
        
        # Composite
        if len(layers) > 1:
            return CompositeVideoClip(layers, size=self.resolution)
        else:
            return bg
    
    def _speed_up_audio_segment_v2(
        self,
        audio: AudioFileClip,
        start: float,
        end: float,
        speed: float
    ) -> AudioFileClip:
        """
        Speed up audio segment using ffmpeg.
        """
        try:
            # Create temp file
            import tempfile
            temp_input = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
            temp_output = tempfile.NamedTemporaryFile(suffix='.mp3', delete=False)
            
            # Write audio segment to temp file
            audio.write_audiofile(temp_input.name, verbose=False, logger=None)
            
            # Speed up using ffmpeg
            cmd = [
                'ffmpeg', '-y', '-i', temp_input.name,
                '-filter:a', f'atempo={speed}',
                '-vn', temp_output.name
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            
            # Load sped-up audio
            result = AudioFileClip(temp_output.name)
            
            # Cleanup
            os.unlink(temp_input.name)
            os.unlink(temp_output.name)
            
            return result
        except Exception as e:
            print(f"   ⚠️ Audio speed-up failed: {e}, using original")
            return audio
    
    def _apply_audio_ducking_v2(
        self,
        audio: AudioFileClip,
        clip_start: float,
        duck_start: float,
        duck_end: float,
        duck_volume: float,
        fade_duration: float
    ) -> AudioFileClip:
        """
        Apply audio ducking with fade in/out.
        Uses numpy-compatible operations for array handling.
        """
        import numpy as np
        
        def volume_curve(t):
            # t can be a numpy array, so use numpy operations
            absolute_t = clip_start + t
            
            # Use numpy.where for conditional logic
            # Region 1: Before duck (full volume)
            result = np.ones_like(absolute_t, dtype=float)
            
            # Region 2: Fade down
            fade_down_mask = (absolute_t >= duck_start) & (absolute_t < duck_start + fade_duration)
            progress = (absolute_t - duck_start) / fade_duration
            result = np.where(fade_down_mask, 1.0 - (1.0 - duck_volume) * progress, result)
            
            # Region 3: Ducked (low volume)
            ducked_mask = (absolute_t >= duck_start + fade_duration) & (absolute_t < duck_end - fade_duration)
            result = np.where(ducked_mask, duck_volume, result)
            
            # Region 4: Fade up
            fade_up_mask = (absolute_t >= duck_end - fade_duration) & (absolute_t < duck_end)
            progress = (absolute_t - (duck_end - fade_duration)) / fade_duration
            result = np.where(fade_up_mask, duck_volume + (1.0 - duck_volume) * progress, result)
            
            # Region 5: After duck (full volume)
            after_mask = absolute_t >= duck_end
            result = np.where(after_mask, 1.0, result)
            
            return result
        
        def apply_volume(get_frame, t):
            frame = get_frame(t)
            curve = volume_curve(t)
            
            # Handle stereo audio: reshape curve to match frame shape
            if len(frame.shape) == 2:  # Stereo: (samples, 2)
                curve = curve.reshape(-1, 1)  # Reshape to (samples, 1) for broadcasting
            
            return frame * curve
        
        return audio.fl(apply_volume, apply_to=['audio'])

    async def _render_from_professional_timeline(self, assets: Dict) -> str:
        """
        Render from V2 professional timeline (beat-synchronized).
        Converts V2 structure to V1 format for rendering.
        """
        v2_timeline = assets["professional_timeline"]
        
        # Process clip audio to flatten ducking structure (V2 -> V1)
        clip_audio_v1 = []
        for clip in v2_timeline.get("tracks", {}).get("audio", {}).get("clips", []):
            v1_clip = clip.copy()
            # Flatten ducking info
            if clip.get("ducking", {}).get("enabled"):
                v1_clip["duck_start"] = clip["ducking"]["start"]
                v1_clip["duck_end"] = clip["ducking"]["end"]
                v1_clip["duck_volume"] = clip["ducking"]["target_volume"]
            # Ensure volume is set (default 0.9 from V2)
            if "volume" not in v1_clip:
                v1_clip["volume"] = 0.9
            clip_audio_v1.append(v1_clip)
            
        # Convert V2 timeline structure to V1 format
        v1_timeline = {
            "total_duration": v2_timeline.get("total_duration", 0),
            "tracks": {
                "narration_audio": v2_timeline.get("tracks", {}).get("audio", {}).get("narration", []),
                "clip_audio": clip_audio_v1,
                "narration_video": v2_timeline.get("tracks", {}).get("video", {}).get("background", []),
                "clip_video": v2_timeline.get("tracks", {}).get("video", {}).get("clips", []),
                "captions": v2_timeline.get("tracks", {}).get("text", {}).get("captions", []),
                "sfx": v2_timeline.get("tracks", {}).get("audio", {}).get("sfx", []),
                "overlay_images": v2_timeline.get("tracks", {}).get("video", {}).get("images", [])
            }
        }
        
        # Add images to narration_video track (V2 images -> V1 narration composite)
        # Note: V1 handles images inside _create_narration_composite_v2 using assets['images']
        # We need to make sure V2 images are passed correctly or handled here.
        # For now, let's rely on V1's image handling which uses random images if not specified in track.
        # TODO: Map V2 specific image placement to V1 composite logic if needed.
        
        print(f"   Converted V2 timeline to V1 format")
        print(f"   Narration segments: {len(v1_timeline['tracks']['narration_audio'])}")
        print(f"   Video clips: {len(v1_timeline['tracks']['clip_video'])}")
        
        # Debug video clips
        for i, clip in enumerate(v1_timeline['tracks']['clip_video']):
            print(f"     Clip {i}: {clip['source']}")
            print(f"       Time: {clip['timeline_start']:.1f}s - {clip['timeline_end']:.1f}s")
            if not os.path.exists(clip['source']):
                print(f"       ⚠️ FILE NOT FOUND: {clip['source']}")
        
        # Use V1 rendering logic
        assets["composer_timeline"] = v1_timeline
        return await self._render_from_timeline(assets)
