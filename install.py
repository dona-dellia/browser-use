#!/usr/bin/env python3
"""
Installation script for browser-use with Selenium
"""

import subprocess
import sys
import os
from pathlib import Path

def install_requirements():
    """Install required Python packages."""
    print("Installing required Python packages...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def setup_webdrivers():
    """Setup WebDrivers for Selenium."""
    print("Setting up WebDrivers...")
    
    try:
        # Try to import webdriver_manager
        from webdriver_manager.chrome import ChromeDriverManager
        from webdriver_manager.firefox import GeckoDriverManager
        from webdriver_manager.microsoft import EdgeChromiumDriverManager
        
        # Download the Chrome driver
        print("Setting up Chrome WebDriver...")
        chrome_path = ChromeDriverManager().install()
        print(f"Chrome WebDriver installed at: {chrome_path}")
        
        # Download the Firefox driver (optional)
        try:
            print("Setting up Firefox WebDriver...")
            firefox_path = GeckoDriverManager().install()
            print(f"Firefox WebDriver installed at: {firefox_path}")
        except Exception as e:
            print(f"Firefox WebDriver setup failed (optional): {e}")
        
        # Download the Edge driver (optional)
        try:
            print("Setting up Edge WebDriver...")
            edge_path = EdgeChromiumDriverManager().install()
            print(f"Edge WebDriver installed at: {edge_path}")
        except Exception as e:
            print(f"Edge WebDriver setup failed (optional): {e}")
            
    except ImportError:
        print("webdriver_manager not installed. Installing it now...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "webdriver-manager"])
        print("Please run this script again to complete setup.")
        return
    except Exception as e:
        print(f"Error setting up WebDrivers: {e}")
        print("You may need to download and install WebDrivers manually.")

def create_example():
    """Create a simple example file."""
    example_dir = Path("examples")
    example_dir.mkdir(exist_ok=True)
    
    example_path = example_dir / "selenium_example.py"
    
    example_code = """
from browser_use import Agent, Browser, BrowserConfig
from langchain_openai import ChatOpenAI
import asyncio
import os

# Set your OpenAI API key here or in .env file
# os.environ["OPENAI_API_KEY"] = "your-api-key"

async def main():
    # Initialize browser with Selenium
    browser_config = BrowserConfig(
        headless=False,  # Set to True for headless mode
        browser_type="chrome"  # You can use "firefox" or "edge" too
    )
    
    browser = Browser(config=browser_config)
    
    # Initialize the language model
    llm = ChatOpenAI(model="gpt-4o")
    
    # Create and run the agent
    agent = Agent(
        task="Search for the latest AI news and summarize the top 3 headlines",
        llm=llm,
        browser=browser
    )
    
    # Run the agent
    result = await agent.run()
    
    # Print the final result
    print("Agent completed with result:")
    print(result.final_result())
    
    # Close the browser
    await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
"""
    
    with open(example_path, "w") as f:
        f.write(example_code)
        
    print(f"Example created at: {example_path}")

def main():
    """Main installation function."""
    print("Installing browser-use with Selenium...")
    
    # Install required packages
    install_requirements()
    
    # Setup WebDrivers
    setup_webdrivers()
    
    # Create example
    create_example()
    
    print("\nInstallation completed successfully!")
    print("\nTo use browser-use with Selenium, you can run the example:")
    print("python examples/selenium_example.py")

if __name__ == "__main__":
    main() 