from typing import Optional

from playwright.sync_api import ViewportSize

initial_selenium_code = """
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
import time
driver = webdriver.Chrome()
driver.implicitly_wait(10)
"""

def go_to(url: str) -> str:
    return f"""\ndriver.get('{url}')"""

def back()-> str:
    return f"""\ndriver.back()"""

def sleep(seconds: int)-> str:
    return f"""time.sleep('{seconds}')"""

def wait_to_element(css_element: str, timeout: int)-> str:
    selenium_code = f""" element = WebDriverWait(driver, {timeout} / 1000).until(
        EC.visibility_of_element_located((By.CSS_SELECTOR, "{css_element}"))
        """
    return selenium_code

def click_by_selector(css_selector:str)-> str:
    selenium_code = f"""
element_to_click = driver.find_element(By.CSS_SELECTOR, '{css_selector}')
element_to_click.click()
"""
    return selenium_code

def click_by_xpath(xpath:str)-> str:
    selenium_code = f"""
element_to_click = driver.find_element(By.XPATH, '{xpath}')
element_to_click.click()
"""
    return selenium_code

def click_by_text(text:str)-> str:
    selenium_code = f"""
element = driver.find_element(By.XPATH, "//*[contains(text(), '{text}')]")
driver.execute_script("arguments[0].scrollIntoView({{block: 'center'}});", element)
element.click()
"""
    return selenium_code


def click_by_selector_selector_js(css_selector: str)-> str:
    selenium_code = f"""
element_to_click = driver.find_element(By.CSS_SELECTOR, '{css_selector}')
element_to_click.click()
"""
    return selenium_code

def click_by_selector_xpath_js(xpath: str)-> str:
    selenium_code = f"""
element_to_click = driver.find_element(By.XPATH, '{xpath}')
element_to_click.click()
"""
    return selenium_code

def click_by_text_js(text:str)-> str:
    selenium_code = f"""
element = driver.find_element(By.XPATH, "//*[contains(text(), '{text}')]")
driver.execute_script("arguments[0].click();", element)
"""
    return selenium_code

def input_txt(element_xpath: str, text: str) -> str:
    selenium_code = f"""
element_to_input = driver.find_element(By.XPATH, '{element_xpath}')
element_to_input.send_keys("{text}")
"""
    return selenium_code

def switch_to_tab(tab_id: int) -> str:
    selenium_code = f"""\ndriver.switch_to.window(driver.window_handles[{tab_id}])"""
    return selenium_code

def open_tab(url:str) -> str:
    selenium_code = f"""
driver.execute_script("window.open('{url}', '_blank');")
driver.switch_to.window(driver.window_handles[-1])
"""
    return selenium_code

def scroll_down(amount: Optional[int] = None, viewport: Optional[ViewportSize] = None) -> str:
    selenium_code = ""
    if viewport is not None:
        selenium_code += f"""\ndriver.set_window_size({viewport["width"]}, {viewport["height"]})"""

    if amount is not None:
        selenium_code += f"""\nActionChains(driver).scroll_by_amount(0, {amount}).perform()"""
    else:
        selenium_code += """\nwindow_height = driver.execute_script("return window.innerHeight;")
ActionChains(driver).scroll_by_amount(0, window_height).perform()"""

    return selenium_code

def scroll_up(amount: Optional[int] = None, viewport: Optional[ViewportSize] = None):
    selenium_code = ""
    if viewport is not None:
        selenium_code += f"""\ndriver.set_window_size({viewport["width"]}, {viewport["height"]})"""

    if amount is not None:
        selenium_code += f"""\nActionChains(driver).scroll_by_amount(0, -{amount}).perform()"""
    else:
        selenium_code += """\nwindow_height = driver.execute_script("return window.innerHeight;")
ActionChains(driver).scroll_by_amount(0, -window_height).perform()"""

    return selenium_code

def send_keys(keys:str) -> str:
    key_mapping = {
        'Enter': 'Keys.ENTER',
        'Backspace': 'Keys.BACKSPACE',
        'Tab': 'Keys.TAB',
        'Delete': 'Keys.DELETE',
        'PageDown': 'Keys.PAGE_DOWN',
        'PageUp': 'Keys.PAGE_UP',
        'ArrowDown': 'Keys.ARROW_DOWN',
        'ArrowUp': 'Keys.ARROW_UP',
        'ArrowLeft': 'Keys.ARROW_LEFT',
        'ArrowRight': 'Keys.ARROW_RIGHT',
        'Escape': 'Keys.ESCAPE',
        'Control': 'Keys.CONTROL',
        'Shift': 'Keys.SHIFT',
        'Alt': 'Keys.ALT',
    }

    selenium_code = """
# Check if any interactive element is focused and only click body if needed
active_element = driver.execute_script(\"\"\"
    const active = document.activeElement;
    const isInteractive = active.tagName !== 'BODY' 
                         && active.tagName !== 'HTML' 
                         && active !== document.body;
    return isInteractive;
\"\"\")
if not active_element:
    main_page = driver.find_element(By.TAG_NAME, 'body')
    main_page.click()
"""

    # Verifica se é um atalho (contém +)
    if '+' in keys:
        keys_spl = keys.split('+')
        modifiers = keys_spl[:-1]  # todas as teclas exceto a última
        final_key = keys_spl[-1]   # última tecla

        selenium_code += f"""\nactions = ActionChains(driver)\n"""
        # Adiciona key_down para cada modificador
        for mod in modifiers:
            mod_key = key_mapping.get(mod, f"'{mod}'")
            selenium_code += f"actions.key_down({mod_key})\n"

        # Adiciona a tecla final
        final_selenium_key = key_mapping.get(final_key, f"'{final_key}'")
        selenium_code += f"actions.send_keys({final_selenium_key})\n"

        # Adiciona key_up para cada modificador (em ordem reversa)
        for mod in reversed(modifiers):
            mod_key = key_mapping.get(mod, f"'{mod}'")
            selenium_code += f"actions.key_up({mod_key})\n"

        selenium_code += "actions.perform()\n"

    else:
        # Tecla única (não é atalho)
        selenium_key = key_mapping.get(keys, f"'{keys}'")
        selenium_code += f"""
actions = ActionChains(driver)
actions.send_keys({selenium_key})
actions.perform()
"""

    return selenium_code

def scroll_to_text(text: str) -> str:
    selenium_code = f"""
element = driver.find_element(By.XPATH, f"//*[contains(text(), '{text}')]")
ActionChains(driver).scroll_to_element(element).perform()
time.sleep(0.5)  # Wait for scroll to complete
"""
    return selenium_code

def select_dropdown_option(dropdown_xpath: str, option: str) -> str:
    selenium_code = f"""
# First check if element is in an iframe
iframes = driver.find_elements(By.TAG_NAME, "iframe")
found_in_frame = False
# Check main frame first
try:
    dropdown = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, '{dropdown_xpath}'))
    )
    select = Select(dropdown)
    select.select_by_visible_text("{option}")
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
            select.select_by_visible_text("{option}")
            found_in_frame = True
            break
        except:
            driver.switch_to.default_content()
            continue
    # Switch back to default content after checking frames
    driver.switch_to.default_content()
if not found_in_frame:
    print(f"Could not select option '{option}' in any frame")
"""

    return selenium_code

def save_pdf(url: str) -> str:
    selenium_code = """# PDF da página atual
from selenium.webdriver.chrome.options import Options
import re

current_url = driver.current_url
short_url = re.sub(r'^https?://(?:www\.)?|/$', '', current_url)
slug = re.sub(r'[^a-zA-Z0-9]+', '-', short_url).strip('-').lower()
sanitized_filename = f'{slug}.pdf'

print_options = {'path': sanitized_filename, 'format': 'A4', 'background': False}
driver.execute_cdp_cmd('Page.printToPDF', print_options)
"""
    return selenium_code

def close_tab(page_id: int) -> str:
    selenium_code = f"""
window_handles = driver.window_handles
driver.switch_to.window(window_handles[{page_id}])
url = driver.current_url
driver.close()

if len(window_handles) > 1:
    driver.switch_to.window(window_handles[0])
"""
    return selenium_code

def save_html_to_file() -> str:

    selenium_code = """# Salvar HTML
import re
from datetime import datetime

html_content = driver.page_source
current_url = driver.current_url
short_url = re.sub(r'^https?://(?:www\.)?|/$', '', current_url)
slug = re.sub(r'[^a-zA-Z0-9]+', '-', short_url).strip('-').lower()[:64]
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
sanitized_filename = f'{slug}_{timestamp}.html'

with open(sanitized_filename, 'w', encoding='utf-8') as f:
    f.write(html_content)
"""
    return selenium_code

def drag_and_drop_elements(source_id: str, target_id: str) -> str:

    selenium_code = f"""
from selenium.webdriver.common.action_chains import ActionChains

source = driver.find_element(By.ID, '{source_id}')
target = driver.find_element(By.ID, '{target_id}')

ActionChains(driver).drag_and_drop(source, target).perform()"""
    return selenium_code

def drag_and_drop_coords(start_x: int, start_y: int, end_x: int, end_y: int) -> str:
    selenium_code = f"""
from selenium.webdriver.common.action_chains import ActionChains

actions = ActionChains(driver)
actions.move_by_offset({start_x}, {start_y})
actions.click_and_hold()
actions.move_by_offset({end_x - start_x}, {end_y - start_y})
actions.release()
actions.perform()"""
    return selenium_code