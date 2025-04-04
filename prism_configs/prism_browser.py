from browser_use.browser.context import BrowserContext
from browser_use.browser.context import BrowserContextConfig
from browser_use import Browser

config = BrowserContextConfig(
	wait_for_network_idle_page_load_time=3.0,
)
browser = Browser()
context = BrowserContext(browser=browser, config=config)