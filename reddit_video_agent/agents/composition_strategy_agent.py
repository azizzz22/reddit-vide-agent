"""
CompositionStrategyAgent - Determines optimal composition strategy
Analyzes content tone and selects appropriate visual/audio strategy
"""

import os
from typing import Dict, List, Any
from .base_agent import BaseAgent
import google.generativeai as genai
from ..core.config import Config

class CompositionStrategyAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = Config.get_gemini_key()
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash-exp")
        
        # Define strategy templates
        self.strategies = {
            "action_packed": {
                "pacing": {
                    "tempo": 1.3,
                    "segment_variation": [1.2, 1.5, 1.3, 1.4]
                },
                "visual": {
                    "image_duration": 1.5,
                    "transition_style": "quick_cuts",
                    "caption_style": "bold",
                    "image_placement": "beat_synchronized"
                },
                "audio": {
                    "overlap_strategy": "minimal",
                    "overlap_percentage": 0.3,
                    "ducking_curve": "sharp",
                    "duck_volume": 0.2,
                    "sfx_density": "high"
                }
            },
            "storytelling": {
                "pacing": {
                    "tempo": 1.1,
                    "segment_variation": [1.0, 1.1, 1.2, 1.1]
                },
                "visual": {
                    "image_duration": 3.0,
                    "transition_style": "smooth_fades",
                    "caption_style": "elegant",
                    "image_placement": "narrative_flow"
                },
                "audio": {
                    "overlap_strategy": "generous",
                    "overlap_percentage": 0.5,
                    "ducking_curve": "smooth",
                    "duck_volume": 0.3,
                    "sfx_density": "medium"
                }
            },
            "educational": {
                "pacing": {
                    "tempo": 1.0,
                    "segment_variation": [1.0, 1.0, 1.0, 1.0]
                },
                "visual": {
                    "image_duration": 4.0,
                    "transition_style": "clean_cuts",
                    "caption_style": "clear",
                    "image_placement": "topic_aligned"
                },
                "audio": {
                    "overlap_strategy": "moderate",
                    "overlap_percentage": 0.4,
                    "ducking_curve": "linear",
                    "duck_volume": 0.25,
                    "sfx_density": "low"
                }
            },
            "dramatic": {
                "pacing": {
                    "tempo": 0.9,
                    "segment_variation": [0.8, 1.0, 1.2, 0.9]
                },
                "visual": {
                    "image_duration": 3.5,
                    "transition_style": "dramatic_fades",
                    "caption_style": "impactful",
                    "image_placement": "emotional_beats"
                },
                "audio": {
                    "overlap_strategy": "dynamic",
                    "overlap_percentage": 0.6,
                    "ducking_curve": "exponential",
                    "duck_volume": 0.15,
                    "sfx_density": "medium"
                }
            }
        }
    
    async def execute(self, assets: Dict) -> Dict:
        """
        Determine optimal composition strategy.
        
        Args:
            assets: {
                "script": str,
                "parsed_script": Dict,
                "asset_catalog": Dict (from AssetManager)
            }
        
        Returns:
            Composition strategy with pacing, visual, and audio plans
        """
        print("CompositionStrategyAgent: Analyzing content...")
        
        script = assets.get("script", "")
        parsed_script = assets.get("parsed_script", {})
        asset_catalog = assets.get("asset_catalog", {})
        
        # Analyze tone
        tone_analysis = await self._analyze_tone(script)
        
        # Select strategy
        strategy_name = self._select_strategy(tone_analysis)
        base_strategy = self.strategies[strategy_name].copy()
        
        # Adapt strategy based on assets
        adapted_strategy = self._adapt_to_assets(base_strategy, asset_catalog, parsed_script)
        
        result = {
            "strategy_name": strategy_name,
            "tone_analysis": tone_analysis,
            "pacing": adapted_strategy["pacing"],
            "visual": adapted_strategy["visual"],
            "audio": adapted_strategy["audio"],
            "metadata": {
                "confidence": tone_analysis.get("confidence", 0.8),
                "adaptations": adapted_strategy.get("adaptations", [])
            }
        }
        
        print(f"   ✅ Selected strategy: {strategy_name}")
        print(f"   Tone: {tone_analysis.get('primary_tone', 'unknown')}")
        print(f"   Tempo: {adapted_strategy['pacing']['tempo']}x")
        
        return result
    
    async def _analyze_tone(self, script: str) -> Dict:
        """Analyze script tone using Gemini."""
        prompt = f"""
        Analyze the tone and style of this video script:
        
        "{script}"
        
        Determine:
        1. Primary tone (action, storytelling, educational, dramatic, funny)
        2. Energy level (low, medium, high)
        3. Pacing preference (slow, medium, fast)
        4. Key emotional beats (timestamps where emotion changes)
        
        Return JSON:
        {{
            "primary_tone": "action|storytelling|educational|dramatic|funny",
            "energy_level": "low|medium|high",
            "pacing": "slow|medium|fast",
            "confidence": 0.0-1.0,
            "keywords": ["keyword1", "keyword2"],
            "emotional_beats": ["description1", "description2"]
        }}
        """
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            
            import json
            analysis = json.loads(response.text)
            return analysis
        except Exception as e:
            print(f"   ⚠️ Tone analysis failed: {e}, using default")
            return {
                "primary_tone": "storytelling",
                "energy_level": "medium",
                "pacing": "medium",
                "confidence": 0.5,
                "keywords": [],
                "emotional_beats": []
            }
    
    def _select_strategy(self, tone_analysis: Dict) -> str:
        """Select strategy based on tone analysis."""
        tone = tone_analysis.get("primary_tone", "storytelling")
        energy = tone_analysis.get("energy_level", "medium")
        
        # Map tone to strategy
        if tone == "action" or energy == "high":
            return "action_packed"
        elif tone == "educational":
            return "educational"
        elif tone == "dramatic":
            return "dramatic"
        elif tone == "funny":
            return "action_packed"  # Fast-paced for comedy
        else:
            return "storytelling"  # Default
    
    def _adapt_to_assets(self, strategy: Dict, asset_catalog: Dict, parsed_script: Dict) -> Dict:
        """Adapt strategy based on available assets."""
        adapted = strategy.copy()
        adaptations = []
        
        # Check image count
        image_count = len(asset_catalog.get("catalog", {}).get("images", []))
        if image_count < 3:
            # Reduce image duration if few images
            adapted["visual"]["image_duration"] *= 1.5
            adaptations.append("Increased image duration (few images)")
        
        # Check video clip availability
        video_clips = asset_catalog.get("catalog", {}).get("video_clips", {})
        available_clips = sum(1 for c in video_clips.values() if c.get("available", False))
        
        if available_clips == 0:
            # No video clips - adjust overlap strategy
            adapted["audio"]["overlap_strategy"] = "none"
            adapted["audio"]["overlap_percentage"] = 0.0
            adaptations.append("Disabled overlap (no video clips)")
        
        # Check narration duration
        narration = asset_catalog.get("catalog", {}).get("narration", {})
        if narration.get("available") and narration.get("duration", 0) > 60:
            # Long narration - speed up more
            adapted["pacing"]["tempo"] = min(1.5, adapted["pacing"]["tempo"] * 1.2)
            adaptations.append("Increased tempo (long narration)")
        
        adapted["adaptations"] = adaptations
        return adapted
