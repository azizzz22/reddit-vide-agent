import os
import requests
from typing import Dict, Any, List
from rembg import remove
from PIL import Image
import io
import google.generativeai as genai
from .base_agent import BaseAgent
from ..core.config import Config

class VisualAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = Config.get_gemini_key()
        self.assets_dir = Config.ASSETS_DIR
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(Config.SCRIPT_MODEL)  # For keyword extraction

    async def execute(self, script_data: Any, video_path: str = None, full_context: Dict = None) -> List[str]:
        """
        Generates visual assets based on the script and context.
        Supports both old format (string) and new format (dict with markers).
        """
        print("VisualAgent: Generating visuals...")
        
        # Handle backward compatibility
        if isinstance(script_data, str):
            script = script_data
            visual_markers = []
        elif isinstance(script_data, dict):
            script = script_data.get("script", "")
            visual_markers = script_data.get("visual_markers", [])
        else:
            script = str(script_data)
            visual_markers = []
        
        # 1. Extract prompts (prioritize markers if available)
        if visual_markers:
            # Filter out screenshot markers (they're already available)
            screenshot_markers = [m for m in visual_markers if m["type"] == "screenshot"]
            image_markers = [m for m in visual_markers if m["type"] != "screenshot"]
            
            if screenshot_markers:
                print(f"   Found {len(screenshot_markers)} screenshot markers (using existing screenshots)")
            
            if image_markers:
                print(f"   Using {len(image_markers)} context-aware visual markers")
                prompts = self._create_prompts_from_markers(image_markers, full_context)
            else:
                print("   No visual markers found, using generic extraction")
                prompts = self._extract_prompts(script, full_context)
        else:
            print("   No visual markers found, using generic extraction")
            prompts = self._extract_prompts(script, full_context)
        
        print(f"   Extracted {len(prompts)} visual prompts")
        
        generated_images = []
        
        # 2. Generate Images
        for i, prompt in enumerate(prompts):
            print(f"\n📸 Generating image {i+1}/{len(prompts)}: {prompt[:80]}...")
            image_path = await self._generate_image(prompt, i)
            if image_path:
                # 3. Process Image (Remove Background & Resize)
                processed_path = self._process_image(image_path)
                generated_images.append(processed_path)
            else:
                print(f"   ⚠️  Failed to generate image for: {prompt}")
                
        print(f"\n✅ Generated {len(generated_images)} images total")
        return generated_images

    def _extract_prompts(self, text: str, full_context: Dict = None) -> List[str]:
        """
        Extract visual prompts using Gemini, now with FULL CONTEXT.
        """
        print("   🧠 VisualAgent: Analyzing text for visual prompts...")
        
        # Default context if not provided
        if not full_context:
            full_context = {
                "title": "Unknown Title",
                "content": "No content",
                "comments": "No comments"
            }
            
        prompt = f"""
        You are an expert Art Director for viral videos.
        
        TASK: Create 3-5 highly specific image prompts based on this video script and context.
        
        CONTEXT:
        Title: {full_context.get('title')}
        Content: {full_context.get('content')}
        Script: {text}
        Comments: {full_context.get('comments')}
        
        STYLE GUIDE:
        - Analyze the TONE of the content (e.g., Extreme Sports, Funny, Tech, Heartwarming).
        - Choose a visual style that fits (e.g., Realistic Action, Cartoon, Minimalist, Watercolor).
        - If the script mentions specific brands (e.g., "Red Bull"), INCLUDE them.
        - If there's a punchline, visualize it.
        
        CRITICAL REQUIREMENT FOR COMPOSITING:
        - All subjects must be CENTERED.
        - All subjects must have a WHITE BACKGROUND.
        - All subjects must have 50px PADDING on all sides (offset).
        - Subjects must be ISOLATED (easy to remove background).
        
        OUTPUT FORMAT:
        Return ONLY a JSON list of strings.
        Example:
        [
            "Realistic action shot of a snowboarder doing a backflip, Red Bull helmet visible, centered, isolated on white background, 50px padding, 8k resolution",
            "Close up of a shocked cartoon face, exaggerated expression, centered, isolated on white background, 50px padding"
        ]
        """
        
        try:
            response = self.model.generate_content(prompt)
            
            # Try to parse JSON first
            import json
            try:
                # Clean up markdown code blocks if present
                clean_text = response.text.replace('```json', '').replace('```', '').strip()
                prompts = json.loads(clean_text)
                if isinstance(prompts, list):
                    return prompts[:5]
            except:
                pass
                
            # Fallback to pipe splitting if JSON fails
            keywords = [k.strip() for k in response.text.split('|')]
            keywords = [k.replace('```', '').replace('*', '').strip() for k in keywords]
            keywords = [k for k in keywords if k and len(k) > 10]
            return keywords[:5]
            
        except Exception as e:
            print(f"   ⚠️ Prompt extraction failed: {e}")
            return ["Dramatic action scene, cinematic, white background",
                    "Surprised expression close-up, intense, white background",
                    "Epic wide shot, heroic moment, white background"]

    async def _generate_image(self, prompt: str, index: int) -> str:
        """Generates an image using Playwright automation in AI Studio - FULLY AUTOMATED."""
        from ..core.browser_manager import BrowserManager
        
        try:
            page = await BrowserManager.ensure_logged_in()
            
            # Navigate to Imagen model URL
            print("   Navigating to Imagen model...")
            await page.goto("https://aistudio.google.com/app/prompts/new_chat?model=gemini-2.5-flash-image")
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(3000)
            
            # Enter prompt in textarea
            print(f"   Entering prompt: '{prompt[:50]}...'")
            try:
                prompt_textarea = page.locator("xpath=/html/body/app-root/ms-app/div/div/div[3]/div/span/ms-prompt-renderer/ms-chunk-editor/section/footer/ms-prompt-input-wrapper/div/div/div/div[2]/ms-chunk-input/section/div/ms-text-chunk/ms-autosize-textarea/textarea")
                await prompt_textarea.click(timeout=5000)
                await prompt_textarea.fill(f"{prompt}")
                print("   ✅ Prompt entered")
            except Exception as e:
                print(f"   ⚠️  Could not enter prompt: {e}")
                return None
            
            await page.wait_for_timeout(500)
            
            # Click Run button
            print("   Clicking Run button...")
            try:
                run_button = page.locator("xpath=/html/body/app-root/ms-app/div/div/div[3]/div/span/ms-prompt-renderer/ms-chunk-editor/section/footer/ms-prompt-input-wrapper/div/div/div/div[4]/ms-run-button/button")
                await run_button.click(timeout=5000)
                print("   ✅ Run button clicked")
            except Exception as e:
                print(f"   ⚠️  Could not click Run: {e}")
                return None
            
            # Wait for image generation
            print("   Waiting for image generation (up to 60 seconds)...")
            import asyncio
            
            # Wait for the image element to appear
            image_found = False
            wait_time = 0
            max_wait = 60
            
            while wait_time < max_wait and not image_found:
                await asyncio.sleep(1)
                wait_time += 1
                
                # Try to find the generated image
                try:
                    # Use a more flexible selector since chat-turn index might vary
                    img_selector = "ms-chat-turn ms-image-chunk img"
                    img_element = page.locator(img_selector).last  # Get the last (most recent) image
                    
                    if await img_element.is_visible(timeout=100):
                        image_found = True
                        print(f"   ✅ Image appeared at {wait_time}s")
                        break
                except:
                    pass
                
                if wait_time % 10 == 0:
                    print(f"   ... still waiting ({wait_time}s)")
            
            if not image_found:
                print("   ⚠️  Image generation timeout")
                return None
            
            # Download the image
            print("   Downloading image...")
            filename = f"gen_image_{index}.png"
            output_path = os.path.join(self.assets_dir, filename)
            
            try:
                # Wait a bit more to ensure image is fully loaded
                await asyncio.sleep(2)
                
                # Get the image src - try multiple times
                img_element = None
                src = None
                
                for attempt in range(3):
                    try:
                        img_element = page.locator("ms-chat-turn ms-image-chunk img").last
                        src = await img_element.get_attribute("src", timeout=5000)
                        if src:
                            break
                        await asyncio.sleep(1)
                    except:
                        if attempt < 2:
                            print(f"   Retry {attempt + 1}/3...")
                            await asyncio.sleep(2)
                        continue
                
                if not src:
                    print("   ⚠️  Could not get image src after retries")
                    return None
                
                print(f"   Found image src: {src[:80]}...")
                
                if src.startswith("data:"):
                    # Data URL (base64)
                    print("   ✅ Data URL detected, extracting...")
                    import base64
                    import re
                    match = re.match(r'data:.*?;base64,(.*)', src)
                    if match:
                        image_bytes = base64.b64decode(match.group(1))
                        with open(output_path, "wb") as f:
                            f.write(image_bytes)
                        print(f"   ✅ Image saved! ({len(image_bytes)} bytes)")
                        return output_path
                    else:
                        print("   ⚠️  Could not parse data URL")
                        return None
                
                elif src.startswith("http"):
                    # HTTP URL
                    print("   Downloading from URL...")
                    response = await page.request.get(src)
                    image_data = await response.body()
                    with open(output_path, "wb") as f:
                        f.write(image_data)
                    print(f"   ✅ Image saved! ({len(image_data)} bytes)")
                    return output_path
                
                elif src.startswith("blob:"):
                    # Blob URL - extract via JavaScript
                    print("   Blob URL detected, extracting via JavaScript...")
                    js_code = f"""
                    async function getBlobData() {{
                        const response = await fetch('{src}');
                        const blob = await response.blob();
                        const reader = new FileReader();
                        return new Promise((resolve) => {{
                            reader.onloadend = () => resolve(reader.result);
                            reader.readAsDataURL(blob);
                        }});
                    }}
                    getBlobData();
                    """
                    base64_data = await page.evaluate(js_code)
                    if base64_data:
                        import base64
                        import re
                        match = re.match(r'data:.*?;base64,(.*)', base64_data)
                        if match:
                            image_bytes = base64.b64decode(match.group(1))
                            with open(output_path, "wb") as f:
                                f.write(image_bytes)
                            print(f"   ✅ Image saved from blob! ({len(image_bytes)} bytes)")
                            return output_path
                
                print("   ⚠️  Unknown src format")
                return None
                
            except Exception as e:
                print(f"   ⚠️  Error downloading image: {e}")
                return None

        except Exception as e:
            print(f"   ❌ Error in image generation: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _process_image(self, image_path: str) -> str:
        """Resize image (background removal disabled to preserve details)."""
        try:
            print(f"   Processing image: {os.path.basename(image_path)}")
            output_path = image_path.replace(".png", "_processed.png")
            
            # Skip background removal - it removes important details
            # Just resize to reasonable size
            with Image.open(image_path) as img:
                # Resize while maintaining aspect ratio
                img.thumbnail((800, 800))
                img.save(output_path)
            
            print(f"   ✅ Image processed: {os.path.basename(output_path)}")
            return output_path
            
        except Exception as e:
            print(f"   ⚠️  Error processing image: {e}")
            return image_path  # Return original if processing fails

    def _create_prompts_from_markers(self, markers: List[Dict], full_context: Dict = None) -> List[str]:
        """
        Create context-aware image prompts from visual markers.
        """
        prompts = []
        
        for marker in markers:
            description = marker.get("description", "")
            marker_id = marker.get("id", "")
            
            # Enhance description with context
            enhanced_prompt = f"""
            Highly detailed studio image of {description}, 
            professional photography, 8k resolution, 
            centered composition, isolated on white background, 
            50px padding on all sides, perfect for video compositing.
            """
            
            prompts.append(enhanced_prompt.strip())
            print(f"   Created prompt for marker '{marker_id}': {description}")
        
        return prompts
