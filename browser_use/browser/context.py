"""
Selenium browser context implementation.
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
from typing import TYPE_CHECKING, Dict, List, Optional, TypedDict, Tuple, Any
import traceback

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import (
	TimeoutException, 
	StaleElementReferenceException,
	ElementNotInteractableException,
	NoSuchElementException,
	WebDriverException
)

from browser_use.browser.views import BrowserError, BrowserState, TabInfo, URLNotAllowedError
from browser_use.dom.service import DomService
from browser_use.dom.views import DOMElementNode, DOMTextNode, SelectorMap
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

		save_downloads_path: None
			Path to save downloads to

		locale: None
			Specify user locale, for example en-GB, de-DE, etc.

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

	cookies_file: Optional[str] = None
	minimum_wait_page_load_time: float = 0.5
	wait_for_network_idle_page_load_time: float = 1
	maximum_wait_page_load_time: float = 5
	wait_between_actions: float = 1

	disable_security: bool = False

	browser_window_size: BrowserContextWindowSize = field(default_factory=lambda: {'width': 1280, 'height': 1100})
	save_downloads_path: Optional[str] = None
	locale: Optional[str] = None
	user_agent: str = (
		'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/85.0.4183.102 Safari/537.36'
	)

	highlight_elements: bool = True
	viewport_expansion: int = 500
	allowed_domains: Optional[List[str]] = None
	include_dynamic_attributes: bool = True


@dataclass
class BrowserSession:
	driver: webdriver.Remote
	cached_state: BrowserState
	original_window_handle: str


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

		# Initialize these as None - they'll be set up when needed
		self.session: Optional[BrowserSession] = None
		self.dom_service = DomService()

	async def __aenter__(self):
		"""Async context manager entry"""
		await self._initialize_session()
		return self

	async def __aexit__(self, exc_type, exc_val, exc_tb):
		"""Async context manager exit"""
		await self.close()

	async def close(self):
		"""Close the browser context"""
		logger.debug('Closing browser context')

		try:
			# check if already closed
			if self.session is None:
				return

			await self.save_cookies()

			try:
				# No need to close context in Selenium, as it's just the driver
				# If we want to close the current window but keep the driver alive:
				if len(self.session.driver.window_handles) > 1:
					self.session.driver.close()  # Close current window
					# Switch to first window
					self.session.driver.switch_to.window(self.session.driver.window_handles[0])
			except Exception as e:
				logger.debug(f'Failed to close window: {e}')
		finally:
			self.session = None

	def __del__(self):
		"""Cleanup when object is destroyed"""
		if self.session is not None:
			logger.debug('BrowserContext was not properly closed before destruction')
			try:
				# As a last resort, try to close window
				try:
					if len(self.session.driver.window_handles) > 1:
						self.session.driver.close()  # Close current window
				except:
					pass
				self.session = None
			except Exception as e:
				logger.warning(f'Failed to force close browser context: {e}')

	async def _initialize_session(self):
		"""Initialize the browser session"""
		logger.debug('Initializing browser context')

		driver = await self.browser.get_webdriver()
		
		# Configure window size
		driver.set_window_size(
			self.config.browser_window_size['width'],
			self.config.browser_window_size['height']
		)

		# Store original window handle
		original_window = driver.current_window_handle

		# Set up downloads directory if specified
		if self.config.save_downloads_path:
			# This would need to be set during driver creation, not here
			# We'll assume it was done in browser.py
			pass
			
		# Load cookies if they exist
		if self.config.cookies_file and os.path.exists(self.config.cookies_file):
			# First navigate to a page in the domain (required for cookie setting)
			driver.get("about:blank")
			
			with open(self.config.cookies_file, 'r') as f:
				cookies = json.load(f)
				logger.info(f'Loaded {len(cookies)} cookies from {self.config.cookies_file}')
				for cookie in cookies:
					# Clean cookie data to handle format differences
					if 'sameSite' in cookie:
						if cookie['sameSite'] == 'None':
							cookie['sameSite'] = 'Strict'
					try:
						driver.add_cookie(cookie)
					except Exception as e:
						logger.debug(f"Failed to add cookie: {e}")

		# Create initial state - creates a blank page if needed
		if not driver.current_url or driver.current_url == "data:,":
			driver.get("about:blank")
		
		initial_state = self._get_initial_state()

		self.session = BrowserSession(
			driver=driver,
			cached_state=initial_state,
			original_window_handle=original_window,
		)
		
		return self.session

	async def get_session(self) -> BrowserSession:
		"""Lazy initialization of the browser and related components"""
		if self.session is None:
			return await self._initialize_session()
		return self.session

	async def get_current_driver(self) -> webdriver.Remote:
		"""Get the current driver"""
		session = await self.get_session()
		return session.driver

	async def get_current_page(self):
		"""
		Compatibility method for Playwright migration.
		In Selenium, there's no separate page object - we just return self since
		the BrowserContext handles page operations directly.
		"""
		await self.get_session()  # Ensure session is initialized
		return self
		
	async def goto(self, url: str):
		"""
		Compatibility method for Playwright migration.
		Calls navigate_to method to handle URL navigation.
		"""
		return await self.navigate_to(url)

	async def content(self) -> str:
		"""
		Compatibility method for Playwright migration.
		Returns the full HTML content of the page.
		"""
		return await self.get_page_html()

	async def wait_for_load_state(self, state: str = "load", timeout: Optional[float] = None):
		"""
		Compatibility method for Playwright migration.
		Waits for a specific load state of the page.
		
		Args:
			state: One of "load", "domcontentloaded", "networkidle". Defaults to "load".
			timeout: Maximum time to wait in seconds. Defaults to config's maximum_wait_page_load_time.
		"""
		if state == "networkidle":
			# For networkidle, wait a bit longer to ensure network requests complete
			await self._wait_for_page_load(timeout_overwrite=timeout)
			await asyncio.sleep(self.config.wait_for_network_idle_page_load_time)
		else:
			# For load and domcontentloaded, use standard wait
			await self._wait_for_page_load(timeout_overwrite=timeout)

	async def _wait_for_page_load(self, timeout_overwrite: Optional[float] = None):
		"""Wait for the page to load"""
		driver = await self.get_current_driver()
		timeout = timeout_overwrite or self.config.maximum_wait_page_load_time
		
		# Wait for minimum time
		await asyncio.sleep(self.config.minimum_wait_page_load_time)
		
		try:
			# Wait for document ready state
			WebDriverWait(driver, timeout).until(
				lambda d: d.execute_script('return document.readyState') == 'complete'
			)
			
			# Wait for network idle (approximation)
			await asyncio.sleep(self.config.wait_for_network_idle_page_load_time)
			
		except TimeoutException:
			logger.warning(f"Page load timed out after {timeout} seconds")
		
		return
	
	def _is_url_allowed(self, url: str) -> bool:
		"""Check if the URL is allowed based on the allowed_domains configuration"""
		if not self.config.allowed_domains:
			return True
			
		try:
			from urllib.parse import urlparse
			hostname = urlparse(url).hostname
			
			if not hostname:
				return True
				
			for domain in self.config.allowed_domains:
				if hostname == domain or hostname.endswith(f".{domain}"):
					return True
					
			return False
		except Exception as e:
			logger.error(f"Error checking allowed URL: {e}")
			return True
	
	async def _check_and_handle_navigation(self) -> None:
		"""Check if the current URL is allowed and handle navigation if needed"""
		driver = await self.get_current_driver()
		current_url = driver.current_url
		
		if not self._is_url_allowed(current_url):
			logger.warning(f"Navigation to disallowed URL: {current_url}")
			raise URLNotAllowedError(f"Navigation to URL '{current_url}' is not allowed.")

	async def navigate_to(self, url: str):
		"""Navigate to a URL"""
		if not self._is_url_allowed(url):
			raise URLNotAllowedError(f"Navigation to URL '{url}' is not allowed.")
			
		driver = await self.get_current_driver()
		driver.get(url)
		await self._wait_for_page_load()
		await self._check_and_handle_navigation()

	async def refresh_page(self):
		"""Refresh the current page"""
		driver = await self.get_current_driver()
		driver.refresh()
		await self._wait_for_page_load()
		await self._check_and_handle_navigation()

	async def go_back(self):
		"""Go back to the previous page"""
		driver = await self.get_current_driver()
		driver.back()
		await self._wait_for_page_load()
		await self._check_and_handle_navigation()

	async def go_forward(self):
		"""Go forward to the next page"""
		driver = await self.get_current_driver()
		driver.forward()
		await self._wait_for_page_load() 
		await self._check_and_handle_navigation()

	async def close_current_tab(self):
		"""Close the current tab"""
		driver = await self.get_current_driver()
		
		# Don't close if it's the last tab
		if len(driver.window_handles) <= 1:
			logger.warning("Cannot close the last tab")
			return
			
		# Close current window and switch to first available
		driver.close()
		driver.switch_to.window(driver.window_handles[0])
		await self._wait_for_page_load()

	async def get_page_html(self) -> str:
		"""Get the HTML of the current page"""
		driver = await self.get_current_driver()
		return driver.page_source

	async def execute_javascript(self, script: str, *args):
		"""Execute JavaScript in the browser"""
		driver = await self.get_current_driver()
		return driver.execute_script(script, *args)

	@time_execution_sync('--get_state')
	async def get_state(self) -> BrowserState:
		"""Get the browser state"""
		session = await self.get_session()
		if session.cached_state:
			return session.cached_state
		else:
			return await self._update_state()

	async def _update_state(self, focus_element: int = -1) -> BrowserState:
		"""Update the browser state"""
		session = await self.get_session()
		driver = session.driver
		
		# Wait for page to stabilize
		await self._wait_for_page_load()
		
		try:
			# Get the DOM tree
			dom_tree = await self.dom_service.extract_dom_tree(
				self,
				viewport_expansion=self.config.viewport_expansion
			)
			
			# Get active tab info
			tabs = await self.get_tabs_info()
			
			# Get current window handle to track active tab
			current_handle = driver.current_window_handle
			
			# Generate selector map
			selector_map = await self.get_selector_map()
			
			# Highlight elements if configured
			if self.config.highlight_elements and dom_tree and focus_element >= 0:
				# Find the element to highlight
				element_to_highlight = None
				if focus_element in selector_map:
					element_to_highlight = selector_map[focus_element]
				
				if element_to_highlight:
					# Highlight in DOM with JavaScript
					js_highlight = """
					function highlightElement(element) {
						var originalBackground = element.style.backgroundColor;
						var originalBorder = element.style.border;
						element.style.backgroundColor = 'rgba(255, 165, 0, 0.3)';
						element.style.border = '2px solid orange';
						setTimeout(function() {
							element.style.backgroundColor = originalBackground;
							element.style.border = originalBorder;
						}, 3000);
					}
					return highlightElement(arguments[0]);
					"""
					
					try:
						web_element = await self.get_element_by_index(focus_element)
						if web_element:
							driver.execute_script(js_highlight, web_element)
					except Exception as e:
						logger.debug(f"Failed to highlight element: {e}")
			
			# Take screenshot if configured
			screenshot = None
			try:
				screenshot = await self.take_screenshot()
			except Exception as e:
				logger.error(f"Failed to take screenshot: {e}")
			
			# Create and cache the browser state
			state = BrowserState(
				element_tree=dom_tree,
				selector_map=selector_map,
				url=driver.current_url,
				title=driver.title,
				screenshot=screenshot,
				tabs=tabs
			)
			session.cached_state = state
			return state
		
		except Exception as e:
			logger.error(f"Error updating browser state: {e}")
			logger.error(traceback.format_exc())
			
			# Return a minimal state in case of error
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
				url=driver.current_url if driver else "",
				title=driver.title if driver else "",
				screenshot=None,
				tabs=[]
			)

	async def take_screenshot(self, full_page: bool = False) -> str:
		"""
		Returns a base64 encoded screenshot of the current page.
		"""
		driver = await self.get_current_driver()
		
		# For full page screenshot, we need to use a different approach
		if full_page:
			# Scroll to capture full page (simplified implementation)
			total_height = driver.execute_script("return document.body.scrollHeight")
			viewport_height = driver.execute_script("return window.innerHeight")
			
			# Create a canvas the size of the page
			create_canvas = """
			var canvas = document.createElement('canvas');
			canvas.width = window.innerWidth;
			canvas.height = arguments[0];
			canvas.style.position = 'absolute';
			canvas.style.top = '0';
			canvas.style.left = '0';
			canvas.style.zIndex = '-1';
			document.body.appendChild(canvas);
			return canvas;
			"""
			canvas = driver.execute_script(create_canvas, total_height)
			
			# Scroll through page and capture each part
			original_scroll = driver.execute_script("return window.scrollY")
			for y_pos in range(0, total_height, viewport_height):
				driver.execute_script(f"window.scrollTo(0, {y_pos})")
				await asyncio.sleep(0.1)  # Wait for rendering
				
				# Draw the current viewport to canvas at the right position
				draw_to_canvas = """
				var ctx = arguments[0].getContext('2d');
				var img = new Image();
				img.src = arguments[1];
				ctx.drawImage(img, 0, arguments[2], window.innerWidth, window.innerHeight);
				"""
				# Take screenshot of current viewport
				viewport_screenshot = driver.get_screenshot_as_base64()
				driver.execute_script(
					draw_to_canvas,
					canvas,
					f"data:image/png;base64,{viewport_screenshot}",
					y_pos
				)
			
			# Return to original scroll position
			driver.execute_script(f"window.scrollTo(0, {original_scroll})")
			
			# Get the final full screenshot from canvas
			get_canvas_image = "return arguments[0].toDataURL('image/png').split(',')[1];"
			full_screenshot = driver.execute_script(get_canvas_image, canvas)
			
			# Clean up
			driver.execute_script("arguments[0].remove()", canvas)
			
			return full_screenshot
		else:
			# Regular viewport screenshot
			screenshot = driver.get_screenshot_as_base64()
			return screenshot

	async def remove_highlights(self):
		"""
		Removes all highlight overlays and labels created by the highlightElement function.
		"""
		try:
			driver = await self.get_current_driver()
			driver.execute_script("""
			try {
				// Remove highlight styles
				document.querySelectorAll('[browser-user-highlight-id]').forEach(el => {
					el.style.backgroundColor = '';
					el.style.border = '';
					el.removeAttribute('browser-user-highlight-id');
				});
			} catch (e) {
				console.error('Failed to remove highlights:', e);
			}
			""")
		except Exception as e:
			logger.debug(f'Failed to remove highlights (this is usually ok): {str(e)}')
			# Don't raise the error since this is not critical functionality

	@classmethod
	def _convert_xpath_to_css_selector(cls, xpath: str) -> str:
		"""
		Convert a simple XPath to CSS selector when possible.
		For complex XPaths, returns an empty string.
		"""
		# This is a simplified conversion - only handles basic cases
		if not xpath or not xpath.startswith('//'):
			return ""
			
		# Remove leading //
		xpath = xpath[2:]
		
		# Split the xpath parts
		parts = xpath.split('/')
		css_parts = []
		
		for part in parts:
			if not part:
				continue
				
			# Check for predicates
			if '[' in part:
				tag_name, predicate = part.split('[', 1)
				predicate = predicate.rstrip(']')
				
				# Handle position predicates
				if predicate.isdigit() or predicate.startswith('position()='):
					pos = predicate if predicate.isdigit() else predicate.split('=')[1]
					css_parts.append(f"{tag_name}:nth-of-type({pos})")
				# Handle attribute predicates
				elif '@' in predicate:
					attr = predicate.replace('@', '')
					if '=' in attr:
						attr_name, attr_value = attr.split('=', 1)
						# Remove quotes from attribute value
						attr_value = attr_value.strip('"\'')
						css_parts.append(f"{tag_name}[{attr_name}='{attr_value}']")
					else:
						css_parts.append(f"{tag_name}[{attr}]")
				else:
					# Can't handle complex predicates
					return ""
			else:
				css_parts.append(part)
				
		return ' > '.join(css_parts)

	@classmethod
	def _enhanced_css_selector_for_element(cls, element: DOMElementNode, include_dynamic_attributes: bool = True) -> str:
		"""
		Creates a more specific CSS selector for an element using attributes.
		"""
		if not element:
			return ""
			
		tag_name = element.tag_name.lower()
		if tag_name == "#text" or tag_name == "#comment":
			return ""
			
		# Start with the tag name
		selector = tag_name
		
		# Add id if available (most specific)
		if element.attributes.get('id'):
			id_value = element.attributes['id']
			# Clean the id value of any special characters
			clean_id = re.sub(r'[:"\'`.()\[\]\/\\]', '\\\\$&', id_value)
			return f"{selector}#'{clean_id}'"
			
		# Add useful identifying attributes
		attr_selectors = []
		
		# Add static identifying attributes
		priority_attrs = ['name', 'type', 'role', 'aria-label', 'title', 'href', 'placeholder']
		for attr in priority_attrs:
			if attr in element.attributes and element.attributes[attr]:
				value = element.attributes[attr]
				value = re.sub(r'[:"\'`.()\[\]\/\\]', '\\\\$&', value)
				attr_selectors.append(f"[{attr}='{value}']")
				
		# Include dynamic attributes if requested
		if include_dynamic_attributes:
			# Add data attributes
			for attr, value in element.attributes.items():
				if attr.startswith('data-') and value:
					value = re.sub(r'[:"\'`.()\[\]\/\\]', '\\\\$&', value)
					attr_selectors.append(f"[{attr}='{value}']")
		
		# Add classes selectively (not all, as they can change)
		if 'class' in element.attributes and element.attributes['class']:
			classes = element.attributes['class'].split()
			stable_classes = [c for c in classes if not c.startswith('js-') and len(c) > 2]
			if stable_classes:
				# Take up to 2 classes to avoid over-specification
				for cls in stable_classes[:2]:
					cls = re.sub(r'[:"\'`.()\[\]\/\\]', '\\\\$&', cls)
					attr_selectors.append(f".{cls}")
					
		# Combine tag with attribute selectors
		if attr_selectors:
			selector += ''.join(attr_selectors)
			
		return selector

	async def get_locate_element(self, element: DOMElementNode) -> Optional[WebElement]:
		"""
		Locate an element in the current page based on the DOM element node.
		"""
		driver = await self.get_current_driver()
		
		if not element:
			return None
			
		# Try different locator strategies in order of reliability
		try:
			# 1. Try locating by XPath
			if element.xpath:
				try:
					return driver.find_element(By.XPATH, element.xpath)
				except (NoSuchElementException, WebDriverException):
					pass
					
			# 2. Try CSS selector derived from the element
			css_selector = self._enhanced_css_selector_for_element(
				element, 
				include_dynamic_attributes=self.config.include_dynamic_attributes
			)
			if css_selector:
				try:
					return driver.find_element(By.CSS_SELECTOR, css_selector)
				except (NoSuchElementException, WebDriverException):
					pass
					
			# 3. Try simpler CSS selector based on tag and id/class
			simple_selector = ""
			if element.tag_name and element.tag_name != "#text":
				simple_selector = element.tag_name.lower()
				
				if 'id' in element.attributes and element.attributes['id']:
					simple_selector += f"#{element.attributes['id']}"
				elif 'class' in element.attributes and element.attributes['class']:
					classes = element.attributes['class'].split()
					if classes:
						simple_selector += f".{classes[0]}"
						
			if simple_selector:
				try:
					return driver.find_element(By.CSS_SELECTOR, simple_selector)
				except (NoSuchElementException, WebDriverException):
					pass
					
			# 4. Try to find by text content
			if isinstance(element, DOMElementNode):
				element_text = ""
				# Get text from child text nodes
				for child in element.children:
					if isinstance(child, DOMTextNode):
						element_text += child.text
				
				if element_text and element_text.strip():
					try:
						return driver.find_element(By.XPATH, f"//*[contains(text(), '{element_text}')]")
					except (NoSuchElementException, WebDriverException):
						pass
					
			# Failed to locate element
			return None
			
		except Exception as e:
			logger.error(f"Error locating element: {e}")
			return None

	async def _input_text_element_node(self, element_node: DOMElementNode, text: str):
		"""Input text into an element"""
		driver = await self.get_current_driver()
		element = await self.get_locate_element(element_node)
		
		if not element:
			raise Exception(f"Could not locate element from node: {element_node.tag_name}")
			
		try:
			# Clear existing text
			element.clear()
			
			# Send the new text
			element.send_keys(text)
			
			# Wait a bit for the page to process the input
			await asyncio.sleep(0.3)
			
			return True
		except Exception as e:
			logger.error(f"Error inputting text: {e}")
			raise

	async def _click_element_node(self, element_node: DOMElementNode) -> Optional[str]:
		"""Click an element on the page"""
		driver = await self.get_current_driver()
		element = await self.get_locate_element(element_node)
		
		if not element:
			raise Exception(f"Could not locate element from node {element_node.tag_name}")
			
		# Store original window handles to detect new windows
		original_handles = driver.window_handles
		
		# Check if element could trigger file upload dialog
		is_file_uploader = await self.is_file_uploader(element_node)
		if is_file_uploader:
			raise Exception("Element appears to be a file uploader. Use a file upload action instead.")
			
		# Try different click methods
		async def try_click_methods():
			# Store the number of windows before clicking
			window_count_before = len(driver.window_handles)
			download_path = None
			
			try:
				# Method 1: Standard click
				try:
					element.click()
					await asyncio.sleep(0.5)  # Wait for potential navigation
					return True
				except Exception as e1:
					logger.debug(f"Standard click failed: {e1}")
				
				# Method 2: JavaScript click
				try:
					driver.execute_script("arguments[0].click();", element)
					await asyncio.sleep(0.5)
					return True
				except Exception as e2:
					logger.debug(f"JavaScript click failed: {e2}")
				
				# Method 3: ActionChains click
				try:
					actions = ActionChains(driver)
					actions.move_to_element(element).click().perform()
					await asyncio.sleep(0.5)
					return True
				except Exception as e3:
					logger.debug(f"ActionChains click failed: {e3}")
				
				# Method 4: Click with coordinates (center of element)
				try:
					actions = ActionChains(driver)
					actions.move_to_element_with_offset(
						element, 
						element.size['width']//2, 
						element.size['height']//2
					).click().perform()
					await asyncio.sleep(0.5)
					return True
				except Exception as e4:
					logger.debug(f"Coordinate click failed: {e4}")
				
				# If all methods failed
				return False
			
			finally:
				# Check if a new window was opened
				window_count_after = len(driver.window_handles)
				if window_count_after > window_count_before:
					# Switch to the new window
					new_handle = [h for h in driver.window_handles if h not in original_handles][0]
					driver.switch_to.window(new_handle)
					await self._wait_for_page_load()
			
			return download_path
			
		success = await try_click_methods()
		if not success:
			raise Exception(f"Failed to click element with all methods")
			
		# Check for downloads
		download_path = None
		if self.config.save_downloads_path:
			# Wait briefly to see if a download started
			await asyncio.sleep(1)
			# Check downloads folder for new files
			# This would need more implementation
		
		# Wait for any navigation or DOM changes to complete
		await self._wait_for_page_load()
		
		return download_path

	async def get_tabs_info(self) -> List[TabInfo]:
		"""Get information about all open tabs"""
		driver = await self.get_current_driver()
		tabs = []
		
		current_handle = driver.current_window_handle
		
		for i, handle in enumerate(driver.window_handles):
			try:
				# Switch to this window/tab
				driver.switch_to.window(handle)
				
				# Store if this is the active tab
				is_active = (handle == current_handle)
				
				# Get tab info
				tab_info = TabInfo(
					page_id=i,
					title=driver.title or f"Tab {i+1}",
					url=driver.current_url
				)
				tabs.append(tab_info)
				
				# Add debug log for tracking active tab
				if is_active:
					logger.debug(f"Active tab: {tab_info.title} (ID: {tab_info.page_id})")
					
			except Exception as e:
				logger.error(f"Error getting tab info: {e}")
				tabs.append(TabInfo(
					page_id=i,
					title=f"Tab {i+1}",
					url=""
				))
				
		# Switch back to original tab
		driver.switch_to.window(current_handle)
		
		return tabs

	async def switch_to_tab(self, tab_id: int) -> None:
		"""Switch to a specific tab"""
		driver = await self.get_current_driver()
		
		if tab_id < 0:
			# Handle negative indexing (e.g., -1 for last tab)
			handles = driver.window_handles
			tab_id = len(handles) + tab_id
			
		if 0 <= tab_id < len(driver.window_handles):
			driver.switch_to.window(driver.window_handles[tab_id])
			await self._wait_for_page_load()
		else:
			raise ValueError(f"Tab ID {tab_id} is out of range")

	async def create_new_tab(self, url: Optional[str] = None) -> None:
		"""Create a new tab and optionally navigate to a URL"""
		driver = await self.get_current_driver()
		
		# Open a new tab
		driver.execute_script("window.open('about:blank');")
		
		# Switch to the new tab (last in the list)
		await self.switch_to_tab(-1)
		
		# Navigate to URL if provided
		if url:
			await self.navigate_to(url)

	async def get_selector_map(self) -> SelectorMap:
		"""Get the selector map from the DOM service"""
		return await self.dom_service.get_selector_map(self)

	async def get_element_by_index(self, index: int) -> Optional[WebElement]:
		"""Get a WebElement by its index in the selector map"""
		session = await self.get_session()
		
		if index not in session.cached_state.selector_map:
			return None
			
		element_node = session.cached_state.selector_map[index]
		return await self.get_locate_element(element_node)

	async def get_dom_element_by_index(self, index: int) -> Optional[DOMElementNode]:
		"""Get a DOM element node by its index in the selector map"""
		session = await self.get_session()
		
		if index not in session.cached_state.selector_map:
			return None
			
		return session.cached_state.selector_map[index]

	async def save_cookies(self):
		"""Save cookies to a file if configured"""
		if not self.config.cookies_file:
			return
			
		try:
			driver = await self.get_current_driver()
			cookies = driver.get_cookies()
			
			# Create directory if it doesn't exist
			cookie_dir = os.path.dirname(self.config.cookies_file)
			if cookie_dir and not os.path.exists(cookie_dir):
				os.makedirs(cookie_dir)
				
			with open(self.config.cookies_file, 'w') as f:
				json.dump(cookies, f)
				
			logger.info(f'Saved {len(cookies)} cookies to {self.config.cookies_file}')
		except Exception as e:
			logger.error(f'Failed to save cookies: {e}')

	async def is_file_uploader(self, element_node: DOMElementNode, max_depth: int = 3, current_depth: int = 0) -> bool:
		"""Check if an element is a file uploader or contains one"""
		# Base case: max recursion depth
		if current_depth > max_depth:
			return False
			
		# Check if element is an input with type="file"
		if (element_node.tag_name.lower() == 'input' and 
			element_node.attributes.get('type', '').lower() == 'file'):
			return True
			
		# Check if element has an input[type="file"] descendant
		for child in element_node.children:
			if isinstance(child, DOMElementNode) and await self.is_file_uploader(child, max_depth, current_depth + 1):
				return True
				
		return False

	async def get_scroll_info(self) -> Tuple[int, int]:
		"""Get scroll position information for the current page"""
		driver = await self.get_current_driver()
		
		scroll_y = driver.execute_script('return window.scrollY;')
		viewport_height = driver.execute_script('return window.innerHeight;')
		total_height = driver.execute_script('return document.documentElement.scrollHeight;')
		
		pixels_above = scroll_y
		pixels_below = total_height - (scroll_y + viewport_height)
		
		return pixels_above, pixels_below

	async def reset_context(self):
		"""Reset the browser context by closing all tabs and opening a new one"""
		driver = await self.get_current_driver()
		
		# Close all tabs except the first one
		handles = driver.window_handles
		current_handle = driver.current_window_handle
		
		# Switch to first tab if not already there
		if current_handle != handles[0]:
			driver.switch_to.window(handles[0])
			
		# Close all other tabs
		for handle in handles[1:]:
			driver.switch_to.window(handle)
			driver.close()
			
		# Go back to first tab
		driver.switch_to.window(handles[0])
		
		# Navigate to blank page
		driver.get("about:blank")
		
		# Reset cached state
		session = await self.get_session()
		session.cached_state = self._get_initial_state()
		
		await self._wait_for_page_load()

	def _get_initial_state(self) -> BrowserState:
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
			url="",
			title="",
			screenshot=None,
			tabs=[],
		)
