import asyncio
import os
from reddit_video_agent.core.config import Config
from reddit_video_agent.agents.clipper_agent import ClipperAgent

async def test_clipper():
    print("🧪 Testing Clipper Agent...")
    
    config = {}
    agent = ClipperAgent(config)
    
    video_path = os.path.join(Config.ASSETS_DIR, "downloaded_video.mp4")
    
    if not os.path.exists(video_path):
        print("❌ downloaded_video.mp4 not found! Please run scraper test first.")
        return

    try:
        clips = await agent.execute(video_path)
        
        if clips:
            print("\n✅ Clips created:")
            for key, path in clips.items():
                size = os.path.getsize(path)
                print(f"   - {key}: {os.path.basename(path)} ({size/1024:.2f} KB)")
        else:
            print("\n❌ No clips created.")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_clipper())
