"""
Selenium browser implementation.
"""

import asyncio
import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union

# Selenium imports
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.common.exceptions import WebDriverException
import requests
import subprocess

from browser_use.browser.context import BrowserContext, BrowserContextConfig

logger = logging.getLogger(__name__)


@dataclass
class ProxySettings:
	"""Proxy settings for the browser."""
	server: str
	username: Optional[str] = None
	password: Optional[str] = None
	bypass: Optional[str] = None


@dataclass
class BrowserConfig:
	"""
	Configuration for the Browser.

	Default values:
		headless: False
			Whether to run browser in headless mode

		disable_security: True
			Disable browser security features

		extra_args: []
			Extra arguments to pass to the browser

		browser_type: "chrome"
			Type of browser to use (chrome, firefox, edge)

		chrome_instance_path: None
			Path to a Chrome instance to use to connect to your normal browser
			e.g. '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
	"""

	headless: bool = False
	disable_security: bool = True
	extra_args: List[str] = field(default_factory=list)
	browser_type: str = "chrome"
	chrome_instance_path: Optional[str] = None
	proxy: Optional[ProxySettings] = None
	new_context_config: BrowserContextConfig = field(default_factory=BrowserContextConfig)


class Browser:
	"""
	Selenium WebDriver browser implementation.

	This is a persistent browser factory that can spawn multiple browser contexts.
	It is recommended to use only one instance of Browser per your application (RAM usage will grow otherwise).
	"""

	def __init__(
		self,
		config: BrowserConfig = BrowserConfig(),
	):
		logger.debug('Initializing new browser')
		self.config = config
		self.driver: Optional[webdriver.Remote] = None
		
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

	async def get_webdriver(self) -> webdriver.Remote:
		"""Get a WebDriver instance"""
		if self.driver is None:
			return await self._init()

		return self.driver

	async def _init(self) -> webdriver.Remote:
		"""Initialize the browser session"""
		driver = await self._setup_browser()
		self.driver = driver
		return self.driver

	async def _setup_browser_with_instance(self) -> webdriver.Remote:
		"""Sets up and returns a WebDriver instance connected to an existing Chrome."""
		if not self.config.chrome_instance_path:
			raise ValueError('Chrome instance path is required')

		try:
			# Check if Chrome is already running with debugging port
			response = requests.get('http://localhost:9222/json/version', timeout=2)
			if response.status_code == 200:
				logger.info('Reusing existing Chrome instance')
				chrome_options = ChromeOptions()
				chrome_options.debugger_address = 'localhost:9222'
				driver = webdriver.Chrome(options=chrome_options)
				return driver
		except requests.ConnectionError:
			logger.debug('No existing Chrome instance found, starting a new one')

		# Start a new Chrome instance
		subprocess.Popen(
			[
				self.config.chrome_instance_path,
				'--remote-debugging-port=9222',
			],
			stdout=subprocess.DEVNULL,
			stderr=subprocess.DEVNULL,
		)
	
		# Wait for Chrome to start
		for _ in range(10):
			try:
				response = requests.get('http://localhost:9222/json/version', timeout=2)
				if response.status_code == 200:
					break
			except requests.ConnectionError:
				pass
			await asyncio.sleep(1)

		# Connect to the Chrome instance
		try:
			chrome_options = ChromeOptions()
			chrome_options.debugger_address = 'localhost:9222'
			driver = webdriver.Chrome(options=chrome_options)
			return driver
		except Exception as e:
			logger.error(f'Failed to start a new Chrome instance: {str(e)}')
			raise RuntimeError(
				'To start Chrome in Debug mode, you need to close all existing Chrome instances and try again.'
			)

	async def _setup_standard_browser(self) -> webdriver.Remote:
		"""Sets up and returns a new WebDriver instance."""
		if self.config.browser_type.lower() == "chrome":
			options = ChromeOptions()
			
			# Add Chrome-specific arguments
			if self.config.headless:
				options.add_argument("--headless=new")
			
			# Add common arguments
			options.add_argument('--no-sandbox')
			options.add_argument('--disable-blink-features=AutomationControlled')
			options.add_argument('--disable-infobars')
			options.add_argument('--disable-background-timer-throttling')
			options.add_argument('--disable-popup-blocking')
			options.add_argument('--disable-backgrounding-occluded-windows')
			options.add_argument('--disable-renderer-backgrounding')
			options.add_argument('--disable-window-activation')
			options.add_argument('--disable-focus-on-load')
			options.add_argument('--no-first-run')
			options.add_argument('--no-default-browser-check')
			options.add_argument('--window-position=0,0')
			
			# Add security-related arguments if needed
			for arg in self.disable_security_args:
				options.add_argument(arg)
			
			# Add extra arguments provided in config
			for arg in self.config.extra_args:
				options.add_argument(arg)
			
			# Add proxy settings if provided
			if self.config.proxy:
				if self.config.proxy.username and self.config.proxy.password:
					proxy_auth = f"{self.config.proxy.username}:{self.config.proxy.password}@"
					proxy_url = f"{proxy_auth}{self.config.proxy.server}"
				else:
					proxy_url = self.config.proxy.server
				
				options.add_argument(f'--proxy-server={proxy_url}')
				if self.config.proxy.bypass:
					options.add_argument(f'--proxy-bypass-list={self.config.proxy.bypass}')
			
			# Create and return Chrome driver
			driver = webdriver.Chrome(options=options)
			
		elif self.config.browser_type.lower() == "firefox":
			options = FirefoxOptions()
			
			if self.config.headless:
				options.add_argument("--headless")
			
			# Add Firefox-specific settings
			options.set_preference("dom.webnotifications.enabled", False)
			options.set_preference("dom.push.enabled", False)
			
			# Add proxy settings if provided
			if self.config.proxy:
				options.set_preference("network.proxy.type", 1)
				host, port = self.config.proxy.server.split(":")
				options.set_preference("network.proxy.http", host)
				options.set_preference("network.proxy.http_port", int(port))
				options.set_preference("network.proxy.ssl", host)
				options.set_preference("network.proxy.ssl_port", int(port))
				
				if self.config.proxy.username and self.config.proxy.password:
					# Firefox handles proxy auth differently
					pass
			
			driver = webdriver.Firefox(options=options)
			
		elif self.config.browser_type.lower() == "edge":
			options = EdgeOptions()
			
			if self.config.headless:
				options.add_argument("--headless=new")
			
			# Add Edge-specific arguments (similar to Chrome)
			options.add_argument('--no-sandbox')
			options.add_argument('--disable-blink-features=AutomationControlled')
			
			# Add proxy settings if provided
			if self.config.proxy:
				options.add_argument(f'--proxy-server={self.config.proxy.server}')
			
			driver = webdriver.Edge(options=options)
		else:
			raise ValueError(f"Unsupported browser type: {self.config.browser_type}")
		
		return driver

	async def _setup_browser(self) -> webdriver.Remote:
		"""Sets up and returns a Selenium WebDriver instance."""
		try:
			if self.config.chrome_instance_path:
				return await self._setup_browser_with_instance()
			else:
				return await self._setup_standard_browser()
		except Exception as e:
			logger.error(f'Failed to initialize browser: {str(e)}')
			raise

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
				loop = asyncio.get_running_loop()
				if loop.is_running():
					loop.create_task(self.close())
				else:
					asyncio.run(self.close())
		except Exception as e:
			logger.debug(f'Failed to cleanup browser in destructor: {e}')
			# As a last resort, try to quit directly
			try:
				if self.driver:
					self.driver.quit()
			except:
				pass
