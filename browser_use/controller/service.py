import asyncio
import json
import enum
import logging
import os
import browser_use.controller.selenium_snippets as selenium_snippets
from typing import Dict, Generic, Optional, Type, TypeVar, Callable

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from lmnr.sdk.laminar import Laminar
from lmnr.sdk.decorators import observe

from browser_use.agent.views import ActionModel, ActionResult
from browser_use.browser.context import BrowserContext
from browser_use.controller.registry.service import Registry
from browser_use.controller.views import (
	ClickElementAction,
	DoneAction,
	GoToUrlAction,
	InputTextAction,
	NoParamsAction,
	OpenTabAction,
	ScrollAction,
	SearchGoogleAction,
	SendKeysAction,
	SwitchTabAction,
)
from browser_use.utils import time_execution_async, time_execution_sync

logger = logging.getLogger(__name__)


Context = TypeVar('Context')


class Controller(Generic[Context]):
	def __init__(
		self,
		exclude_actions: list[str] = [],
		output_model: Optional[Type[BaseModel]] = None,
  		save_selenium_code: Optional[str] = None,
		save_py: Optional[str] = None,
	):
		if not save_py:
			save_py = "output"

		self.save_py = save_py
		self.save_selenium_code = save_selenium_code

		if self.save_selenium_code and '/' not in self.save_selenium_code:
			self.save_selenium_code = f'{self.save_selenium_code}/'
   
		self._save_selenium_code(selenium_snippets.initial_selenium_code, overwrite=True)
		self.exclude_actions = exclude_actions
		self.output_model = output_model
		self.registry = Registry(exclude_actions)

		"""Register all default browser actions"""

		if output_model is not None:
			# Create a new model that extends the output model with success parameter
			class ExtendedOutputModel(BaseModel):
				success: bool = True
				data: BaseModel

			@self.registry.action(
				'Complete task - with return text and if the task is finished (success=True) or not yet  completly finished (success=False), because last step is reached',
				param_model=ExtendedOutputModel,
			)
			async def done(params: ExtendedOutputModel):
				# Exclude success from the output JSON since it's an internal parameter
				output_dict = params.data.model_dump()

				# Enums are not serializable, convert to string
				for key, value in output_dict.items():
					if isinstance(value, enum.Enum):
						output_dict[key] = value.value

				return ActionResult(is_done=True, extracted_content=json.dumps(output_dict))
		else:

			@self.registry.action(
				'Complete task - with return text and if the task is finished (success=True) or not yet  completly finished (success=False), because last step is reached',
				param_model=DoneAction,
			)
			async def done(params: DoneAction):
				return ActionResult(is_done=True, extracted_content=params.text)

		# Basic Navigation Actions
		@self.registry.action(
			'Search the query in Google in the current tab, the query should be a search query like humans search in Google, concrete and not vague or super long. More the single most important items. ',
			param_model=SearchGoogleAction,
		)
		async def search_google(params: SearchGoogleAction, browser: BrowserContext):
			driver = await browser.get_current_driver()
			driver.get(f'https://www.google.com/search?q={params.query}&udm=14')
			await asyncio.sleep(browser.config.minimum_wait_page_load_time)
			msg = f'🔍  Searched for "{params.query}" in Google'
			logger.info(msg)
			return ActionResult(extracted_content=msg, include_in_memory=True)

		@self.registry.action('Navigate to URL in the current tab', param_model=GoToUrlAction)
		async def go_to_url(params: GoToUrlAction, browser: BrowserContext):
			driver = await browser.get_current_driver()
			driver.get(params.url)
			await asyncio.sleep(browser.config.minimum_wait_page_load_time)
			msg = f'🔗  Navigated to {params.url}'
			logger.info(msg)
   
			selenium_code = selenium_snippets.go_to(params.url)	
			self._save_selenium_code(selenium_code)   
			return ActionResult(extracted_content=msg, include_in_memory=True)

		@self.registry.action('Go back', param_model=NoParamsAction)
		async def go_back(_: NoParamsAction, browser: BrowserContext):
			driver = await browser.get_current_driver()
			driver.back()
			await asyncio.sleep(browser.config.minimum_wait_page_load_time)
			msg = '🔙  Navigated back'
			logger.info(msg)
   
			selenium_code = selenium_snippets.back()
			self._save_selenium_code(selenium_code)
			return ActionResult(extracted_content=msg, include_in_memory=True)

		# wait for x seconds
		@self.registry.action('Wait for x seconds default 3')
		async def wait(seconds: int = 3):
			msg = f'🕒  Waiting for {seconds} seconds'
			logger.info(msg)
			await asyncio.sleep(seconds)
   
			selenium_code = selenium_snippets.sleep(seconds)
			self._save_selenium_code(selenium_code)
			return ActionResult(extracted_content=msg, include_in_memory=True)

		# Element Interaction Actions
		@self.registry.action('Click element', param_model=ClickElementAction)
		async def click_element(params: ClickElementAction, browser: BrowserContext):
			session = await browser.get_session()
			driver = session.driver

			if params.index not in await browser.get_selector_map():
				raise Exception(f'Element with index {params.index} does not exist - retry or use alternative actions')

			element_node = await browser.get_dom_element_by_index(params.index)
			if element_node is None:
				raise Exception(f'Element with index {params.index} could not be found in the DOM')

			initial_windows = len(driver.window_handles)

			# if element has file uploader then dont click
			if await browser.is_file_uploader(element_node):
				msg = f'Index {params.index} - has an element which opens file upload dialog. To upload files please use a specific function to upload files '
				logger.info(msg)
				return ActionResult(extracted_content=msg, include_in_memory=True)

			msg = None

			try:
				download_path = await browser._click_element_node(element_node)
				if download_path:
					msg = f'💾  Downloaded file to {download_path}'
				else:
					msg = f'🖱️  Clicked button with index {params.index}: {element_node.get_all_text_till_next_clickable_element(max_depth=2)}'
				selenium_code = selenium_snippets.click(element_node.xpath)
				self._save_selenium_code(selenium_code)

				logger.info(msg)
				logger.debug(f'Element xpath: {element_node.xpath}')
				# Check if a new window was opened
				if len(driver.window_handles) > initial_windows:
					new_tab_msg = 'New tab opened - switching to it'
					msg += f' - {new_tab_msg}'
					logger.info(new_tab_msg)
					await browser.switch_to_tab(-1)
					selenium_code = selenium_snippets.switch_to_tab(-1)
					self._save_selenium_code(selenium_code)
				return ActionResult(extracted_content=msg, include_in_memory=True)
			except Exception as e:
				logger.warning(f'Element not clickable with index {params.index} - most likely the page changed')
				return ActionResult(error=str(e))

		@self.registry.action(
			'Input text into a input interactive element',
			param_model=InputTextAction,
		)
		async def input_text(params: InputTextAction, browser: BrowserContext, has_sensitive_data: bool = False):
			if params.index not in await browser.get_selector_map():
				raise Exception(f'Element index {params.index} does not exist - retry or use alternative actions')

			element_node = await browser.get_dom_element_by_index(params.index)
			if element_node is None:
				raise Exception(f'Element with index {params.index} could not be found in the DOM')

			await browser._input_text_element_node(element_node, params.text)
			if not has_sensitive_data:
				msg = f'⌨️  Input {params.text} into index {params.index}'
			else:
				msg = f'⌨️  Input sensitive data into index {params.index}'
			logger.info(msg)
			logger.debug(f'Element xpath: {element_node.xpath}')

			selenium_code = selenium_snippets.input_txt(element_node.xpath, params.text)
			self._save_selenium_code(selenium_code)
			return ActionResult(extracted_content=msg, include_in_memory=True)

		# Tab Management Actions
		@self.registry.action('Switch tab', param_model=SwitchTabAction)
		async def switch_tab(params: SwitchTabAction, browser: BrowserContext):
			await browser.switch_to_tab(params.page_id)
			await asyncio.sleep(browser.config.minimum_wait_page_load_time)
			msg = f'🔄  Switched to tab {params.page_id}'
			logger.info(msg)
			selenium_code = selenium_snippets.switch_to_tab(params.page_id)	
			self._save_selenium_code(selenium_code)
			return ActionResult(extracted_content=msg, include_in_memory=True)

		@self.registry.action('Open url in new tab', param_model=OpenTabAction)
		async def open_tab(params: OpenTabAction, browser: BrowserContext):
			await browser.create_new_tab(params.url)
			msg = f'🔗  Opened new tab with {params.url}'
			logger.info(msg)
			selenium_code = selenium_snippets.open_tab(params.url)
			self._save_selenium_code(selenium_code)
			return ActionResult(extracted_content=msg, include_in_memory=True)

		# Content Actions
		@self.registry.action(
			'Extract page content to retrieve specific information from the page, e.g. all company names, a specifc description, all information about, links with companies in structured format or simply links',
		)
		async def extract_content(goal: str, browser: BrowserContext, page_extraction_llm: BaseChatModel):
			driver = await browser.get_current_driver()
			import markdownify

			content = markdownify.markdownify(driver.page_source)

			prompt = 'Your task is to extract the content of the page. You will be given a page and a goal and you should extract all relevant information around this goal from the page. If the goal is vague, summarize the page. Respond in json format. Extraction goal: {goal}, Page: {page}'
			template = PromptTemplate(input_variables=['goal', 'page'], template=prompt)
			try:
				output = page_extraction_llm.invoke(template.format(goal=goal, page=content))
				msg = f'📄  Extracted from page\n: {output.content}\n'
				logger.info(msg)
				return ActionResult(extracted_content=msg, include_in_memory=True)
			except Exception as e:
				logger.debug(f'Error extracting content: {e}')
				msg = f'📄  Extracted from page\n: {content}\n'
				logger.info(msg)
				return ActionResult(extracted_content=msg)

		@self.registry.action(
			'Scroll down the page by pixel amount - if no amount is specified, scroll down one page',
			param_model=ScrollAction,
		)
		async def scroll_down(params: ScrollAction, browser: BrowserContext):
			driver = await browser.get_current_driver()
			if params.amount is not None:
				driver.execute_script(f'window.scrollBy(0, {params.amount});')
			else:
				driver.execute_script('window.scrollBy(0, window.innerHeight);')
			selenium_code = selenium_snippets.scroll_down(params.amount)
			self._save_selenium_code(selenium_code)

			amount = f'{params.amount} pixels' if params.amount is not None else 'one page'
			msg = f'🔍  Scrolled down the page by {amount}'
			logger.info(msg)
			return ActionResult(
				extracted_content=msg,
				include_in_memory=True,
			)

		# scroll up
		@self.registry.action(
			'Scroll up the page by pixel amount - if no amount is specified, scroll up one page',
			param_model=ScrollAction,
		)
		async def scroll_up(params: ScrollAction, browser: BrowserContext):
			driver = await browser.get_current_driver()
			if params.amount is not None:
				driver.execute_script(f'window.scrollBy(0, -{params.amount});')
			else:
				driver.execute_script('window.scrollBy(0, -window.innerHeight);')

			amount = f'{params.amount} pixels' if params.amount is not None else 'one page'
			msg = f'🔍  Scrolled up the page by {amount}'
			logger.info(msg)
   
			selenium_code = selenium_snippets.scroll_up(params.amount)
			self._save_selenium_code(selenium_code)
			return ActionResult(
				extracted_content=msg,
				include_in_memory=True,
			)

		# send keys
		@self.registry.action(
			'Send strings of special keys like Escape,Backspace, Insert, PageDown, Delete, Enter, Shortcuts such as `Control+o`, `Control+Shift+T` are supported as well.',
			param_model=SendKeysAction,
		)
		async def send_keys(params: SendKeysAction, browser: BrowserContext):
			driver = await browser.get_current_driver()

			try:
				# Convert Playwright key notation to Selenium Keys
				key_mapping = {
					"Escape": Keys.ESCAPE,
					"Backspace": Keys.BACK_SPACE,
					"Insert": Keys.INSERT,
					"PageDown": Keys.PAGE_DOWN,
					"Delete": Keys.DELETE,
					"Enter": Keys.ENTER,
					"Control+o": Keys.CONTROL + "o",
					"Control+Shift+T": Keys.CONTROL + Keys.SHIFT + "t",
				}

				active_element = driver.execute_script("""
					const active = document.activeElement;
					const isInteractive = active.tagName !== 'BODY' 
										&& active.tagName !== 'HTML' 
										&& active !== document.body;
					return isInteractive;
				""")
				if not active_element:
					main_page = driver.find_element(By.TAG_NAME, 'body')
					main_page.click()

					# Find the matching key or use the original
					# key_to_send = key_mapping.get(params.keys, params.keys)

					# # Create action chain and perform key press
					# actions = ActionChains(driver)
					# actions.send_keys(key_to_send)
					# actions.perform()

				keys = params.keys

				if '+' in keys:
					keys_spl = keys.split('+')
					modifiers = keys_spl[:-1]  # todas as teclas exceto a última
					final_key = keys_spl[-1]   # última tecla

					actions = ActionChains(driver)
					# Adiciona key_down para cada modificador
					for mod in modifiers:
						mod_key = key_mapping.get(mod, f"'{mod}'")
						actions.key_down(mod_key)

					# Adiciona a tecla final
					final_selenium_key = key_mapping.get(final_key, f"'{final_key}'")
					actions.send_keys(final_selenium_key)

					# Adiciona key_up para cada modificador (em ordem reversa)
					for mod in reversed(modifiers):
						mod_key = key_mapping.get(mod, f"'{mod}'")
						actions.key_up(mod_key)

					actions.perform()

				else:
					# Tecla única (não é atalho)
					selenium_key = key_mapping.get(keys, f"'{keys}'")
					
					actions = ActionChains(driver)
					actions.send_keys(selenium_key)
					actions.perform()
			
			except Exception as e:
				logger.debug(f'Error sending keys: {str(e)}')
				raise e
				
			msg = f'⌨️  Sent keys: {params.keys}'

			selenium_code = selenium_snippets.send_keys(params.keys)
			self._save_selenium_code(selenium_code)
			logger.info(msg)
			return ActionResult(extracted_content=msg, include_in_memory=True)

		@self.registry.action(
			description='If you dont find something which you want to interact with, scroll to it',
		)
		async def scroll_to_text(text: str, browser: BrowserContext):  # type: ignore
			driver = await browser.get_current_driver()
			try:
				# Try different locator strategies with Selenium
				locator_strategies = [
					(By.XPATH, f"//*[contains(text(), '{text}')]"),
					(By.LINK_TEXT, text),
					(By.PARTIAL_LINK_TEXT, text)
				]

				for by, locator in locator_strategies:
					try:
						# First check if element exists
						elements = driver.find_elements(by, locator)
						if elements and len(elements) > 0:
							# Scroll to the element with JavaScript
							driver.execute_script("arguments[0].scrollIntoView();", elements[0])
							await asyncio.sleep(0.5)  # Wait for scroll to complete
							msg = f'🔍  Scrolled to text: {text}'
							logger.info(msg)
							selenium_code = selenium_snippets.scroll_to_text(text)
							self._save_selenium_code(selenium_code)
							return ActionResult(extracted_content=msg, include_in_memory=True)
					except Exception as e:
						logger.debug(f'Locator attempt failed: {str(e)}')
						continue

				msg = f"Text '{text}' not found or not visible on page"
				logger.info(msg)
				return ActionResult(extracted_content=msg, include_in_memory=True)

			except Exception as e:
				msg = f"Failed to scroll to text '{text}': {str(e)}"
				logger.error(msg)
				return ActionResult(error=msg, include_in_memory=True)

		@self.registry.action(
			description='Get all options from a native dropdown',
		)
		async def get_dropdown_options(index: int, browser: BrowserContext) -> ActionResult:
			"""Get all options from a native dropdown"""
			if index not in await browser.get_selector_map():
				raise Exception(f'Element index {index} does not exist')

			dom_element = await browser.get_dom_element_by_index(index)
			if dom_element is None:
				raise Exception(f'Element with index {index} could not be found in the DOM')

			driver = await browser.get_current_driver()

			# Ensure we're working with a SELECT element
			tag_name = dom_element.tag_name.lower()
			if tag_name != "select":
				return ActionResult(
					error=f"Element at index {index} is a {tag_name}, not a SELECT",
					include_in_memory=True,
				)

			# Use Selenium's Select class for dropdowns
			try:
				# Get the dropdown element using XPath
				dropdown_element = driver.find_element(By.XPATH, dom_element.xpath)
				
				# Create a Select object
				select = Select(dropdown_element)
				
				# Get all options
				options = [option.text for option in select.options]
				
				# Get the currently selected option
				selected = select.first_selected_option.text if select.options else None
				
				result = {
					"options": options,
					"selected": selected,
					"count": len(options)
				}
				
				msg = f"📝 Dropdown options: {json.dumps(result)}"
				logger.info(msg)
				return ActionResult(extracted_content=msg, include_in_memory=True)
				
			except Exception as e:
				logger.error(f"Error getting dropdown options: {str(e)}")
				return ActionResult(error=f"Failed to get dropdown options: {str(e)}")

		@self.registry.action(
			description='Select dropdown option for interactive element index by the text of the option you want to select',
		)
		async def select_dropdown_option(
			index: int,
			text: str,
			browser: BrowserContext,
		) -> ActionResult:
			"""Select a dropdown option by text"""
			if index not in await browser.get_selector_map():
				raise Exception(f'Element index {index} does not exist')

			dom_element = await browser.get_dom_element_by_index(index)
			if dom_element is None:
				raise Exception(f'Element with index {index} could not be found in the DOM')

			driver = await browser.get_current_driver()

			# Ensure we're working with a SELECT element
			tag_name = dom_element.tag_name.lower()
			if tag_name != "select":
				return ActionResult(
					error=f"Element at index {index} is a {tag_name}, not a SELECT",
					include_in_memory=True,
				)

			# Use Selenium's Select class for handling dropdowns
			try:
				# Get the dropdown element using XPath
				# dropdown_element = driver.find_element(By.XPATH, dom_element.xpath)
				
				# # Create a Select object
				# select = Select(dropdown_element)
				
				# # Select by visible text
				# select.select_by_visible_text(text)

				# First check if element is in an iframe
				iframes = driver.find_elements(By.TAG_NAME, "iframe")
				found_in_frame = False
				# Check main frame first
				try:
					dropdown = WebDriverWait(driver, 10).until(
						EC.presence_of_element_located((By.XPATH, '{dropdown_xpath}'))
					)
					select = Select(dropdown)
					select.select_by_visible_text("{text}")
					found_in_frame = True
				except:
					pass
				# If not found in main frame, check iframes
				if not found_in_frame:
					for frame in iframes:
						try:
							driver.switch_to.frame(frame)
							dropdown = WebDriverWait(driver, 10).until(
								EC.presence_of_element_located((By.XPATH, '{dropdown_xpath}'))
							)
							select = Select(dropdown)
							select.select_by_visible_text("{text}")
							found_in_frame = True
							break
						except:
							driver.switch_to.default_content()
							continue
					# Switch back to default content after checking frames
					driver.switch_to.default_content()
				if not found_in_frame:
					print(f"Could not select option '{text}' in any frame")
				
				msg = f"Selected option '{text}' from dropdown at index {index}"
				logger.info(msg)
    
				selenium_code = selenium_snippets.select_dropdown_option(dom_element.xpath, text)
				self._save_selenium_code(selenium_code)
				return ActionResult(extracted_content=msg, include_in_memory=True)
				
			except Exception as e:
				logger.error(f"Error selecting dropdown option: {str(e)}")
				return ActionResult(error=f"Failed to select dropdown option: {str(e)}")

	# Pass through the action method for custom actions
	def action(self, description: str, **kwargs):
		"""Register a custom action"""
		return self.registry.action(description, **kwargs)


	@observe(name='controller.multi_act')
	@time_execution_async('--multi-act')
	async def multi_act(
 		self,
 		actions: list[ActionModel],
 		browser_context: BrowserContext,
 		check_break_if_paused: Callable[[], bool],
 		check_for_new_elements: bool = True,
 		page_extraction_llm: Optional[BaseChatModel] = None,
 		sensitive_data: Optional[Dict[str, str]] = None,
 	) -> list[ActionResult]:
		"""Execute multiple actions"""
		results = []

		session = await browser_context.get_session()
		cached_selector_map = session.cached_state.selector_map
		cached_path_hashes = set(e.hash.branch_path_hash for e in cached_selector_map.values())

		check_break_if_paused()

		await browser_context.remove_highlights()

		for i, action in enumerate(actions):
			check_break_if_paused()

			if action.get_index() is not None and i != 0:
				new_state = await browser_context.get_state()
				new_path_hashes = set(e.hash.branch_path_hash for e in new_state.selector_map.values())
				if check_for_new_elements and not new_path_hashes.issubset(cached_path_hashes):
					# next action requires index but there are new elements on the page
					msg = f'Something new appeared after action {i} / {len(actions)}'
					logger.info(msg)
					results.append(ActionResult(extracted_content=msg, include_in_memory=True))
					break

			check_break_if_paused()

			results.append(await self.act(action, browser_context, page_extraction_llm, sensitive_data))

			logger.debug(f'Executed action {i + 1} / {len(actions)}')
			if results[-1].is_done or results[-1].error or i == len(actions) - 1:
				break

			await asyncio.sleep(browser_context.config.wait_between_actions)
			# hash all elements. if it is a subset of cached_state its fine - else break (new elements on page)

		return results

	# Act --------------------------------------------------------------------

	@time_execution_sync('--act')
	async def act(
		self,
		action: ActionModel,
		browser_context: BrowserContext,
		#
		page_extraction_llm: Optional[BaseChatModel] = None,
		sensitive_data: Optional[Dict[str, str]] = None,
	) -> ActionResult:
		"""Execute an action"""

		try:
			for action_name, params in action.model_dump(exclude_unset=True).items():
				if params is not None:
					result = await self.registry.execute_action(
						action_name,
						params,
						browser=browser_context,
						page_extraction_llm=page_extraction_llm,
						sensitive_data=sensitive_data,
					)

					if isinstance(result, str):
						return ActionResult(extracted_content=result)
					elif isinstance(result, ActionResult):
						return result
					elif result is None:
						return ActionResult()
					else:
						raise ValueError(f'Invalid action result type: {type(result)} of {result}')
			return ActionResult()
		except Exception as e:
			raise e

	def _save_selenium_code(self, selenium_action: str, overwrite: bool = False) -> None:
		"""Create directory and save Selenium action to a separate code file if path is specified"""
		if not self.save_selenium_code:
			return 
		os.makedirs(os.path.dirname(self.save_selenium_code), exist_ok=True)        # Save the Selenium action to a dedicated .py file per action
		file_path = f"{self.save_selenium_code}{self.save_py}.py"

		with open(file_path, 'w' if overwrite else 'a', encoding='utf-8') as f:
			f.write(selenium_action + '\n')