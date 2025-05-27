import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver import Chrome, ChromeOptions
import time
from selenium.webdriver.chrome.service import Service


@pytest.fixture(scope="function")
def driver():
    options = ChromeOptions()
    options.add_argument("--window-size=1280,1024")
    options.add_argument('--ignore-certificate-errors')

    #options.add_argument("--headless=new")  # Pode tirar se quiser ver interações
    service = Service(ChromeDriverManager().install())
    driver = Chrome(service=service, options=options)
    driver.get("https://www.w3schools.com/html/html_tables.asp")  # Página com conteúdo scrollável
    yield driver
    driver.quit()


# def test_scroll_down_pass(driver):
#     initial_scroll = driver.execute_script("return window.scrollY")
#     ActionChains(driver).scroll_by_amount(0, 500).perform()
#     time.sleep(0.5)
#     final_scroll = driver.execute_script("return window.scrollY")
#     assert final_scroll > initial_scroll


# def test_scroll_down_fail(driver):
#     initial_scroll = driver.execute_script("return window.scrollY")
#     # Não rola nada
#     time.sleep(0.5)
#     final_scroll = driver.execute_script("return window.scrollY")
#     with pytest.raises(AssertionError):
#         assert final_scroll > initial_scroll


def test_scroll_up_pass(driver):
    driver.execute_script("window.scrollTo(0, 600);")  # Simula scroll prévio
    initial_scroll = driver.execute_script("return window.scrollY")
    ActionChains(driver).scroll_by_amount(0, -300).perform()
    time.sleep(0.5)
    final_scroll = driver.execute_script("return window.scrollY")
    assert final_scroll < initial_scroll


def test_scroll_up_fail(driver):
    driver.execute_script("window.scrollTo(0, 0);")  # Já está no topo
    initial_scroll = driver.execute_script("return window.scrollY")
    ActionChains(driver).scroll_by_amount(0, -300).perform()
    time.sleep(0.5)
    final_scroll = driver.execute_script("return window.scrollY")
    with pytest.raises(AssertionError):
        assert final_scroll < initial_scroll


# def test_scroll_to_text_pass(driver):
#     element = driver.find_element(By.XPATH, "//*[contains(text(), 'Island Trading')]")
#     ActionChains(driver).scroll_to_element(element).perform()
#     time.sleep(0.5)
#     in_viewport = driver.execute_script("""
#         const rect = arguments[0].getBoundingClientRect();
#         return (
#             rect.top >= 0 &&
#             rect.left >= 0 &&
#             rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
#             rect.right <= (window.innerWidth || document.documentElement.clientWidth)
#         );
#     """, element)
#     assert in_viewport


# def test_scroll_to_text_fail(driver):
#     with pytest.raises(AssertionError):
#         element = driver.find_element(By.TAG_NAME, "body")  # Já visível
#         ActionChains(driver).scroll_to_element(element).perform()
#         time.sleep(0.5)
#         in_viewport = driver.execute_script("""
#             const rect = arguments[0].getBoundingClientRect();
#             return (
#                 rect.top >= 0 &&
#                 rect.left >= 0 &&
#                 rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) &&
#                 rect.right <= (window.innerWidth || document.documentElement.clientWidth)
#             );
#         """, element)
#         assert not in_viewport  # força falha
