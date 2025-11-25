import asyncio
import os
from playwright.async_api import async_playwright, Page, BrowserContext

class BrowserManager:
    _instance = None
    _playwright = None
    _browser = None
    _context = None
    _page = None

    @classmethod
    async def get_page(cls) -> Page:
        if cls._page:
            return cls._page

        if not cls._playwright:
            cls._playwright = await async_playwright().start()
        
        # Connect to existing Chrome with remote debugging
        if not cls._browser:
            print("🔗 Connecting to Chrome (Remote Debugging Port: 9222)...")
            
            try:
                # Connect to the Chrome instance with remote debugging
                cls._browser = await cls._playwright.chromium.connect_over_cdp("http://localhost:9222")
                print("✅ Successfully connected to Chrome!")
                
                # Get the default context
                contexts = cls._browser.contexts
                if contexts:
                    cls._context = contexts[0]
                else:
                    print("⚠️  No context found, creating new one...")
                    cls._context = await cls._browser.new_context()
                    
            except Exception as e:
                print(f"\n❌ Failed to connect to Chrome: {e}")
                print("\n⚠️  Make sure Chrome is running with remote debugging:")
                print("   /Applications/Google\\ Chrome.app/Contents/MacOS/Google\\ Chrome \\")
                print("   --remote-debugging-port=9222 \\")
                print("   --user-data-dir=\"$HOME/Library/Application Support/Google/Chrome\"")
                raise
            
        if not cls._page:
            if cls._context and cls._context.pages:
                cls._page = cls._context.pages[0]
            else:
                cls._page = await cls._context.new_page()
            
        return cls._page

    @classmethod
    async def close(cls):
        # Don't close context or browser when using CDP
        # Just disconnect
        if cls._browser:
            await cls._browser.close()
        if cls._playwright:
            await cls._playwright.stop()
        
        cls._page = None
        cls._context = None
        cls._browser = None
        cls._playwright = None

    @classmethod
    async def ensure_logged_in(cls, url: str = "https://aistudio.google.com/"):
        """Get page without manual intervention."""
        page = await cls.get_page()
        # Just return the page, assume user already logged in via Chrome
        return page
