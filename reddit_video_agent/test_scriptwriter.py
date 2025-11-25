import asyncio
from reddit_video_agent.core.config import Config
from reddit_video_agent.agents.scriptwriter_agent import ScriptwriterAgent

async def test_scriptwriter():
    print("🧪 Testing Scriptwriter Agent (with Comments)...")
    
    config = {}
    agent = ScriptwriterAgent(config)
    
    # Dummy data simulating a successful scrape
    post_data = {
        "title": "Is she slicing the paper with a wooden sword?",
        "content": "Video of a woman slicing paper cleanly with a wooden bokken.",
        "video_path": "dummy_video.mp4",
        "comments_text": [
            {
                "author": "Dramatic-Fall701",
                "text": "My toxic trait is that id think i can easily do this"
            },
            {
                "author": "OstrichSmoothe",
                "text": "You could easily do that... with scissors"
            },
            {
                "author": "Int-Merc805",
                "text": "I was thinking this the other day. That I'd fight a bear to save my family. Then I stubbed my pinky toe and wanted to die."
            }
        ]
    }
    
    try:
        script = await agent.execute(post_data)
        
        print("\n📝 Generated Script:")
        print("-" * 40)
        print(script)
        print("-" * 40)
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_scriptwriter())
