"""
Selenium browser on steroids.
"""

import asyncio
import base64
import json
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Optional, TypedDict, Awaitable, Any, Protocol, Union

from selenium.webdriver import Chrome, ChromeOptions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import NoSuchElementException

from browser_use.browser.views import BrowserError, BrowserState, TabInfo, URLNotAllowedError
from browser_use.dom.service import DomService
from browser_use.dom.views import DOMElementNode, SelectorMap
from browser_use.utils import time_execution_sync

if TYPE_CHECKING:
	from browser_use.browser.browser import Browser

logger = logging.getLogger(__name__)


class BrowserContextWindowSize(TypedDict):
	width: int
	height: int


@dataclass
class BrowserContextConfig:
	"""
	Configuration for the BrowserContext.

	Default values:
		cookies_file: None
			Path to cookies file for persistence

	        disable_security: False
	                Disable browser security features

		minimum_wait_page_load_time: 0.5
			Minimum time to wait before getting page state for LLM input

	        wait_for_network_idle_page_load_time: 1.0
	                Time to wait for network requests to finish before getting page state.
	                Lower values may result in incomplete page loads.

		maximum_wait_page_load_time: 5.0
			Maximum time to wait for page load before proceeding anyway

		wait_between_actions: 1.0
			Time to wait between multiple per step actions

		browser_window_size: {
				'width': 1280,
				'height': 1100,
			}
			Default browser window size

		no_viewport: False
			Disable viewport

		save_recording_path: None
			Path to save video recordings

		save_downloads_path: None
	        Path to save downloads to

		trace_path: None
			Path to save trace files. It will auto name the file with the TRACE_PATH/{context_id}.zip

		locale: None
			Specify user locale, for example en-GB, de-DE, etc. Locale will affect navigator.language value, Accept-Language request header value as well as number and date formatting rules. If not provided, defaults to the system default locale.

		user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36'
			custom user agent to use.

		highlight_elements: True
			Highlight elements in the DOM on the screen

		viewport_expansion: 500
			Viewport expansion in pixels. This amount will increase the number of elements which are included in the state what the LLM will see. If set to -1, all elements will be included (this leads to high token usage). If set to 0, only the elements which are visible in the viewport will be included.

		allowed_domains: None
			List of allowed domains that can be accessed. If None, all domains are allowed.
			Example: ['example.com', 'api.example.com']

		include_dynamic_attributes: bool = True
			Include dynamic attributes in the CSS selector. If you want to reuse the css_selectors, it might be better to set this to False.
	"""

	cookies_file: str | None = None
	minimum_wait_page_load_time: float = 0.5
	wait_for_network_idle_page_load_time: float = 1
	maximum_wait_page_load_time: float = 5
	wait_between_actions: float = 1

	disable_security: bool = False

	browser_window_size: BrowserContextWindowSize = field(default_factory=lambda: {'width': 1280, 'height': 1100})
	no_viewport: Optional[bool] = None

	save_recording_path: str | None = None
	save_downloads_path: str | None = None
	trace_path: str | None = None
	locale: str | None = None
	user_agent: str = (
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36'
	)

	highlight_elements: bool = True
	viewport_expansion: int = 500
	allowed_domains: list[str] | None = None
	include_dynamic_attributes: bool = True


class Page(Protocol):
	async def evaluate(self, script: str, *args: Any) -> Any: ...

# Create a wrapper class that adapts Selenium's WebDriver to the expected Page interface
class SeleniumPageWrapper(Page):
	def __init__(self, driver: Chrome):
		self.driver = driver

	async def evaluate(self, script: str, *args: Any) -> Any:
		return self.driver.execute_script(script, *args)

@dataclass
class BrowserSession:
	driver: Chrome
	current_window: str
	cached_state: BrowserState


class BrowserContext:
	def __init__(
		self,
		browser: 'Browser',
		config: BrowserContextConfig = BrowserContextConfig(),
	):
		self.context_id = str(uuid.uuid4())
		logger.debug(f'Initializing new browser context with id: {self.context_id}')

		self.config = config
		self.browser = browser
		self.session: Optional[BrowserSession] = None
		self.current_state: Optional[BrowserState] = None

	async def __aenter__(self):
		"""Async context manager entry"""
		await self._initialize_session()
		return self

	async def __aexit__(self, exc_type, exc_val, exc_tb):
		"""Async context manager exit"""
		await self.close()

	async def close(self):
		"""Close the browser instance"""
		logger.debug('Closing browser context')

		try:
			if self.session is None:
				return

			await self.save_cookies()

			try:
				self.session.driver.quit()
			except Exception as e:
				logger.debug(f'Failed to close driver: {e}')
		finally:
			self.session = None

	def __del__(self):
		"""Cleanup when object is destroyed"""
		if self.session is not None:
			logger.debug('BrowserContext was not properly closed before destruction')
			try:
				self.session.driver.quit()
				self.session = None
			except Exception as e:
				logger.warning(f'Failed to force close browser context: {e}')

	async def _initialize_session(self) -> BrowserSession:
		"""Initialize the browser session"""
		logger.debug('Initializing browser context')

		driver = await self._create_driver()
		initial_state = self._get_initial_state(driver)

		self.session = BrowserSession(
			driver=driver,
			current_window=driver.current_window_handle,
			cached_state=initial_state,
		)
		return self.session

	async def _create_driver(self) -> Chrome:
		"""Creates a new browser driver with anti-detection measures and loads cookies if available."""
		options = ChromeOptions()
		
		# Set window size
		if not self.config.no_viewport:
			options.add_argument(f'--window-size={self.config.browser_window_size["width"]},{self.config.browser_window_size["height"]}')
		
		# Set user agent
		options.add_argument(f'--user-agent={self.config.user_agent}')
		
		# Disable security if needed
		if self.config.disable_security:
			options.add_argument('--disable-web-security')
			options.add_argument('--disable-site-isolation-trials')
			options.add_argument('--disable-features=IsolateOrigins,site-per-process')
		
		# Add anti-detection measures
		options.add_argument('--disable-blink-features=AutomationControlled')
		options.add_experimental_option("excludeSwitches", ["enable-automation"])
		options.add_experimental_option('useAutomationExtension', False)
		
		# Set download path if specified
		if self.config.save_downloads_path:
			prefs = {
				"download.default_directory": self.config.save_downloads_path,
				"download.prompt_for_download": False,
			}
			options.add_experimental_option("prefs", prefs)
		
		# Create driver
		service = Service(ChromeDriverManager().install())
		driver = Chrome(service=service, options=options)
		
		# Execute anti-detection script
		driver.execute_script("""
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
		
		# Load cookies if they exist
		if self.config.cookies_file and os.path.exists(self.config.cookies_file):
			with open(self.config.cookies_file, 'r') as f:
				cookies = json.load(f)
				logger.info(f'Loaded {len(cookies)} cookies from {self.config.cookies_file}')
				for cookie in cookies:
					driver.add_cookie(cookie)
		
		return driver

	async def get_session(self) -> BrowserSession:
		"""Lazy initialization of the browser and related components"""
		if self.session is None:
			return await self._initialize_session()
		return self.session

	async def get_current_driver(self) -> Chrome:
		"""Get the current driver"""
		session = await self.get_session()
		return session.driver

	async def _wait_for_stable_network(self):
		"""Wait for network requests to stabilize"""
		driver = await self.get_current_driver()
		
		# Wait for document ready state
		WebDriverWait(driver, self.config.maximum_wait_page_load_time).until(
			lambda d: d.execute_script('return document.readyState') == 'complete'
		)
		
		# Wait for jQuery if present
		try:
			WebDriverWait(driver, 5).until(
				lambda d: d.execute_script('return jQuery.active') == 0
			)
		except:
			pass
		
		# Wait for any pending XHR requests
		try:
			WebDriverWait(driver, 5).until(
				lambda d: d.execute_script('return window.XMLHttpRequest.active') == 0
			)
		except:
			pass

	async def _wait_for_page_and_frames_load(self, timeout_overwrite: float | None = None):
		"""Ensures page is fully loaded before continuing."""
		start_time = time.time()
		
		try:
			await self._wait_for_stable_network()
			driver = await self.get_current_driver()
			await self._check_and_handle_navigation(driver)
		except URLNotAllowedError as e:
			raise e
		except Exception:
			logger.warning('Page load failed, continuing...')
			pass

		elapsed = time.time() - start_time
		remaining = max((timeout_overwrite or self.config.minimum_wait_page_load_time) - elapsed, 0)

		logger.debug(f'--Page loaded in {elapsed:.2f} seconds, waiting for additional {remaining:.2f} seconds')

		if remaining > 0:
			await asyncio.sleep(remaining)

	def _is_url_allowed(self, url: str) -> bool:
		"""Check if a URL is allowed based on the whitelist configuration."""
		if not self.config.allowed_domains:
			return True

		try:
			from urllib.parse import urlparse
			parsed_url = urlparse(url)
			domain = parsed_url.netloc.lower()

			if ':' in domain:
				domain = domain.split(':')[0]

			return any(
				domain == allowed_domain.lower() or domain.endswith('.' + allowed_domain.lower())
				for allowed_domain in self.config.allowed_domains
			)
		except Exception as e:
			logger.error(f'Error checking URL allowlist: {str(e)}')
			return False

	async def _check_and_handle_navigation(self, driver: Chrome) -> None:
		"""Check if current page URL is allowed and handle if not."""
		if not self._is_url_allowed(driver.current_url):
			logger.warning(f'Navigation to non-allowed URL detected: {driver.current_url}')
			try:
				await self.go_back()
			except Exception as e:
				logger.error(f'Failed to go back after detecting non-allowed URL: {str(e)}')
			raise URLNotAllowedError(f'Navigation to non-allowed URL: {driver.current_url}')

	async def navigate_to(self, url: str):
		"""Navigate to a URL"""
		if not self._is_url_allowed(url):
			raise BrowserError(f'Navigation to non-allowed URL: {url}')

		driver = await self.get_current_driver()
		driver.get(url)
		await self._wait_for_page_and_frames_load()

	async def refresh_page(self):
		"""Refresh the current page"""
		driver = await self.get_current_driver()
		driver.refresh()
		await self._wait_for_page_and_frames_load()

	async def go_back(self):
		"""Navigate back in history"""
		driver = await self.get_current_driver()
		driver.back()
		await self._wait_for_page_and_frames_load()

	async def go_forward(self):
		"""Navigate forward in history"""
		driver = await self.get_current_driver()
		driver.forward()
		await self._wait_for_page_and_frames_load()

	async def close_current_tab(self):
		"""Close the current tab"""
		driver = await self.get_current_driver()
		driver.close()
		
		# Switch to the first available tab if any exist
		if len(driver.window_handles) > 0:
			await self.switch_to_tab(0)

	async def get_page_html(self) -> str:
		"""Get the current page HTML content"""
		driver = await self.get_current_driver()
		return driver.page_source

	async def execute_javascript(self, script: str):
		"""Execute JavaScript code on the page"""
		driver = await self.get_current_driver()
		return driver.execute_script(script)

	@time_execution_sync('--get_state')
	async def get_state(self) -> BrowserState:
		"""Get the current state of the browser"""
		await self._wait_for_page_and_frames_load()
		session = await self.get_session()
		session.cached_state = await self._update_state()

		if self.config.cookies_file:
			asyncio.create_task(self.save_cookies())

		return session.cached_state

	async def _update_state(self, focus_element: int = -1) -> BrowserState:
		"""Update and return state."""
		session = await self.get_session()
		driver = session.driver

		try:
			await self.remove_highlights()

			dom_service = DomService(SeleniumPageWrapper(driver))
			content = await dom_service.get_clickable_elements(
				focus_element=focus_element,
				viewport_expansion=self.config.viewport_expansion,
				highlight_elements=self.config.highlight_elements,
			)

			screenshot_b64 = await self.take_screenshot()
			pixels_above, pixels_below = await self.get_scroll_info(driver)

			self.current_state = BrowserState(
				element_tree=content.element_tree,
				selector_map=content.selector_map,
				url=driver.current_url,
				title=driver.title,
				tabs=await self.get_tabs_info(),
				screenshot=screenshot_b64,
				pixels_above=pixels_above,
				pixels_below=pixels_below,
			)

			return self.current_state
		except Exception as e:
			logger.error(f'Failed to update state: {str(e)}')
			if self.current_state is not None:
				return self.current_state
			raise

	async def take_screenshot(self, full_page: bool = False) -> str:
		"""Returns a base64 encoded screenshot of the current page."""
		driver = await self.get_current_driver()
		
		if full_page:
			# Get total page height
			total_height = driver.execute_script("return document.body.scrollHeight")
			# Set window size to capture full page
			driver.set_window_size(1920, total_height)
		
		screenshot = driver.get_screenshot_as_png()
		screenshot_b64 = base64.b64encode(screenshot).decode('utf-8')
		
		return screenshot_b64

	async def remove_highlights(self):
		"""Removes all highlight overlays and labels."""
		try:
			driver = await self.get_current_driver()
			driver.execute_script("""
				try {
					const container = document.getElementById('playwright-highlight-container');
					if (container) {
						container.remove();
					}

					const highlightedElements = document.querySelectorAll('[browser-user-highlight-id^="playwright-highlight-"]');
					highlightedElements.forEach(el => {
						el.removeAttribute('browser-user-highlight-id');
					});
				} catch (e) {
					console.error('Failed to remove highlights:', e);
				}
			""")
		except Exception as e:
			logger.debug(f'Failed to remove highlights (this is usually ok): {str(e)}')
			pass

	# endregion

	# region - User Actions

	@classmethod
	def _convert_simple_xpath_to_css_selector(cls, xpath: str) -> str:
		"""Converts simple XPath expressions to CSS selectors."""
		if not xpath:
			return ''

		# Remove leading slash if present
		xpath = xpath.lstrip('/')

		# Split into parts
		parts = xpath.split('/')
		css_parts = []

		for part in parts:
			if not part:
				continue

			# Handle index notation [n]
			if '[' in part:
				base_part = part[: part.find('[')]
				index_part = part[part.find('[') :]

				# Handle multiple indices
				indices = [i.strip('[]') for i in index_part.split(']')[:-1]]

				for idx in indices:
					try:
						# Handle numeric indices
						if idx.isdigit():
							index = int(idx) - 1
							base_part += f':nth-of-type({index + 1})'
						# Handle last() function
						elif idx == 'last()':
							base_part += ':last-of-type'
						# Handle position() functions
						elif 'position()' in idx:
							if '>1' in idx:
								base_part += ':nth-of-type(n+2)'
					except ValueError:
						continue

				css_parts.append(base_part)
			else:
				css_parts.append(part)

		base_selector = ' > '.join(css_parts)
		return base_selector

	@classmethod
	def _enhanced_css_selector_for_element(cls, element: DOMElementNode, include_dynamic_attributes: bool = True) -> str:
		"""
		Creates a CSS selector for a DOM element, handling various edge cases and special characters.

		Args:
		        element: The DOM element to create a selector for

		Returns:
		        A valid CSS selector string
		"""
		try:
			# Get base selector from XPath
			css_selector = cls._convert_simple_xpath_to_css_selector(element.xpath)

			# Handle class attributes
			if 'class' in element.attributes and element.attributes['class'] and include_dynamic_attributes:
				# Define a regex pattern for valid class names in CSS
				valid_class_name_pattern = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_-]*$')

				# Iterate through the class attribute values
				classes = element.attributes['class'].split()
				for class_name in classes:
					# Skip empty class names
					if not class_name.strip():
						continue

					# Check if the class name is valid
					if valid_class_name_pattern.match(class_name):
						# Append the valid class name to the CSS selector
						css_selector += f'.{class_name}'
					else:
						# Skip invalid class names
						continue

			# Expanded set of safe attributes that are stable and useful for selection
			SAFE_ATTRIBUTES = {
				# Data attributes (if they're stable in your application)
				'id',
				# Standard HTML attributes
				'name',
				'type',
				'placeholder',
				# Accessibility attributes
				'aria-label',
				'aria-labelledby',
				'aria-describedby',
				'role',
				# Common form attributes
				'for',
				'autocomplete',
				'required',
				'readonly',
				# Media attributes
				'alt',
				'title',
				'src',
				# Custom stable attributes (add any application-specific ones)
				'href',
				'target',
			}

			if include_dynamic_attributes:
				dynamic_attributes = {
					'data-id',
					'data-qa',
					'data-cy',
					'data-testid',
				}
				SAFE_ATTRIBUTES.update(dynamic_attributes)

			# Handle other attributes
			for attribute, value in element.attributes.items():
				if attribute == 'class':
					continue

				# Skip invalid attribute names
				if not attribute.strip():
					continue

				if attribute not in SAFE_ATTRIBUTES:
					continue

				# Escape special characters in attribute names
				safe_attribute = attribute.replace(':', r'\:')

				# Handle different value cases
				if value == '':
					css_selector += f'[{safe_attribute}]'
				elif any(char in value for char in '"\'<>`\n\r\t'):
					# Use contains for values with special characters
					# Regex-substitute *any* whitespace with a single space, then strip.
					collapsed_value = re.sub(r'\s+', ' ', value).strip()
					# Escape embedded double-quotes.
					safe_value = collapsed_value.replace('"', '\\"')
					css_selector += f'[{safe_attribute}*="{safe_value}"]'
				else:
					css_selector += f'[{safe_attribute}="{value}"]'

			return css_selector

		except Exception:
			# Fallback to a more basic selector if something goes wrong
			tag_name = element.tag_name or '*'
			return f"{tag_name}[highlight_index='{element.highlight_index}']"

	async def get_locate_element(self, element: DOMElementNode) -> Optional[WebElement]:
		driver = await self.get_current_driver()

		# Navegar até os iframes pais
		parents: list[DOMElementNode] = []
		current = element
		while current.parent is not None:
			parent = current.parent
			parents.append(parent)
			current = parent
		parents.reverse()

		iframes = [item for item in parents if item.tag_name == 'iframe']
		driver.switch_to.default_content()
		for parent in iframes:
			css_selector = self._enhanced_css_selector_for_element(
				parent, include_dynamic_attributes=self.config.include_dynamic_attributes
			)
			try:
				iframe_element = driver.find_element(By.CSS_SELECTOR, css_selector)
				driver.switch_to.frame(iframe_element)
			except NoSuchElementException:
				logger.error(f'Failed to locate iframe: {css_selector}')
				return None

		css_selector = self._enhanced_css_selector_for_element(
			element, include_dynamic_attributes=self.config.include_dynamic_attributes
		)

		try:
			element_handle = driver.find_element(By.CSS_SELECTOR, css_selector)
			driver.execute_script("arguments[0].scrollIntoView(true);", element_handle)
			return element_handle
		except Exception as e:
			logger.error(f'Failed to locate element: {str(e)}')
			return None

	async def _input_text_element_node(self, element_node: DOMElementNode, text: str):
		try:
			if element_node.highlight_index is not None:
				await self._update_state(focus_element=element_node.highlight_index)

			driver = await self.get_current_driver()
			element_handle = await self.get_locate_element(element_node)

			if element_handle is None:
				raise Exception(f'Element: {repr(element_node)} not found')

			element_handle.clear()
			element_handle.send_keys(text)

			WebDriverWait(driver, 10).until(
				lambda d: d.execute_script("return document.readyState") == "complete"
			)

		except Exception as e:
			raise Exception(f'Failed to input text into element: {repr(element_node)}. Error: {str(e)}')

	async def _click_element_node(self, element_node: DOMElementNode) -> Optional[str]:
		try:
			driver = await self.get_current_driver()

			if element_node.highlight_index is not None:
				await self._update_state(focus_element=element_node.highlight_index)

			element_handle = await self.get_locate_element(element_node)
			if element_handle is None:
				raise Exception(f'Element: {repr(element_node)} not found')

			async def perform_click(click_func):
				try:
					click_func()
					WebDriverWait(driver, 10).until(
						lambda d: d.execute_script("return document.readyState") == "complete"
					)
					await self._check_and_handle_navigation(driver)
					return None
				except Exception as e:
					raise e

			try:
				return await perform_click(lambda: element_handle.click())
			except Exception:
				try:
					return await perform_click(lambda: driver.execute_script("arguments[0].click();", element_handle))
				except Exception as e:
					raise Exception(f'Failed to click element: {str(e)}')

		except Exception as e:
			raise Exception(f'Failed to click element: {repr(element_node)}. Error: {str(e)}')

	async def get_tabs_info(self) -> list[TabInfo]:
		"""Get information about all tabs"""
		driver = await self.get_current_driver()
		tabs_info = []
		
		for i, handle in enumerate(driver.window_handles):
			driver.switch_to.window(handle)
			tabs_info.append(TabInfo(
				page_id=i,
				url=driver.current_url,
				title=driver.title
			))
		
		# Switch back to original window
		if self.session is not None:
			driver.switch_to.window(self.session.current_window)
		return tabs_info

	async def switch_to_tab(self, page_id: int) -> None:
		"""Switch to a specific tab by its page_id"""
		driver = await self.get_current_driver()
		handles = driver.window_handles
		
		if page_id >= len(handles):
			raise BrowserError(f'No tab found with page_id: {page_id}')
		
		handle = handles[page_id]
		driver.switch_to.window(handle)
		
		if not self._is_url_allowed(driver.current_url):
			raise BrowserError(f'Cannot switch to tab with non-allowed URL: {driver.current_url}')
		
		if self.session is not None:
			self.session.current_window = handle
		await self._wait_for_page_and_frames_load()

	async def create_new_tab(self, url: str | None = None) -> None:
		"""Create a new tab and optionally navigate to a URL"""
		if url and not self._is_url_allowed(url):
			raise BrowserError(f'Cannot create new tab with non-allowed URL: {url}')
		
		driver = await self.get_current_driver()
		driver.execute_script("window.open('');")
		handles = driver.window_handles
		driver.switch_to.window(handles[-1])
		if self.session is not None:
			self.session.current_window = handles[-1]
		
		if url:
			driver.get(url)
			await self._wait_for_page_and_frames_load()

	async def get_selector_map(self) -> SelectorMap:
		session = await self.get_session()
		return session.cached_state.selector_map

	async def get_element_by_index(self, index: int) -> WebElement | None:
		selector_map = await self.get_selector_map()
		element = await self.locate_element(selector_map[index])
		return element

	async def get_dom_element_by_index(self, index: int) -> DOMElementNode | None:
		selector_map = await self.get_selector_map()
		return selector_map[index]

	async def locate_element(self, element: DOMElementNode) -> WebElement | None:
		"""Locate a WebElement using the provided DOMElementNode's selector."""
		driver = await self.get_current_driver()
		try:
			return driver.find_element(By.CSS_SELECTOR, element.selector)
		except Exception as e:
			logger.debug(f'Failed to locate element: {str(e)}')
			return None

	async def save_cookies(self):
		"""Save current cookies to file"""
		if self.session and self.session.driver and self.config.cookies_file:
			try:
				cookies = self.session.driver.get_cookies()
				logger.info(f'Saving {len(cookies)} cookies to {self.config.cookies_file}')

				dirname = os.path.dirname(self.config.cookies_file)
				if dirname:
					os.makedirs(dirname, exist_ok=True)

				with open(self.config.cookies_file, 'w') as f:
					json.dump(cookies, f)
			except Exception as e:
				logger.warning(f'Failed to save cookies: {str(e)}')

	async def is_file_uploader(self, element_node: DOMElementNode, max_depth: int = 3, current_depth: int = 0) -> bool:
		"""Check if element or its children are file uploaders"""
		if current_depth > max_depth:
			return False

		# Check current element
		is_uploader = False

		if not isinstance(element_node, DOMElementNode):
			return False

		# Check for file input attributes
		if element_node.tag_name == 'input':
			is_uploader = element_node.attributes.get('type') == 'file' or element_node.attributes.get('accept') is not None

		if is_uploader:
			return True

		# Recursively check children
		if element_node.children and current_depth < max_depth:
			for child in element_node.children:
				if isinstance(child, DOMElementNode):
					if await self.is_file_uploader(child, max_depth, current_depth + 1):
						return True

		return False

	async def get_scroll_info(self, driver: Chrome) -> tuple[int, int]:
		"""Get scroll position information for the current page."""
		scroll_y = driver.execute_script('return window.scrollY')
		viewport_height = driver.execute_script('return window.innerHeight')
		total_height = driver.execute_script('return document.documentElement.scrollHeight')
		pixels_above = scroll_y
		pixels_below = total_height - (scroll_y + viewport_height)
		return pixels_above, pixels_below

	async def reset_context(self):
		"""Reset the browser session"""
		session = await self.get_session()
		driver = session.driver
		
		# Close all tabs except the first one
		handles = driver.window_handles
		for handle in handles[1:]:
			driver.switch_to.window(handle)
			driver.close()
		
		# Switch back to first tab
		driver.switch_to.window(handles[0])
		if self.session is not None:
			self.session.current_window = handles[0]
		
		session.cached_state = self._get_initial_state()
		driver.get('about:blank')

	def _get_initial_state(self, driver: Optional[Chrome] = None) -> BrowserState:
		"""Get the initial state of the browser"""
		return BrowserState(
			element_tree=DOMElementNode(
				tag_name='root',
				is_visible=True,
				parent=None,
				xpath='',
				attributes={},
				children=[],
			),
			selector_map={},
			url=driver.current_url if driver else '',
			title=driver.title if driver else '',
			screenshot=None,
			tabs=[],
		)
