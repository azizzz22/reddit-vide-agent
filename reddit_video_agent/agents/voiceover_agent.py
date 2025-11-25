import os
import base64
import requests
from typing import Dict, Any
from .base_agent import BaseAgent
from ..core.config import Config

class VoiceoverAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_key = Config.get_gemini_key()
        self.assets_dir = Config.ASSETS_DIR
        self.model_name = Config.TTS_MODEL
        self.voice_name = Config.TTS_VOICE

    async def execute(self, text: str, output_filename: str = "voiceover.mp3") -> str:
        """
        Generates audio using Playwright - FULLY AUTOMATED with exact XPaths.
        """
        print(f"VoiceoverAgent: Starting FULLY AUTOMATED audio generation for {output_filename}...")
        from ..core.browser_manager import BrowserManager
        
        try:
            page = await BrowserManager.ensure_logged_in()
            
            print("VoiceoverAgent: Navigating to AI Studio...")
            await page.goto("https://aistudio.google.com/app/prompts/new_chat")
            await page.wait_for_load_state("domcontentloaded")
            await page.wait_for_timeout(3000)
            
            # STEP 1: Click model selector
            print("VoiceoverAgent: Step 1 - Opening model selector...")
            try:
                model_selector = page.locator("xpath=/html/body/app-root/ms-app/div/div/div[3]/div/span/ms-prompt-renderer/ms-chunk-editor/ms-right-side-panel/div/ms-run-settings/div[2]/div/ms-prompt-run-settings-switcher/ms-prompt-run-settings/div[1]/div/ms-model-selector-v3/button")
                await model_selector.click(timeout=5000)
                await page.wait_for_timeout(1000)
                print("   ✅ Model selector opened")
            except Exception as e:
                print(f"   ⚠️  Could not open model selector: {e}")
            
            # STEP 2: Search for TTS
            print("VoiceoverAgent: Step 2 - Searching for TTS...")
            try:
                search_input = page.locator("xpath=/html/body/div[3]/div/div[2]/mat-dialog-container/div/div/mat-dialog-content/ms-model-carousel/ms-input-field/div/input")
                await search_input.fill("tts", timeout=5000)
                await page.wait_for_timeout(1000)
                print("   ✅ Searched for 'tts'")
            except Exception as e:
                print(f"   ⚠️  Could not search: {e}")
            
            # STEP 3: Select gemini-pro-preview-tts
            print("VoiceoverAgent: Step 3 - Selecting TTS model...")
            try:
                tts_model = page.locator("xpath=/html/body/div[3]/div/div[2]/mat-dialog-container/div/div/mat-dialog-content/ms-model-carousel/div/ms-model-carousel-row[1]/button")
                await tts_model.click(timeout=5000)
                await page.wait_for_timeout(2000)
                print("   ✅ TTS model selected")
            except Exception as e:
                print(f"   ⚠️  Could not select TTS model: {e}")
            
            # STEP 4: Select single-speaker audio
            print("VoiceoverAgent: Step 4 - Selecting single-speaker mode...")
            try:
                single_speaker = page.locator("xpath=/html/body/app-root/ms-app/div/div/div[3]/div/span/ms-speech-prompt/ms-right-side-panel/div/ms-run-settings/div[2]/div/ms-speech-run-settings/div[2]/ms-tts-mode-selector/ms-toggle-button[1]/button")
                await single_speaker.click(timeout=5000)
                await page.wait_for_timeout(500)
                print("   ✅ Single-speaker mode selected")
            except Exception as e:
                print(f"   ⚠️  Could not select single-speaker: {e}")
            
            # STEP 5: Open temperature dropdown
            print("VoiceoverAgent: Step 5 - Opening temperature settings...")
            try:
                temp_dropdown = page.locator("xpath=/html/body/app-root/ms-app/div/div/div[3]/div/span/ms-speech-prompt/ms-right-side-panel/div/ms-run-settings/div[2]/div/ms-speech-run-settings/div[3]/div/button")
                await temp_dropdown.click(timeout=5000)
                await page.wait_for_timeout(500)
                print("   ✅ Temperature dropdown opened")
            except Exception as e:
                print(f"   ⚠️  Could not open temperature: {e}")
            
            # STEP 6: Set temperature to 0.8
            print("VoiceoverAgent: Step 6 - Setting temperature to 0.8...")
            try:
                temp_slider = page.locator("xpath=/html/body/app-root/ms-app/div/div/div[3]/div/span/ms-speech-prompt/ms-right-side-panel/div/ms-run-settings/div[2]/div/ms-speech-run-settings/div[4]/div[2]/ms-slider/div/input")
                await temp_slider.fill("0.8", timeout=5000)
                await page.wait_for_timeout(500)
                print("   ✅ Temperature set to 0.8")
            except Exception as e:
                print(f"   ⚠️  Could not set temperature: {e}")
            
            # STEP 7: Open voice selector
            print("VoiceoverAgent: Step 7 - Opening voice selector...")
            try:
                voice_selector = page.locator("xpath=/html/body/app-root/ms-app/div/div/div[3]/div/span/ms-speech-prompt/ms-right-side-panel/div/ms-run-settings/div[2]/div/ms-speech-run-settings/div[5]/ms-voice-selector/div/mat-form-field/div[1]")
                await voice_selector.click(timeout=5000)
                await page.wait_for_timeout(1000)
                print("   ✅ Voice selector opened")
            except Exception as e:
                print(f"   ⚠️  Could not open voice selector: {e}")
            
            # STEP 8: Select Algeiba voice
            print("VoiceoverAgent: Step 8 - Selecting Algeiba voice...")
            try:
                algeiba_voice = page.locator("xpath=/html/body/div[3]/div/div[2]/div/mat-option[17]")
                await algeiba_voice.click(timeout=5000)
                await page.wait_for_timeout(500)
                print("   ✅ Algeiba voice selected")
            except Exception as e:
                print(f"   ⚠️  Could not select Algeiba: {e}")
            
            # STEP 9: Clear style instruction placeholder
            print("VoiceoverAgent: Step 9 - Clearing style instruction placeholder...")
            try:
                style_textarea = page.locator("xpath=/html/body/app-root/ms-app/div/div/div[3]/div/span/ms-speech-prompt/section/div[1]/div/ms-autosize-textarea")
                await style_textarea.click(timeout=5000)
                await page.keyboard.press("Meta+A")  # Command+A on Mac
                await page.keyboard.press("Backspace")
                await page.wait_for_timeout(300)
                print("   ✅ Style instruction cleared")
            except Exception as e:
                print(f"   ⚠️  Could not clear style: {e}")
            
            # STEP 10: Enter script text in the CORRECT textarea
            print("VoiceoverAgent: Step 10 - Entering script text...")
            try:
                # Use the exact selector for script narasi textarea
                script_textarea = page.locator("textarea[placeholder='Start writing or paste text here to generate speech']")
                await script_textarea.click(timeout=5000)
                await script_textarea.fill(text)
                print(f"   ✅ Script text entered")
                await page.wait_for_timeout(500)
            except Exception as e:
                print(f"   ⚠️  Could not enter text: {e}")
            
            # STEP 11: Click Run button
            print("VoiceoverAgent: Step 11 - Clicking Run button...")
            try:
                run_button = page.locator("xpath=/html/body/app-root/ms-app/div/div/div[3]/div/span/ms-speech-prompt/section/div[2]/div/div[2]/ms-run-button/button")
                await run_button.click(timeout=5000)
                print("   ✅ Run button clicked")
            except Exception as e:
                print(f"   ⚠️  Could not click Run: {e}")
                return None
            
            # STEP 12: Wait for audio generation and scrape from preview
            print("VoiceoverAgent: Step 12 - Waiting for audio generation...")
            output_path = os.path.join(self.assets_dir, output_filename)
            
            # Set up network listener to capture ALL audio-related requests
            audio_urls = []
            
            async def handle_response(response):
                nonlocal audio_urls
                url = response.url
                content_type = response.headers.get("content-type", "")
                
                # Log all responses for debugging
                if "audio" in content_type or "wav" in url.lower() or "mp3" in url.lower():
                    print(f"   🔍 Audio response detected:")
                    print(f"      URL: {url[:100]}...")
                    print(f"      Content-Type: {content_type}")
                    audio_urls.append(url)
            
            page.on("response", handle_response)
            
            # Wait for audio to be generated
            print("   Waiting for audio generation (up to 180 seconds)...")
            import asyncio
            wait_time = 0
            max_wait = 180
            
            while wait_time < max_wait:
                await asyncio.sleep(1)
                wait_time += 1
                
                # Check if audio element appeared
                try:
                    audio_elem = page.locator("audio").first
                    if await audio_elem.is_visible(timeout=100):
                        print(f"   ✅ Audio player appeared at {wait_time}s")
                        break
                except:
                    pass
                    
                if wait_time % 10 == 0:
                    print(f"   ... still waiting ({wait_time}s)")
            
            page.remove_listener("response", handle_response)
            
            # Try to download from captured URLs
            downloaded = False
            if audio_urls:
                print(f"   Found {len(audio_urls)} audio URL(s), trying to download...")
                for url in audio_urls:
                    try:
                        print(f"   Attempting download from: {url[:80]}...")
                        response = await page.request.get(url)
                        audio_data = await response.body()
                        
                        if len(audio_data) > 1000:  # Valid audio file
                            with open(output_path, "wb") as f:
                                f.write(audio_data)
                            print(f"   ✅ Audio downloaded! ({len(audio_data)} bytes)")
                            downloaded = True
                            break
                    except Exception as e:
                        print(f"   ⚠️  Failed: {e}")
                        continue
            
            # Fallback 1: Try to get from audio element src
            if not downloaded:
                print("   Trying to get audio from <audio> element...")
                try:
                    audio_element = page.locator("audio").first
                    if await audio_element.is_visible(timeout=5000):
                        src = await audio_element.get_attribute("src")
                        if src:
                            print(f"   Found audio src: {src[:80]}...")
                            
                            if src.startswith("data:"):
                                # Data URL (base64 encoded)
                                print("   ✅ Data URL detected, extracting base64...")
                                try:
                                    import base64
                                    import re
                                    # Extract base64 data from data URL
                                    match = re.match(r'data:.*?;base64,(.*)', src)
                                    if match:
                                        audio_bytes = base64.b64decode(match.group(1))
                                        with open(output_path, "wb") as f:
                                            f.write(audio_bytes)
                                        print(f"   ✅ Downloaded from data URL! ({len(audio_bytes)} bytes)")
                                        downloaded = True
                                    else:
                                        print("   ⚠️  Could not parse data URL")
                                except Exception as e:
                                    print(f"   ⚠️  Data URL extraction failed: {e}")
                                    
                            elif src.startswith("http"):
                                response = await page.request.get(src)
                                audio_data = await response.body()
                                with open(output_path, "wb") as f:
                                    f.write(audio_data)
                                print(f"   ✅ Downloaded from audio element!")
                                downloaded = True
                            elif src.startswith("blob:"):
                                print("   ⚠️  Blob URL detected, trying alternative method...")
                                # Try to use CDP to resolve blob URL
                                try:
                                    # Execute JavaScript to fetch blob data
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
                                        # Remove data URL prefix
                                        import base64
                                        import re
                                        match = re.match(r'data:.*?;base64,(.*)', base64_data)
                                        if match:
                                            audio_bytes = base64.b64decode(match.group(1))
                                            with open(output_path, "wb") as f:
                                                f.write(audio_bytes)
                                            print(f"   ✅ Downloaded blob via JavaScript!")
                                            downloaded = True
                                except Exception as e:
                                    print(f"   ⚠️  Blob extraction failed: {e}")
                except Exception as e:
                    print(f"   ⚠️  Audio element method failed: {e}")
            
            # Check result
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                size = os.path.getsize(output_path)
                print(f"\n✅ SUCCESS! Audio generated: {size} bytes")
                return output_path
            else:
                print("\n❌ FAILED: Could not capture audio automatically")
                print("   Debug info:")
                print(f"   - Audio URLs captured: {len(audio_urls)}")
                if audio_urls:
                    for i, url in enumerate(audio_urls[:3]):
                        print(f"     {i+1}. {url[:100]}")
                return None

        except Exception as e:
            print(f"\n❌ Error in VoiceoverAgent: {e}")
            import traceback
            traceback.print_exc()
            return None
