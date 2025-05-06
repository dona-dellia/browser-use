
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


driver.execute_script("window.open('https://prism-cm-adapter-ge4.pnp4.pcf.dell.com/home', '_blank');")
driver.switch_to.window(driver.window_handles[-1])


driver.get('https://prism-cm-adapter-ge4.pnp4.pcf.dell.com/home')

element_to_input = driver.find_element(By.XPATH, 'html/body/div/div/div[2]/div/div/div/div/form/div[2]/input')
element_to_input.send_keys("")


element_to_input = driver.find_element(By.XPATH, 'html/body/div/div/div[2]/div/div/div/div/form/div[3]/div/div/input')
element_to_input.send_keys("")


element_to_click = driver.find_element(By.XPATH, 'html/body/div/div/div[2]/div/div/div/div/form/div[4]/a')
element_to_click.click()


element_to_click = driver.find_element(By.XPATH, 'html/body/app-root/app-prism-header/div/div[2]/nav/section/ul/li[2]/a')
element_to_click.click()


element_to_click = driver.find_element(By.XPATH, 'html/body/app-root/app-prism-header/div/div[2]/div/app-coparent/app-cohome/div/form/div/div[2]/div/div[3]/mat-form-field/div/div[2]/div/label')
element_to_click.click()

