# Migration Guide: Playwright to Selenium

This guide provides instructions for migrating from Playwright to Selenium in the browser-use project.

## Why Migrate?

- Selenium has broader adoption and community support
- Better compatibility with existing testing infrastructure
- Simplified webdriver management
- Support for more browsers and platforms

## Installation

1. Uninstall Playwright:
```bash
pip uninstall playwright
```

2. Install Selenium and dependencies:
```bash
# Install from requirements.txt
pip install -r requirements.txt

# Or manually:
pip install selenium webdriver-manager
```

3. Run the installation script to set up WebDrivers:
```bash
python install.py
```

## API Changes

### Browser Configuration

The `BrowserConfig` class has been updated with Selenium-specific options:

```python
from browser_use import Browser, BrowserConfig

# Old Playwright config:
# config = BrowserConfig(
#    headless=True,
#    chrome_instance_path="/path/to/chrome",
#    extra_chromium_args=["--disable-gpu"]
# )

# New Selenium config:
config = BrowserConfig(
    headless=True,  
    browser_type="chrome",  # Now supports: "chrome", "firefox", "edge"
    chrome_instance_path="/path/to/chrome",  # Still supported
    extra_args=["--disable-gpu"]  # Renamed from extra_chromium_args
)

browser = Browser(config=config)
```

### Removed Features

The following Playwright-specific features have been removed:

- `wss_url` and `cdp_url` parameters for remote browser connection
- `trace_path` for trace recording
- `record_video_dir` for video recording

### New Features

Selenium provides some new capabilities:

- Better native file upload handling
- Browser extension support
- Improved iframe handling
- Built-in screenshot functionality for visible elements

## Code Migration Examples

### Example 1: Basic Browser Setup

```python
# Playwright version:
# from browser_use import Browser, BrowserConfig
# 
# browser = Browser(
#     config=BrowserConfig(
#         headless=False,
#     )
# )

# Selenium version:
from browser_use import Browser, BrowserConfig

browser = Browser(
    config=BrowserConfig(
        headless=False,
        browser_type="chrome"  # Specify browser type
    )
)
```

### Example 2: Clicking Elements

```python
# The Agent API remains the same!
from browser_use import Agent
from langchain_openai import ChatOpenAI

agent = Agent(
    task="Search for the latest news about AI",
    llm=ChatOpenAI(model="gpt-4o"),
    browser=browser
)

# Run the agent - this works the same way
result = await agent.run()
```

## Troubleshooting

### WebDriver Issues

If you encounter WebDriver problems:

1. Ensure you have the latest WebDriver for your browser:
```python
from webdriver_manager.chrome import ChromeDriverManager
from selenium import webdriver

driver_path = ChromeDriverManager().install()
```

2. Make sure your browser version is compatible with the WebDriver version.

3. For Chrome, check if your ChromeDriver version matches your Chrome version:
```bash
chromedriver --version
google-chrome --version
```

### Browser Not Found

If you get a "Browser not found" error:

1. Make sure you've specified the correct browser type:
```python
config = BrowserConfig(browser_type="chrome")  # or "firefox", "edge"
```

2. For custom browser paths, ensure the path is correct:
```python
config = BrowserConfig(
    browser_type="chrome",
    chrome_instance_path="/path/to/chrome"
)
```

## Additional Resources

- [Selenium Documentation](https://www.selenium.dev/documentation/)
- [WebDriver Manager](https://github.com/SergeyPirogov/webdriver_manager)
- [browser-use Documentation](https://docs.browser-use.com) 