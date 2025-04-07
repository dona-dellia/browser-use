# Migration Plan: Playwright to Selenium

## Overview
This document outlines the steps to migrate the browser-use project from Playwright to Selenium.

## Key Components to Modify

### 1. Core Browser Classes
- `browser_use/browser/browser.py`: Replace Playwright browser initialization with Selenium WebDriver
- `browser_use/browser/context.py`: Replace Playwright BrowserContext with Selenium equivalent functionality
- `browser_use/browser/views.py`: Update browser state models to align with Selenium

### 2. DOM Handling
- `browser_use/dom/service.py`: Update DOM extraction to use Selenium's methods
- `browser_use/dom/buildDomTree.js`: Modify or replace with Selenium-compatible DOM extraction

### 3. Controller Actions
- `browser_use/controller/service.py`: Update action implementations to use Selenium methods
- Modify controller functions for clicking, navigation, etc.

### 4. Dependencies
- Replace Playwright dependencies with Selenium in setup/requirements

## Implementation Strategy

### Phase 1: Setup Selenium Core
1. Create Selenium equivalents of Browser and BrowserContext classes
2. Implement basic browser control (open, close, navigation)

### Phase 2: DOM Interaction
1. Implement element selection and interaction
2. Update DOM tree extraction to work with Selenium

### Phase 3: Controller Functions
1. Update all controller actions to use Selenium methods
2. Ensure compatibility with existing agent code

### Phase 4: Testing
1. Test basic browser operations
2. Test complex scenarios with the agent

## Selenium vs Playwright Mapping

| Playwright Concept | Selenium Equivalent |
|-------------------|---------------------|
| Browser | WebDriver |
| BrowserContext | WebDriver (with options) |
| Page | WebDriver |
| Locator | WebElement/By |
| ElementHandle | WebElement |
| async_playwright().start() | webdriver.Chrome()/Firefox()/etc. |
| page.goto() | driver.get() |
| page.click() | element.click() |
| page.fill() | element.send_keys() |
| page.wait_for_load_state() | WebDriverWait |
| page.evaluate() | driver.execute_script() |

## Implementation Details

### Browser Configuration
Selenium requires different configuration parameters:
- Replace Playwright's headless configuration
- Handle proxy settings differently
- WebDriver path management

### DOM Handling
Selenium has a different approach to DOM:
- Need to use execute_script() for complex DOM operations
- Different element selection mechanisms
- No built-in shadow DOM support (requires custom handling)

### Actions
Many actions need to be reimplemented:
- Scrolling (using JavaScript execution)
- File uploads
- Keyboard shortcuts
- Tab management

## Timeline
1. Core Browser functionality: 2-3 days
2. DOM handling: 2-3 days
3. Controller actions: 3-4 days
4. Testing and bug fixing: 2-3 days

Total estimated time: 9-13 days 