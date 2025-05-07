from browser_use import Agent, Controller, ActionResult, Browser
from browser_use.browser.context import BrowserContext
import logging
logger = logging.getLogger(__name__)

controller = Controller(exclude_actions=['search_google','get_dropdown_options','select_dropdown_option','scroll_down','scroll_to_text','scroll_up'])

@controller.action(
    description='Scroll down a specific element by a number of pixels using its index in the selector map.',
)
async def scroll_down_element(pixels: int, index: int, browser: BrowserContext) -> ActionResult:
    """
    Scrolls a DOM element (by index from selector_map) vertically by a given number of pixels.
    """
    try:
        selector_map = await browser.get_selector_map()
        if index not in selector_map:
            msg = f'❌ Element with index {index} not found in selector map.'
            logger.warning(msg)
            return ActionResult(error=msg)

        dom_element = selector_map[index]
        page = await browser.get_current_page()

        await page.evaluate(
            """(args) => {
                const [xpath, amount] = args;
                const el = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (el) {
                    el.scrollBy({ top: amount, behavior: 'smooth' });
                } else {
                    throw new Error('Element not found for scrolling');
                }
            }""",
            [dom_element.xpath, pixels]
        )

        msg = f'🧭 Scrolled element at index {index} down by {pixels}px'
        logger.info(msg)
        return ActionResult(extracted_content=msg, include_in_memory=True)

    except Exception as e:
        error_msg = f'Error scrolling element at index {index}: {str(e)}'
        logger.error(error_msg)
        return ActionResult(error=error_msg, include_in_memory=True)

#@controller.action('Ask user for information about acronyms meaning, inputs, or points in the specification that were not clear ')
#def ask_human(question: str) -> ActionResult:
#    answer = input(f'\n{question}\nInput: ')
#    return ActionResult(extracted_content=answer)
   
@controller.action(
    description='Scroll up a specific element by a number of pixels using its index in the selector map.',
)
async def scroll_up_element(pixels: int, index: int, browser: BrowserContext) -> ActionResult:
    """
    Scrolls a DOM element (by index from selector_map) vertically *up* by a given number of pixels.
    """
    try:
        selector_map = await browser.get_selector_map()
        if index not in selector_map:
            msg = f'❌ Element with index {index} not found in selector map.'
            logger.warning(msg)
            return ActionResult(error=msg)

        dom_element = selector_map[index]
        page = await browser.get_current_page()

        await page.evaluate(
            """(args) => {
                const [xpath, amount] = args;
                const el = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue;
                if (el) {
                    el.scrollBy({ top: -amount, behavior: 'smooth' });
                } else {
                    throw new Error('Element not found for scrolling');
                }
            }""",
            [dom_element.xpath, pixels]
        )

        msg = f'🧭 Scrolled element at index {index} *up* by {pixels}px'
        logger.info(msg)
        return ActionResult(extracted_content=msg, include_in_memory=True)

    except Exception as e:
        error_msg = f'Error scrolling element at index {index}: {str(e)}'
        logger.error(error_msg)
        return ActionResult(error=error_msg, include_in_memory=True)
    
