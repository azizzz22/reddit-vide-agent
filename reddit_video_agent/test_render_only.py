import asyncio
import os
import glob
from reddit_video_agent.core.config import Config
from reddit_video_agent.agents.editor_agent import EditorAgent
from reddit_video_agent.agents.director import Director

async def test_rendering_only():
    print("🎬 Testing Rendering Only (Using Existing Assets)...")
    
    # Check if assets exist
    assets_dir = Config.ASSETS_DIR
    
    voiceover = os.path.join(assets_dir, "voiceover.mp3")
    captions = os.path.join(assets_dir, "captions.srt")
    timeline = os.path.join(assets_dir, "timeline.json")
    
    if not os.path.exists(voiceover):
        print("❌ voiceover.mp3 not found!")
        return
    
    if not os.path.exists(captions):
        print("❌ captions.srt not found!")
        return
    
    print(f"✅ Found voiceover: {os.path.getsize(voiceover)} bytes")
    print(f"✅ Found captions: {os.path.getsize(captions)} bytes")
    
    # Collect all assets
    video_files = glob.glob(os.path.join(assets_dir, "video_*.mp4"))
    clip_files = glob.glob(os.path.join(assets_dir, "clip_*.mp4"))
    image_files = glob.glob(os.path.join(assets_dir, "gen_image_*_processed.png"))
    post_screenshot = glob.glob(os.path.join(assets_dir, "post_screenshot_*.png"))
    comment_screenshots = glob.glob(os.path.join(assets_dir, "comment_thread_*.png"))
    
    print(f"\n📦 Assets Found:")
    print(f"   Videos: {len(video_files)}")
    print(f"   Clips: {len(clip_files)}")
    print(f"   AI Images: {len(image_files)}")
    print(f"   Post Screenshot: {len(post_screenshot)}")
    print(f"   Comment Screenshots: {len(comment_screenshots)}")
    
    # Prepare assets dict
    assets = {
        "voiceover_path": voiceover,
        "captions_path": captions,
        "images": image_files,
        "post_screenshot": post_screenshot[0] if post_screenshot else None,
        "comment_screenshots": comment_screenshots,
        "video_path": video_files[0] if video_files else None,
        "video_clips": {},
        "sound_effects": []
    }
    
    # Add clips as dict with metadata
    for clip_file in clip_files:
        clip_name = os.path.basename(clip_file).replace(".mp4", "").replace("clip_", "")
        assets["video_clips"][clip_name] = {
            "path": clip_file,
            "description": f"{clip_name} clip",
            "duration": 0  # Will be calculated by Director
        }
    
    # Load timeline if exists
    if os.path.exists(timeline):
        import json
        with open(timeline, 'r') as f:
            assets["timeline"] = json.load(f)
        print(f"✅ Loaded timeline with {len(assets['timeline'].get('layers', []))} layers")
    else:
        print("⚠️  No timeline found, will use fallback distribution")
    
    # Render!
    print("\n🎬 Starting Rendering...")
    editor = EditorAgent({})
    
    try:
        output_path = await editor.execute(assets)
        
        if output_path and os.path.exists(output_path):
            print(f"\n✅ SUCCESS! Video created: {output_path}")
            print(f"   File size: {os.path.getsize(output_path) / 1024 / 1024:.2f} MB")
        else:
            print("\n❌ FAILED: No video created")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_rendering_only())
