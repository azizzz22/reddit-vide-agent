import asyncio
import os
from reddit_video_agent.core.config import Config
from reddit_video_agent.agents.editor_agent import EditorAgent

async def test_editor():
    print("🧪 Testing Editor Agent (Phase 1)...")
    
    # Initialize
    config = {}
    agent = EditorAgent(config)
    
    # Prepare test assets
    assets = {
        "voiceover_path": os.path.join(Config.ASSETS_DIR, "voiceover.mp3"),
        "captions_path": os.path.join(Config.ASSETS_DIR, "captions.srt"),
        "images": [
            os.path.join(Config.ASSETS_DIR, "gen_image_0_processed.png"),
            os.path.join(Config.ASSETS_DIR, "gen_image_1_processed.png"),
            os.path.join(Config.ASSETS_DIR, "gen_image_2_processed.png"),
        ],
        "post_screenshot": os.path.join(Config.ASSETS_DIR, "post_screenshot.png"),
        "video_path": os.path.join(Config.ASSETS_DIR, "downloaded_video.mp4")  # Reddit video as background
    }
    
    # Check if assets exist
    print("\n📁 Checking assets...")
    for key, value in assets.items():
        if value:
            if isinstance(value, list):
                for item in value:
                    exists = os.path.exists(item)
                    print(f"   {key}: {os.path.basename(item)} - {'✅' if exists else '❌'}")
            else:
                exists = os.path.exists(value)
                print(f"   {key}: {os.path.basename(value)} - {'✅' if exists else '❌'}")
    
    # Execute
    print("\n🎬 Starting video composition...")
    try:
        output_path = await agent.execute(assets)
        
        if output_path and os.path.exists(output_path):
            size = os.path.getsize(output_path)
            print(f"\n✅ SUCCESS! Video created:")
            print(f"   Path: {output_path}")
            print(f"   Size: {size / 1024 / 1024:.2f} MB")
            print(f"\n🎥 Opening video...")
            os.system(f"open '{output_path}'")
        else:
            print("\n❌ Failed to create video.")
            
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_editor())
