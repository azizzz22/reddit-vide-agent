import asyncio
import sys
from reddit_video_agent.core.config import Config
from reddit_video_agent.agents.director import Director

async def main():
    # Validate Config
    try:
        Config.validate()
    except ValueError as e:
        print(f"Configuration Error: {e}")
        print("Please check your .env file.")
        return

    # Get URL from args or input
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter Reddit Post URL: ")

    # Initialize Director
    config = {} 
    director = Director(config)

    try:
        # Run
        await director.execute(url)
    finally:
        # Cleanup Browser
        from reddit_video_agent.core.browser_manager import BrowserManager
        await BrowserManager.close()

if __name__ == "__main__":
    asyncio.run(main())
