import asyncio
import os
import glob
import json
from reddit_video_agent.core.config import Config
from reddit_video_agent.core.timeline_builder import AudioDrivenTimelineBuilder

async def test_audio_timeline():
    print("🎯 Testing Audio-Driven Timeline Builder...")
    
    assets_dir = Config.ASSETS_DIR
    
    # Check required files
    voiceover = os.path.join(assets_dir, "voiceover.mp3")
    captions = os.path.join(assets_dir, "captions.srt")
    
    if not os.path.exists(captions):
        print("❌ captions.srt not found!")
        return
    
    # Collect assets
    video_files = glob.glob(os.path.join(assets_dir, "video_*.mp4"))
    clip_files = glob.glob(os.path.join(assets_dir, "clip_*.mp4"))
    image_files = glob.glob(os.path.join(assets_dir, "gen_image_*_processed.png"))
    post_screenshot = glob.glob(os.path.join(assets_dir, "post_screenshot_*.png"))
    comment_screenshots = glob.glob(os.path.join(assets_dir, "comment_thread_*.png"))
    
    # Prepare assets dict
    assets = {
        "post_screenshot": post_screenshot[0] if post_screenshot else None,
        "comment_screenshots": comment_screenshots,
        "images": image_files,
        "video_path": video_files[0] if video_files else None,
        "video_clips": {}
    }
    
    # Add clips
    for clip_file in clip_files:
        clip_name = os.path.basename(clip_file).replace(".mp4", "").replace("clip_", "")
        assets["video_clips"][clip_name] = {
            "path": clip_file,
            "description": f"{clip_name} clip",
            "duration": 0
        }
    
    # Get audio duration
    if os.path.exists(voiceover):
        from moviepy.editor import AudioFileClip
        audio = AudioFileClip(voiceover)
        duration = audio.duration
        audio.close()
    else:
        duration = 60.0
    
    # Build timeline
    builder = AudioDrivenTimelineBuilder()
    timeline = builder.build_timeline(
        srt_path=captions,
        assets=assets,
        total_duration=duration
    )
    
    # Display results
    print(f"\n📊 Timeline Summary:")
    print(f"   Total Duration: {timeline['total_duration']:.2f}s")
    print(f"   Total Layers: {len(timeline['layers'])}")
    
    print(f"\n📋 Layer Details:")
    for i, layer in enumerate(timeline['layers']):
        print(f"   {i+1}. [{layer['start']:.1f}s-{layer['end']:.1f}s] {layer['type']}: {layer['asset_name']}")
        print(f"      Reason: {layer['reason']}")
    
    # Save
    output_path = os.path.join(assets_dir, "timeline_audio_driven.json")
    with open(output_path, 'w') as f:
        json.dump(timeline, f, indent=2)
    
    print(f"\n✅ Timeline saved to: {output_path}")

if __name__ == "__main__":
    asyncio.run(test_audio_timeline())
