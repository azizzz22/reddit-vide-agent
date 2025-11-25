import asyncio
import os
from reddit_video_agent.core.config import Config
from reddit_video_agent.agents.visual_agent import VisualAgent
from reddit_video_agent.core.browser_manager import BrowserManager

async def test_visual():
    print("🧪 Testing Visual Agent Automation...")
    
    # Initialize
    config = {}
    agent = VisualAgent(config)
    
    # Sample script
    script = "Robot humanoid yang bergerak super cepat dan keren banget!"
    
    # Execute
    try:
        images = await agent.execute(script)
        
        if images:
            print(f"✅ Success! Generated {len(images)} images:")
            for img in images:
                if os.path.exists(img):
                    size = os.path.getsize(img)
                    print(f"   - {img} ({size} bytes)")
        else:
            print("❌ Failed to generate images.")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
    finally:
        await BrowserManager.close()

if __name__ == "__main__":
    asyncio.run(test_visual())
