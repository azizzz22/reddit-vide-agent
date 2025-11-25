import asyncio
import os
from reddit_video_agent.core.config import Config
from reddit_video_agent.agents.voiceover_agent import VoiceoverAgent
from reddit_video_agent.core.browser_manager import BrowserManager

async def test_voiceover():
    print("🧪 Testing Voiceover Agent Automation...")
    
    # Initialize
    config = {}
    agent = VoiceoverAgent(config)
    
    # Sample Text
    text = "Halo, ini adalah tes suara menggunakan Google AI Studio automation. Suara ini harusnya terdengar lebay dan periang!"
    
    # Execute
    try:
        output_path = await agent.execute(text)
        
        if output_path and os.path.exists(output_path):
            print(f"✅ Success! Audio saved to: {output_path}")
            # Verify size
            size = os.path.getsize(output_path)
            print(f"   File size: {size} bytes")
        else:
            print("❌ Failed to generate audio.")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
    finally:
        await BrowserManager.close()

if __name__ == "__main__":
    asyncio.run(test_voiceover())
