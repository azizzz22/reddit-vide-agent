"""
AssetManagerAgent - Intelligent asset organization and validation
Handles asset inventory, scoring, grouping, and quality validation
"""

import os
from typing import Dict, List, Any, Optional
from .base_agent import BaseAgent
from moviepy.editor import VideoFileClip, AudioFileClip, ImageClip
import json

class AssetManagerAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.min_video_duration = 2.0  # Minimum acceptable video duration
        self.min_image_size = (400, 400)  # Minimum image resolution
        
    async def execute(self, raw_assets: Dict) -> Dict:
        """
        Organize and validate all assets.
        
        Args:
            raw_assets: {
                "script": str,
                "parsed_script": Dict,
                "voiceover_path": str,
                "captions_path": str,
                "video_clips": Dict,
                "images": List[str],
                "video_path": str (background),
                "sound_effects": List
            }
        
        Returns:
            Organized asset catalog with metadata and quality report
        """
        print("AssetManagerAgent: Organizing assets...")
        
        catalog = {
            "narration": self._process_narration(
                raw_assets.get("voiceover_path"),
                raw_assets.get("captions_path")
            ),
            "video_clips": self._process_video_clips(
                raw_assets.get("video_clips", {}),
                raw_assets.get("parsed_script", {})
            ),
            "images": self._process_images(
                raw_assets.get("images", []),
                raw_assets.get("script", "")
            ),
            "screenshots": self._process_screenshots(
                raw_assets.get("post_screenshot"),
                raw_assets.get("comment_screenshots", [])
            ),
            "background": self._process_background(
                raw_assets.get("video_path")
            ),
            "sound_effects": self._process_sfx(
                raw_assets.get("sound_effects", [])
            )
        }
        
        # Generate quality report
        quality_report = self._generate_quality_report(catalog)
        
        result = {
            "catalog": catalog,
            "quality_report": quality_report,
            "metadata": {
                "total_assets": self._count_assets(catalog),
                "completeness": quality_report["completeness"],
                "ready_for_composition": quality_report["completeness"] >= 0.7
            }
        }
        
        print(f"   ✅ Organized {result['metadata']['total_assets']} assets")
        print(f"   Completeness: {quality_report['completeness']*100:.0f}%")
        
        if quality_report["issues"]:
            print(f"   ⚠️ {len(quality_report['issues'])} issues found")
            for issue in quality_report["issues"][:3]:
                print(f"      - {issue}")
        
        return result
    
    def _process_screenshots(self, post_screenshot: Optional[str], comment_screenshots: List[str]) -> Dict:
        """Process Reddit screenshots."""
        processed = {
            "post": None,
            "comments": []
        }
        
        # Process post screenshot
        if post_screenshot and os.path.exists(post_screenshot):
            try:
                img = ImageClip(post_screenshot)
                width, height = img.size
                img.close()
                
                processed["post"] = {
                    "path": post_screenshot,
                    "width": width,
                    "height": height,
                    "available": True,
                    "quality_score": 1.0
                }
            except Exception as e:
                print(f"   ⚠️ Error processing post screenshot: {e}")
        
        # Process comment screenshots
        for i, path in enumerate(comment_screenshots):
            if path and os.path.exists(path):
                try:
                    img = ImageClip(path)
                    width, height = img.size
                    img.close()
                    
                    processed["comments"].append({
                        "path": path,
                        "index": i,
                        "width": width,
                        "height": height,
                        "available": True,
                        "quality_score": 0.9
                    })
                except Exception as e:
                    print(f"   ⚠️ Error processing comment screenshot {path}: {e}")
                    
        return processed
    
    def _process_narration(self, voiceover_path: str, captions_path: str) -> Dict:
        """Process narration audio and captions."""
        if not voiceover_path or not os.path.exists(voiceover_path):
            return {"available": False, "issues": ["Voiceover file missing"]}
        
        try:
            audio = AudioFileClip(voiceover_path)
            duration = audio.duration
            audio.close()
            
            # Load captions
            caption_count = 0
            if captions_path and os.path.exists(captions_path):
                import srt
                with open(captions_path, 'r', encoding='utf-8') as f:
                    captions = list(srt.parse(f.read()))
                    caption_count = len(captions)
            
            return {
                "available": True,
                "path": voiceover_path,
                "duration": duration,
                "captions_path": captions_path,
                "caption_count": caption_count,
                "quality_score": 1.0,
                "issues": []
            }
        except Exception as e:
            return {
                "available": False,
                "issues": [f"Error processing narration: {e}"]
            }
    
    def _process_video_clips(self, video_clips: Dict, parsed_script: Dict) -> Dict:
        """Process and score video clips based on script requirements."""
        processed = {}
        
        # Get required clip types from script
        required_types = set()
        if parsed_script.get("has_breaks"):
            for segment in parsed_script.get("segments", []):
                if segment["type"] == "video_break":
                    required_types.add(segment.get("break_type", "action"))
        
        # Process each clip
        for clip_type, clip_info in video_clips.items():
            if isinstance(clip_info, dict):
                clip_path = clip_info.get("path")
                description = clip_info.get("description", "")
                duration = clip_info.get("duration", 0)
            else:
                clip_path = clip_info
                description = ""
                duration = 0
            
            if not clip_path or not os.path.exists(clip_path):
                processed[clip_type] = {
                    "available": False,
                    "issues": ["File not found"]
                }
                continue
            
            try:
                # Get actual duration if not provided
                if duration == 0:
                    clip = VideoFileClip(clip_path)
                    duration = clip.duration
                    clip.close()
                
                # Calculate relevance score
                is_required = clip_type in required_types
                duration_ok = duration >= self.min_video_duration
                
                score = 0.5  # Base score
                if is_required:
                    score += 0.3
                if duration_ok:
                    score += 0.2
                
                processed[clip_type] = {
                    "available": True,
                    "path": clip_path,
                    "duration": duration,
                    "description": description,
                    "required": is_required,
                    "quality_score": score,
                    "issues": [] if duration_ok else ["Duration too short"]
                }
            except Exception as e:
                processed[clip_type] = {
                    "available": False,
                    "issues": [f"Error processing clip: {e}"]
                }
        
        # Fallback: Scan assets dir if no clips found
        if not processed:
            print("   ⚠️ No clips provided, scanning assets directory...")
            # Assuming assets dir is ../assets relative to this file
            assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
            if os.path.exists(assets_dir):
                for f in os.listdir(assets_dir):
                    if f.endswith(('.mp4', '.mov')) and 'clip' in f:
                        path = os.path.join(assets_dir, f)
                        try:
                            clip = VideoFileClip(path)
                            duration = clip.duration
                            clip.close()
                            
                            processed["fallback_clip"] = {
                                "available": True,
                                "path": path,
                                "duration": duration,
                                "description": "Fallback clip",
                                "required": False,
                                "quality_score": 0.5,
                                "issues": [],
                                "tags": ["fallback"]
                            }
                            print(f"   Found fallback clip: {f}")
                            break # Just need one
                        except: pass
                        
        return processed
    
    def _process_images(self, images: List[str], script: str) -> List[Dict]:
        """Process and score images."""
        processed = []
        
        for i, img_path in enumerate(images):
            if not os.path.exists(img_path):
                continue
            
            try:
                # Get image metadata
                img = ImageClip(img_path)
                width, height = img.size
                img.close()
                
                # Score based on resolution
                size_ok = width >= self.min_image_size[0] and height >= self.min_image_size[1]
                score = 0.8 if size_ok else 0.5
                
                processed.append({
                    "path": img_path,
                    "index": i,
                    "width": width,
                    "height": height,
                    "quality_score": score,
                    "suggested_timing": None,  # Will be set by TimelineArchitect
                    "issues": [] if size_ok else ["Low resolution"]
                })
            except Exception as e:
                print(f"   ⚠️ Error processing image {img_path}: {e}")
        
        return processed
    
    def _process_background(self, video_path: Optional[str]) -> Dict:
        """Process background video."""
        if not video_path or not os.path.exists(video_path):
            return {
                "available": False,
                "fallback": "solid_color",
                "issues": ["Background video missing"]
            }
        
        try:
            clip = VideoFileClip(video_path)
            duration = clip.duration
            width, height = clip.size
            clip.close()
            
            return {
                "available": True,
                "path": video_path,
                "duration": duration,
                "width": width,
                "height": height,
                "quality_score": 1.0,
                "issues": []
            }
        except Exception as e:
            return {
                "available": False,
                "fallback": "solid_color",
                "issues": [f"Error processing background: {e}"]
            }
    
    def _process_sfx(self, sound_effects: List) -> List[Dict]:
        """Process sound effects."""
        processed = []
        
        for sfx in sound_effects:
            if isinstance(sfx, dict):
                sfx_path = sfx.get("path")
                sfx_type = sfx.get("type", "generic")
            else:
                sfx_path = sfx
                sfx_type = "generic"
            
            if sfx_path and os.path.exists(sfx_path):
                processed.append({
                    "path": sfx_path,
                    "type": sfx_type,
                    "quality_score": 0.8,
                    "suggested_trigger": None  # Will be set by TimelineArchitect
                })
        
        return processed
    
    def _generate_quality_report(self, catalog: Dict) -> Dict:
        """Generate quality report for all assets."""
        issues = []
        total_score = 0
        score_count = 0
        
        # Check narration
        if not catalog["narration"]["available"]:
            issues.extend(catalog["narration"]["issues"])
        else:
            total_score += catalog["narration"]["quality_score"]
            score_count += 1
        
        # Check video clips
        required_clips = sum(1 for c in catalog["video_clips"].values() if c.get("required", False))
        available_required = sum(1 for c in catalog["video_clips"].values() 
                                if c.get("required", False) and c.get("available", False))
        
        if required_clips > 0 and available_required < required_clips:
            issues.append(f"Missing {required_clips - available_required} required video clips")
        
        for clip in catalog["video_clips"].values():
            if clip.get("available"):
                total_score += clip.get("quality_score", 0)
                score_count += 1
            else:
                issues.extend(clip.get("issues", []))
        
        # Check images
        if len(catalog["images"]) == 0:
            issues.append("No images available")
        else:
            for img in catalog["images"]:
                total_score += img["quality_score"]
                score_count += 1
        
        # Check background
        if not catalog["background"]["available"]:
            issues.extend(catalog["background"]["issues"])
        else:
            total_score += catalog["background"]["quality_score"]
            score_count += 1
        
        # Calculate completeness
        completeness = (total_score / score_count) if score_count > 0 else 0.0
        
        return {
            "completeness": completeness,
            "issues": issues,
            "suggestions": self._generate_suggestions(catalog, issues)
        }
    
    def _generate_suggestions(self, catalog: Dict, issues: List[str]) -> List[str]:
        """Generate suggestions for improving asset quality."""
        suggestions = []
        
        if not catalog["narration"]["available"]:
            suggestions.append("Generate voiceover audio")
        
        if len(catalog["images"]) < 3:
            suggestions.append("Generate more images for visual variety")
        
        if not catalog["background"]["available"]:
            suggestions.append("Use solid color background as fallback")
        
        return suggestions
    
    def _count_assets(self, catalog: Dict) -> int:
        """Count total number of available assets."""
        count = 0
        
        if catalog["narration"]["available"]:
            count += 1
        
        count += sum(1 for c in catalog["video_clips"].values() if c.get("available", False))
        count += len(catalog["images"])
        
        if catalog["background"]["available"]:
            count += 1
        
        count += len(catalog["sound_effects"])
        
        return count
