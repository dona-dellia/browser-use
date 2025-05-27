from browser_use.browser.context import BrowserContext
from browser_use.browser.context import BrowserContextConfig
from browser_use import Browser,BrowserConfig

config = BrowserContextConfig(
    
	wait_for_network_idle_page_load_time=3.0,
	headless=False,
)
conf = BrowserConfig(disable_security=True)

browser = Browser(config=conf)
context = BrowserContext(browser=browser, config=config)