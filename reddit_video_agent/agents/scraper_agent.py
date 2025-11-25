import os
import asyncio
from typing import Dict, Any
from playwright.async_api import async_playwright
import yt_dlp
from .base_agent import BaseAgent
from ..core.config import Config

class ScraperAgent(BaseAgent):
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.assets_dir = Config.ASSETS_DIR

    async def execute(self, url: str) -> Dict[str, Any]:
        """
        Scrapes Reddit post, takes screenshots, and downloads video.
        """
        print(f"ScraperAgent: Processing {url}")
        
        result = {
            "title": "",
            "content": "",
            "post_screenshot": "",
            "comment_screenshots": [],
            "video_path": None
        }

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True) # Set headless=False for debugging
            context = await browser.new_context(
                viewport={"width": 1080, "height": 1920}, # Mobile-ish view for better screenshots? Or desktop? Let's stick to desktop for clarity then crop.
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            )
            page = await context.new_page()
            try:
                await page.goto(url, timeout=60000)
                # Reddit is heavy, networkidle is too strict.
                await page.wait_for_load_state("domcontentloaded", timeout=60000)
                # Optional: wait for a specific element to ensure content is there
                try:
                    await page.wait_for_selector("shreddit-post", timeout=10000)
                except:
                    pass
            except Exception as e:
                print(f"Warning: Page load timed out or failed: {e}")
                # Continue anyway to try downloading video or extracting what's there

            # 1. Extract Text
            # Selectors might need adjustment based on Reddit's dynamic classes. 
            # Using generic attributes where possible.
            try:
                # Title - usually inside an h1
                title_element = await page.query_selector("h1")
                if title_element:
                    result["title"] = await title_element.inner_text()
                
                # Content - usually in a div with specific ID or class
                # This is tricky on new Reddit.
                # Let's try to grab the main post container's text if specific selector fails.
                post_content_element = await page.query_selector("div[data-test-id='post-content']")
                if post_content_element:
                     result["content"] = await post_content_element.inner_text()
            except Exception as e:
                print(f"Error extracting text: {e}")

            # 2. Screenshots
            # Post Screenshot
            # We want to capture the header and the body.
            try:
                # Wait for the post content to load
                await page.wait_for_selector("shreddit-post", timeout=10000)
                
                # Take screenshot of the main post container
                post_element = await page.query_selector("shreddit-post")
                if post_element:
                    import uuid
                    unique_id = str(uuid.uuid4())[:8]
                    screenshot_path = os.path.join(self.assets_dir, f"post_screenshot_{unique_id}.png")
                    await post_element.screenshot(path=screenshot_path)
                    result["post_screenshot"] = screenshot_path
            except Exception as e:
                print(f"Error taking post screenshot: {e}")

            # 2. Extract Comments (Text & Screenshots)
            print("   Scraping comments...")
            comments_data = [] # To store text for scriptwriter
            comment_screenshots = []
            
            try:
                # Wait for comments to load
                await page.wait_for_selector("shreddit-comment", timeout=10000)
                
                # Get all top-level comments (or comment trees)
                # In new Reddit, shreddit-comment-tree often wraps the thread
                # But shreddit-comment is the individual comment.
                # We want to capture the visual "block" of a conversation.
                
                # Strategy: Find top-level comments, check if they are not deleted, 
                # then take a screenshot of the thread (or the comment + its first reply).
                
                comment_elements = await page.query_selector_all("shreddit-comment[depth='0']")
                
                count = 0
                for i, comment in enumerate(comment_elements):
                    if count >= 3: # Limit to top 3 threads
                        break
                        
                    # Check for deleted/removed
                    author = await comment.get_attribute("author")
                    if author == "[deleted]" or author == "[removed]":
                        continue
                        
                    # Extract text content for Scriptwriter
                    # The text is usually in a slot="comment" or specific div
                    text_content = await comment.inner_text()
                    
                    # Clean up text (remove UI elements like "Reply", "Share")
                    lines = [line.strip() for line in text_content.split('\n') if line.strip()]
                    # Heuristic: Take the longest line or combine lines that look like content
                    clean_text = " ".join(lines[:5]) # Take first few lines
                    
                    # Check for nested replies (children)
                    # We want to capture the conversation flow
                    # Try to find the next sibling or nested tree
                    # Taking screenshot of the 'comment' element usually captures children if they are expanded.
                    
                    # Screenshot
                    import uuid
                    unique_id = str(uuid.uuid4())[:8]
                    screenshot_filename = f"comment_thread_{count}_{unique_id}.png"
                    screenshot_path = os.path.join(self.assets_dir, screenshot_filename)
                    
                    # Scroll into view
                    await comment.scroll_into_view_if_needed()
                    await page.wait_for_timeout(500) # Wait for render
                    
                    await comment.screenshot(path=screenshot_path)
                    comment_screenshots.append(screenshot_path)
                    
                    comments_data.append({
                        "author": author,
                        "text": clean_text
                    })
                    
                    count += 1
                    print(f"   ✅ Captured comment thread {count}")
            
            except Exception as e:
                print(f"   ⚠️ Error scraping comments: {e}")

            result["comments_text"] = comments_data
            result["comment_screenshots"] = comment_screenshots

            await browser.close()
            
        # 3. Download Video (if applicable)
        # We use yt-dlp which handles Reddit videos very well
        try:
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            
            ydl_opts = {
                'outtmpl': os.path.join(self.assets_dir, f'video_{unique_id}.%(ext)s'),
                'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'quiet': True,
                'no_warnings': True
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                
                if info.get('vcodec') != 'none':
                    ydl.download([url])
                    # Find the file (since extension might vary)
                    # We forced mp4 preference but yt-dlp might still use mkv if mp4 unavailable
                    # Let's look for the file with our unique_id
                    import glob
                    potential_files = glob.glob(os.path.join(self.assets_dir, f'video_{unique_id}.*'))
                    if potential_files:
                        video_path = potential_files[0]
                        result["video_path"] = video_path
                        
                        # 4. Process Thumbnail Insertion
                        if result["post_screenshot"] and os.path.exists(result["post_screenshot"]):
                            try:
                                self._insert_video_thumbnail(video_path, result["post_screenshot"])
                            except Exception as e:
                                print(f"Failed to insert video thumbnail: {e}")
        except Exception as e:
            print(f"Video download failed or no video found: {e}")

        return result

    def _insert_video_thumbnail(self, video_path: str, screenshot_path: str):
        """
        Creates a FRAME from the screenshot by making the video player area TRANSPARENT.
        This allows the video thumbnail to show through from the layer below.
        
        Strategy:
        1. Detect dark/black area in screenshot (video player placeholder)
        2. Make that area transparent
        3. Save as PNG with alpha channel (frame with hole)
        4. Video thumbnail will be placed in layer below during editing
        """
        from PIL import Image, ImageDraw
        import numpy as np
        
        print("   Creating transparent frame from screenshot...")
        try:
            # Load screenshot
            screenshot = Image.open(screenshot_path).convert("RGBA")
            width, height = screenshot.size
            
            # Convert to numpy for easier processing
            img_array = np.array(screenshot)
            
            # Strategy: Find large dark rectangular area (video player)
            # Reddit video players are typically:
            # - Black or very dark gray
            # - Rectangular
            # - In the middle-lower portion of the post
            
            # Create mask for dark pixels
            # Dark pixels: RGB values all < 50
            r, g, b, a = img_array[:,:,0], img_array[:,:,1], img_array[:,:,2], img_array[:,:,3]
            dark_mask = (r < 50) & (g < 50) & (b < 50)
            
            # Find the largest contiguous dark region
            # Simplified approach: Find bounding box of dark region in middle area
            
            # Focus on middle 60% of image (where video player usually is)
            middle_start_y = int(height * 0.2)
            middle_end_y = int(height * 0.8)
            
            # Find dark pixels in middle region
            middle_dark = dark_mask[middle_start_y:middle_end_y, :]
            
            # Find columns and rows with significant dark pixels
            dark_cols = np.where(middle_dark.sum(axis=0) > (middle_end_y - middle_start_y) * 0.3)[0]
            dark_rows = np.where(middle_dark.sum(axis=1) > width * 0.3)[0]
            
            if len(dark_cols) > 0 and len(dark_rows) > 0:
                # Found video player area!
                player_left = dark_cols[0]
                player_right = dark_cols[-1]
                player_top = dark_rows[0] + middle_start_y
                player_bottom = dark_rows[-1] + middle_start_y
                
                # Add some padding to ensure we get the whole player
                padding = 10
                player_left = max(0, player_left - padding)
                player_right = min(width, player_right + padding)
                player_top = max(0, player_top - padding)
                player_bottom = min(height, player_bottom + padding)
                
                # Make this area TRANSPARENT
                img_array[player_top:player_bottom, player_left:player_right, 3] = 0  # Set alpha to 0
                
                print(f"   ✅ Video player area detected: ({player_left},{player_top}) to ({player_right},{player_bottom})")
                print(f"   ✅ Made area transparent - screenshot is now a FRAME!")
                
                # Save the frame
                frame_image = Image.fromarray(img_array, 'RGBA')
                frame_image.save(screenshot_path)
                
                # Also save the player dimensions for EditorAgent to use
                frame_info_path = screenshot_path.replace('.png', '_frame_info.txt')
                with open(frame_info_path, 'w') as f:
                    f.write(f"{player_left},{player_top},{player_right},{player_bottom}")
                
            else:
                print("   ⚠️ Could not detect video player area - screenshot unchanged")
                # Fallback: Create a generic transparent rectangle in the middle
                # This ensures we at least have some transparency
                center_x = width // 2
                center_y = int(height * 0.5)
                rect_width = int(width * 0.85)
                rect_height = int(height * 0.4)
                
                left = center_x - rect_width // 2
                top = center_y - rect_height // 2
                right = left + rect_width
                bottom = top + rect_height
                
                img_array[top:bottom, left:right, 3] = 0
                
                frame_image = Image.fromarray(img_array, 'RGBA')
                frame_image.save(screenshot_path)
                print(f"   ⚠️ Used fallback: Created generic transparent area in center")
            
        except Exception as e:
            print(f"   ⚠️ Error creating frame: {e}")
            import traceback
            traceback.print_exc()
