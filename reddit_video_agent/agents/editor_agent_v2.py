"""
Editor Agent - Renders multi-track timeline to final video
Handles MoviePy composition and export
"""

import os
from typing import Dict, List, Any
from moviepy.editor import (
    VideoFileClip, AudioFileClip, ImageClip, TextClip,
    CompositeVideoClip, CompositeAudioClip, ColorClip,
    concatenate_videoclips
)
from .base_agent import BaseAgent
from ..core.config import Config
import subprocess

class EditorAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.resolution = (720, 1280)  # 9:16 for shorts
        self.fps = 30
        self.output_dir = Config.OUTPUT_DIR
    
    async def execute(self, assets: Dict) -> str:
        """
        Render video from multi-track timeline or standard assets.
        """
        print("EditorAgent: Composing video...")
        
        try:
            # Check if we have multi-track timeline (from VideoComposerAgent)
            if "composer_timeline" in assets:
                return await self._render_from_timeline(assets)
            else:
                # Fallback to old method
                return await self._render_standard(assets)
                
        except Exception as e:
            print(f"❌ Editor Error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    async def _render_from_timeline(self, assets: Dict) -> str:
        """
        Render video from multi-track timeline (NEW METHOD).
        """
        timeline = assets["composer_timeline"]
        total_duration = timeline["total_duration"]
        
        print(f"   Rendering from timeline ({total_duration:.1f}s)...")
        
        # === BUILD VIDEO LAYERS ===
        video_layers = []
        
        # Layer 1: Narration video composites (background + images)
        for clip_info in timeline["tracks"]["narration_video"]:
            composite = self._create_narration_composite(clip_info, assets)
            if composite:
                composite = composite.set_start(clip_info["timeline_start"])
                composite = composite.set_duration(
                    clip_info["timeline_end"] - clip_info["timeline_start"]
                )
                video_layers.append(composite)
        
        # Layer 2: Original video clips (on top, during video breaks)
        for clip_info in timeline["tracks"]["clip_video"]:
            try:
                clip = VideoFileClip(clip_info["source"])
                clip = clip.subclip(clip_info["source_start"], clip_info["source_end"])
                clip = clip.resize(width=self.resolution[0])
                clip = clip.set_position("center")
                clip = clip.set_start(clip_info["timeline_start"])
                clip = clip.without_audio()  # We'll handle audio separately
                video_layers.append(clip)
                print(f"   Added video clip at {clip_info['timeline_start']:.1f}s")
            except Exception as e:
                print(f"   ⚠️ Failed to load video clip: {e}")
        
        # Layer 3: Captions (on top of everything)
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
                txt = txt.set_position(('center', self.resolution[1] - 150))
                txt = txt.set_start(caption_info["timeline_start"])
                txt = txt.set_duration(
                    caption_info["timeline_end"] - caption_info["timeline_start"]
                )
                txt = txt.crossfadein(0.1).crossfadeout(0.1)
                video_layers.append(txt)
            except Exception as e:
                print(f"   ⚠️ Caption error: {e}")
        
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
                    audio = self._speed_up_audio_segment(
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
                        audio = self._apply_audio_ducking(
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
    
    def _create_narration_composite(self, clip_info: Dict, assets: Dict) -> VideoFileClip:
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
    
    def _speed_up_audio_segment(
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
    
    def _apply_audio_ducking(
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
        """
        def volume_curve(t):
            # t is absolute time in the clip
            absolute_t = clip_start + t
            
            if absolute_t < duck_start:
                return 1.0  # Full volume before duck
            elif absolute_t < duck_start + fade_duration:
                # Fade down
                progress = (absolute_t - duck_start) / fade_duration
                return 1.0 - (1.0 - duck_volume) * progress
            elif absolute_t < duck_end - fade_duration:
                return duck_volume  # Ducked volume
            elif absolute_t < duck_end:
                # Fade up
                progress = (absolute_t - (duck_end - fade_duration)) / fade_duration
                return duck_volume + (1.0 - duck_volume) * progress
            else:
                return 1.0  # Full volume after duck
        
        return audio.fl(lambda gf, t: gf(t) * volume_curve(t), apply_to=['audio'])
    
    async def _render_standard(self, assets: Dict) -> str:
        """
        Fallback to standard rendering (old method).
        """
        # ... (keep existing standard rendering code)
        print("   Using standard rendering mode")
        return None
