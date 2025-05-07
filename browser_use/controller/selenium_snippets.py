from typing import Optional

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

def click(element_xpath: str)-> str:
    selenium_code = f"""
element_to_click = driver.find_element(By.XPATH, '{element_xpath}')
element_to_click.click()
"""
    return selenium_code


def input_txt(element_xpath: str, text: str, is_sensitive: bool) -> str:
    if is_sensitive:
        text_value = "Replace with your sensitive data"
        
    else:
        text_value = f'"{text}"'
    selenium_code = f"""
element_to_input = driver.find_element(By.XPATH, '{element_xpath}')
element_to_input.send_keys({text_value})
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

def sleep(seconds: int)-> str:
    return f"""time.sleep('{seconds}')"""

def scroll_down(amount: Optional[int] = None) -> str:
    selenium_code = ""
    if amount is not None:
        selenium_code += f"""\nActionChains(driver).scroll_by_amount(0, {amount}).perform()"""
    else:
        selenium_code += """\nwindow_height = driver.execute_script("return window.innerHeight;")
ActionChains(driver).scroll_by_amount(0, window_height).perform()"""

    return selenium_code

def scroll_up(amount: Optional[int] = None):
    selenium_code = ""
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