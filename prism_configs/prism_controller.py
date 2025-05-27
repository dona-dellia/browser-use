from browser_use import Agent, Controller, ActionResult, Browser
from browser_use.browser.context import BrowserContext
import browser_use.controller.selenium_snippets as selenium_snippets

import logging
logger = logging.getLogger(__name__)

controller = Controller(exclude_actions=['search_google','get_dropdown_options','select_dropdown_option','scroll_down','scroll_to_text','scroll_up'],save_py="code", save_selenium_code="output/")

@controller.action(
    description='Scroll down a specific element by a number of pixels using its index in the selector map.',
)
async def scroll_down_element(pixels: int, index: int, browser: BrowserContext) -> ActionResult:
    """
    Scrolls a DOM element (by index from selector_map) vertically by a given number of pixels.
    """
    try:
        # Recupera o DOMElementNode correspondente ao índice
        element_node = await browser.get_dom_element_by_index(index)
        if not element_node:
            return f"Elemento de índice {index} não encontrado no selector_map."

        # Localiza o WebElement real
        element = await browser.get_locate_element(element_node)
        if not element:
            return f"Falha ao localizar o elemento com índice {index} no DOM."

        # Rola o scroll DENTRO do elemento (não na janela)
        driver = await browser.get_current_driver()
        driver.execute_script("arguments[0].scrollTop += arguments[1];", element, pixels)
        selenium_code = selenium_snippets.scroll_down_element(element_node.xpath, pixels)
        
        controller._save_selenium_code(selenium_code)
        msg = f'🧭 Scrolled element at index {index} down by {pixels}px'
        logger.info(msg)
        return ActionResult(extracted_content=msg, include_in_memory=True)

    except Exception as e:
        error_msg = f'Error scrolling element at index {index}: {str(e)}'
        logger.error(error_msg)
        return ActionResult(error=error_msg, include_in_memory=True)

@controller.action(
    description='Scroll up a specific element by a number of pixels using its index in the selector map.',
)
async def scroll_up_element(pixels: int, index: int, browser: BrowserContext) -> ActionResult:
    """
    Scrolls a DOM element (by index from selector_map) vertically by a given number of pixels.
    """
    try:
        # Recupera o DOMElementNode correspondente ao índice
        element_node = await browser.get_dom_element_by_index(index)
        if not element_node:
            return f"Elemento de índice {index} não encontrado no selector_map."

        # Localiza o WebElement real
        element = await browser.get_locate_element(element_node)
        if not element:
            return f"Falha ao localizar o elemento com índice {index} no DOM."

        # Rola o scroll DENTRO do elemento (não na janela)
        driver = await browser.get_current_driver()
        driver.execute_script("arguments[0].scrollTop -= arguments[1];", element, pixels)
        selenium_code = selenium_snippets.scroll_up_element(element_node.xpath, pixels)
        
        controller._save_selenium_code(selenium_code)
        msg = f'🧭 Scrolled element at index {index} down by {pixels}px'
        logger.info(msg)
        return ActionResult(extracted_content=msg, include_in_memory=True)

    except Exception as e:
        error_msg = f'Error scrolling element at index {index}: {str(e)}'
        logger.error(error_msg)
        return ActionResult(error=error_msg, include_in_memory=True)
