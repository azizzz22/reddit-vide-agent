import asyncio
import os
from reddit_video_agent.core.config import Config
from reddit_video_agent.agents.audio_agent import AudioAgent

async def regenerate_captions():
    print("🔄 Regenerating captions with Whisper...")
    
    config = {}
    agent = AudioAgent(config)
    
    audio_path = os.path.join(Config.ASSETS_DIR, "voiceover.mp3")
    
    if not os.path.exists(audio_path):
        print("❌ voiceover.mp3 not found!")
        return

    try:
        # Force regeneration
        result = await agent.execute(audio_path)
        print(f"✅ Captions regenerated at: {result['captions_path']}")
        
        # Verify content
        with open(result['captions_path'], 'r') as f:
            print("\n📄 Caption Preview:")
            print(f.read()[:200] + "...")
            
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(regenerate_captions())
