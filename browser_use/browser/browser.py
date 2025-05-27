"""
Selenium browser on steroids.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Optional

from selenium.webdriver import Chrome
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from browser_use.browser.context import BrowserContext, BrowserContextConfig

logger = logging.getLogger(__name__)


@dataclass
class BrowserConfig:
	"""
	Configuration for the Browser.

	Default values:
		headless: True
			Whether to run browser in headless mode

		disable_security: False
			Disable browser security features

		extra_chromium_args: []
			Extra arguments to pass to the browser

		chrome_instance_path: None
			Path to a Chrome instance to use to connect to your normal browser
			e.g. '/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome'
	"""

	headless: bool = False
	disable_security: bool = True
	extra_chromium_args: list[str] = field(default_factory=list)
	chrome_instance_path: str | None = None
	new_context_config: BrowserContextConfig = field(default_factory=BrowserContextConfig)


class Browser:
	"""
	Selenium browser on steroids.

	This is a persistent browser factory that can spawn multiple browser contexts.
	It is recommended to use only one instance of Browser per your application (RAM usage will grow otherwise).
	"""

	def __init__(
		self,
		config: BrowserConfig = BrowserConfig(),
	):
		logger.debug('Initializing new browser')
		self.config = config
		self.driver: Optional[Chrome] = None

		self.disable_security_args = []
		if self.config.disable_security:
			self.disable_security_args = [
				'--disable-web-security',
				'--disable-site-isolation-trials',
				'--disable-features=IsolateOrigins,site-per-process',
			]

	async def new_context(
		self, config: BrowserContextConfig = BrowserContextConfig()
	) -> BrowserContext:
		"""Create a browser context"""
		return BrowserContext(config=config, browser=self)

	async def get_driver(self) -> Chrome:
		"""Get a browser driver"""
		if self.driver is None:
			return await self._init()
		return self.driver

	async def _init(self) -> Chrome:
		"""Initialize the browser session"""
		options = Options()
		if self.config.headless:
      
			options.add_argument('--headless')
		
		# Add anti-detection measures
		options.add_argument('--disable-blink-features=AutomationControlled')
		options.add_experimental_option("excludeSwitches", ["enable-automation"])
		options.add_experimental_option('useAutomationExtension', False)
		
		# Add security args if needed
		for arg in self.disable_security_args:
			options.add_argument(arg)
		
		# Add extra arguments
		for arg in self.config.extra_chromium_args:
			options.add_argument(arg)
		
		# Create driver
		service = Service(ChromeDriverManager().install())
		self.driver = Chrome(service=service, options=options)
		
		# Execute anti-detection script
		self.driver.execute_script("""
			// Webdriver property
			Object.defineProperty(navigator, 'webdriver', {
				get: () => undefined
			});

			// Languages
			Object.defineProperty(navigator, 'languages', {
				get: () => ['en-US']
			});

			// Plugins
			Object.defineProperty(navigator, 'plugins', {
				get: () => [1, 2, 3, 4, 5]
			});

			// Chrome runtime
			window.chrome = { runtime: {} };

			// Permissions
			const originalQuery = window.navigator.permissions.query;
			window.navigator.permissions.query = (parameters) => (
				parameters.name === 'notifications' ?
					Promise.resolve({ state: Notification.permission }) :
					originalQuery(parameters)
			);
		""")
		
		return self.driver

	async def close(self):
		"""Close the browser instance"""
		try:
			if self.driver:
				self.driver.quit()
		except Exception as e:
			logger.debug(f'Failed to close browser properly: {e}')
		finally:
			self.driver = None

	def __del__(self):
		"""Cleanup when object is destroyed"""
		try:
			if self.driver:
				self.driver.quit()
		except Exception as e:
			logger.debug(f'Failed to cleanup browser in destructor: {e}')
