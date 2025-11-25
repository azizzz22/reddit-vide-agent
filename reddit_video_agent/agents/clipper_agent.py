import os
import json
import time
from typing import Dict, Any, List
from moviepy.editor import VideoFileClip
import google.generativeai as genai
from .base_agent import BaseAgent
from ..core.config import Config

class ClipperAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = Config.get_gemini_key()
        self.assets_dir = Config.ASSETS_DIR
        genai.configure(api_key=self.api_key)
        # Using the latest Flash model as requested
        self.model = genai.GenerativeModel("models/gemini-flash-latest")

    async def execute(self, video_path: str) -> Dict[str, str]:
        """
        Analyzes the video and extracts key clips (Intro, Climax, Punchline).
        Returns a dictionary of clip paths.
        """
        print(f"ClipperAgent: Analyzing video {os.path.basename(video_path)}...")
        
        if not video_path or not os.path.exists(video_path):
            print("❌ No video to clip.")
            return {}

        clips = {}
        
        try:
            # 1. Upload Video to Gemini for Analysis
            print("   Uploading video to Gemini...")
            video_file = genai.upload_file(path=video_path)
            
            # Wait for processing
            while video_file.state.name == "PROCESSING":
                print("   Processing video...", end="\r")
                time.sleep(2)
                video_file = genai.get_file(video_file.name)
                
            if video_file.state.name == "FAILED":
                print("❌ Video processing failed.")
                return {}

            print("   ✅ Video processed. Analyzing content...")

            # 2. Analyze Video to find timestamps AND descriptions
            prompt = """
            Analyze this video carefully. I need to cut it into 3 key segments for a viral short video:
            1. "intro": The beginning context (start to something happening).
            2. "action": The main action or build-up.
            3. "punchline": The funniest moment, climax, or key reveal.
            
            For each segment, provide:
            - start_sec: Start time in seconds
            - end_sec: End time in seconds  
            - description: 1-sentence description of what's happening in this clip
            
            Return a JSON object:
            {
                "intro": {
                    "start": start_sec,
                    "end": end_sec,
                    "description": "Brief description of intro"
                },
                "action": {
                    "start": start_sec,
                    "end": end_sec,
                    "description": "Brief description of action"
                },
                "punchline": {
                    "start": start_sec,
                    "end": end_sec,
                    "description": "Brief description of punchline"
                }
            }
            
            If the video is too short or simple, just split it logically. Ensure segments don't overlap too much.
            """
            
            response = self.model.generate_content(
                [video_file, prompt],
                generation_config={"response_mime_type": "application/json"}
            )
            
            timestamps = json.loads(response.text)
            print(f"   Timestamps found: {timestamps}")
            
            # 3. Cut Video Clips
            original_clip = VideoFileClip(video_path)
            
            for key, clip_info in timestamps.items():
                # Handle both old format [start, end] and new format {start, end, description}
                if isinstance(clip_info, dict):
                    start = clip_info.get("start", 0)
                    end = clip_info.get("end", start + 2)
                    description = clip_info.get("description", f"{key} clip")
                else:
                    # Old format fallback
                    start, end = clip_info
                    description = f"{key} clip"
                
                # Validate times
                start = max(0, float(start))
                end = min(original_clip.duration, float(end))
                
                if end - start < 0.5: # Too short
                    continue
                    
                print(f"   Cutting {key}: {start:.2f}s - {end:.2f}s")
                
                output_filename = f"clip_{key}.mp4"
                output_path = os.path.join(self.assets_dir, output_filename)
                
                new_clip = original_clip.subclip(start, end)
                new_clip.write_videofile(
                    output_path, 
                    codec="libx264", 
                    audio_codec="aac", 
                    verbose=False, 
                    logger=None
                )
                
                clips[key] = {
                    "path": output_path,
                    "description": description,
                    "duration": end - start
                }
                
            original_clip.close()
            
            # Cleanup Gemini file
            genai.delete_file(video_file.name)
            
            print(f"✅ Created {len(clips)} clips.")
            return clips

        except Exception as e:
            print(f"❌ Error in ClipperAgent: {e}")
            import traceback
            traceback.print_exc()
            return {}
