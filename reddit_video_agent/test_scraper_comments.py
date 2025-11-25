import asyncio
import os
from reddit_video_agent.core.config import Config
from reddit_video_agent.agents.scraper_agent import ScraperAgent

async def test_scraper():
    print("🧪 Testing Scraper Agent (Comments)...")
    
    config = {}
    agent = ScraperAgent(config)
    
    url = "https://www.reddit.com/r/nextfuckinglevel/comments/1ny8m4t/is_she_slicing_the_paper_with_a_wooden_sword/"
    
    try:
        result = await agent.execute(url)
        
        print("\n📄 Scrape Result:")
        print(f"Title: {result['title']}")
        print(f"Content Length: {len(result['content'])}")
        
        print("\n💬 Comments:")
        if result.get("comments_text"):
            for i, c in enumerate(result["comments_text"]):
                print(f"   {i+1}. {c['author']}: {c['text'][:50]}...")
        else:
            print("   ❌ No comments scraped.")
            
        print("\n📸 Screenshots:")
        if result.get("comment_screenshots"):
            for s in result["comment_screenshots"]:
                print(f"   - {os.path.basename(s)}")
        else:
            print("   ❌ No comment screenshots.")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_scraper())
