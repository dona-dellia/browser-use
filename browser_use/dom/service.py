"""
DOM service for extracting and processing DOM elements.
"""

import asyncio
import json
import logging
import os
from typing import Dict, List, Optional, Set, Tuple, Any, TypeVar, cast

# Selenium imports
from selenium import webdriver
from selenium.webdriver.remote.webelement import WebElement

from browser_use.dom.views import DOMBaseNode, DOMElementNode, DOMTextNode, SelectorMap

logger = logging.getLogger(__name__)

# Generic type for the context
T = TypeVar('T')

class DomService:
	"""Service for extracting and processing DOM elements"""

	def __init__(self):
		script_dir = os.path.dirname(os.path.abspath(__file__))
		with open(os.path.join(script_dir, "buildDomTree.js"), "r") as f:
			self.build_dom_tree_script = f.read()

	async def extract_dom_tree(
		self, 
		browser_context: Any, 
		viewport_expansion: int = 500
	) -> DOMElementNode:
		"""
		Extract the DOM tree from the current page.
		
		Args:
			browser_context: The browser context
			viewport_expansion: How much to expand the viewport for element extraction
								(-1 for all elements, 0 for only viewport elements)
		
		Returns:
			The DOM tree as a DOMElementNode
		"""
		driver = await browser_context.get_current_driver()
		
		# Execute the JavaScript to build the DOM tree
		result = driver.execute_script(
			self.build_dom_tree_script + 
			f"\nreturn buildDOMTree({viewport_expansion});"
		)
		
		# Parse the DOM tree from the result
		return self._parse_dom_tree(result)

	def _parse_dom_tree(self, dom_data: Dict[str, Any]) -> DOMElementNode:
		"""
		Parse the DOM tree from the JavaScript result.
		
		Args:
			dom_data: The DOM tree data from JavaScript
		
		Returns:
			The parsed DOM tree
		"""
		# Create root element
		root = DOMElementNode(
			tag_name=dom_data.get('tagName', 'root'),
			xpath=dom_data.get('xpath', ''),
			is_visible=dom_data.get('isVisible', True),
			attributes=dom_data.get('attributes', {}),
			parent=None,
			children=[],
			highlight_index=dom_data.get('highlightIndex'),
			is_interactive=dom_data.get('isInteractive', False),
			is_top_element=dom_data.get('isTopElement', False),
			shadow_root=dom_data.get('shadowRoot', False),
		)
		
		# Process children recursively
		children = []
		if 'children' in dom_data and isinstance(dom_data['children'], list):
			for child_data in dom_data['children']:
				# Handle text nodes
				if child_data.get('type') == 'TEXT_NODE':
					child = DOMTextNode(
						text=child_data.get('text', ''),
						is_visible=child_data.get('isVisible', True),
						parent=root
					)
					children.append(child)
				else:
					# Handle element nodes
					child = self._parse_dom_tree(child_data)
					child.parent = root
					children.append(child)
				
		root.children = children
		return root

	async def get_selector_map(self, browser_context: Any) -> SelectorMap:
		"""
		Get a map of element indices to DOM elements.
		
		Args:
			browser_context: The browser context
		
		Returns:
			A mapping of element indices to DOM elements
		"""
		element_tree = await self.extract_dom_tree(browser_context)
		return self._build_selector_map(element_tree)
		
	def _build_selector_map(self, root: DOMElementNode) -> SelectorMap:
		"""
		Build a mapping of highlight indices to DOM elements.
		
		Args:
			root: The root DOM element
		
		Returns:
			A mapping of highlight indices to DOM elements
		"""
		selector_map: SelectorMap = {}
		
		def traverse(node: DOMBaseNode):
			if isinstance(node, DOMElementNode) and node.highlight_index is not None:
				selector_map[node.highlight_index] = node
				
			if isinstance(node, DOMElementNode):
				for child in node.children:
					traverse(child)
				
		traverse(root)
		return selector_map
