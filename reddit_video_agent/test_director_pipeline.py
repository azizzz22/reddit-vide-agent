import asyncio
import json
from reddit_video_agent.core.config import Config
from reddit_video_agent.agents.director import Director

async def test_director_pipeline():
    print("🧪 Testing Director 4-Stage Fine-Tuning Pipeline...")
    
    config = {}
    director = Director(config)
    
    url = "https://www.reddit.com/r/nextfuckinglevel/comments/1ny8m4t/is_she_slicing_the_paper_with_a_wooden_sword/"
    
    try:
        print("\n🎬 Starting full pipeline test...")
        final_video = await director.execute(url)
        
        if final_video:
            print(f"\n✅ SUCCESS! Video created: {final_video}")
            
            # Check if timeline was created
            import os
            timeline_path = os.path.join(Config.ASSETS_DIR, "timeline.json")
            if os.path.exists(timeline_path):
                with open(timeline_path, 'r') as f:
                    timeline = json.load(f)
                    print(f"\n📋 Timeline Summary:")
                    print(f"   Total Duration: {timeline.get('total_duration', 0):.2f}s")
                    print(f"   Layers: {len(timeline.get('layers', []))}")
                    
                    # Show first few layers
                    for i, layer in enumerate(timeline.get('layers', [])[:5]):
                        print(f"   Layer {i+1}: {layer.get('type')} at {layer.get('start'):.1f}s-{layer.get('end'):.1f}s")
                    
                    if len(timeline.get('layers', [])) > 5:
                        print(f"   ... and {len(timeline['layers']) - 5} more layers")
        else:
            print("\n❌ FAILED: No video created")
            
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_director_pipeline())
