import logging
from importlib import resources
from typing import Any, List, Optional

from selenium.webdriver.remote.webdriver import WebDriver

from browser_use.dom.history_tree_processor.view import Coordinates
from browser_use.dom.views import (
	CoordinateSet,
	DOMBaseNode,
	DOMElementNode,
	DOMState,
	DOMTextNode,
	SelectorMap,
	ViewportInfo,
)
from browser_use.dom.accessibility import parse_accessibility_tree, AccessibilityTree

logger = logging.getLogger(__name__)

class DomService:
	def __init__(self, driver: WebDriver):
		self.driver = driver
		self.xpath_cache = {}

	def _map_node_to_highlight_index(self, node, node_id, highlight_map):
		has_attrs = "attributes" in node

		if has_attrs:
			attrs: List[str] = node["attributes"]
			is_highlighted_element = "browser-user-highlight-id" in attrs

			if is_highlighted_element:
				highlight_index = int(next(attr for attr in attrs if attr.startswith("browser-user-highlight-") and attr != "browser-user-highlight-id").split("-")[-1])
				highlight_map[node_id] = highlight_index
		else:
			if "parentId" not in node: return
			parent = self.driver.execute_cdp_cmd("DOM.describeNode", {
            	"backendNodeId": int(node["parentId"])
        	})["node"]
			self._map_node_to_highlight_index(parent, node_id, highlight_map)

	def _filter_nodes(self, a11y_tree):
		highlight_map = {}

		def check_and_add_highlight(node_id: int, attrs: list):
			if "browser-user-highlight-id" in attrs:
				highlight_index = int(next(
        	        attr for attr in attrs 
        	         if attr.startswith("browser-user-highlight-") and attr != "browser-user-highlight-id").split("-")[-1])
				highlight_map[node_id] = highlight_index

		for node in a11y_tree:
			if "backendDOMNodeId" not in node:
				continue

			node_id = node["backendDOMNodeId"]
			node_data = self.driver.execute_cdp_cmd("DOM.describeNode", {
	            "backendNodeId": node_id
	        })["node"]
			
			if "attributes" in node_data:
				check_and_add_highlight(node_id, node_data["attributes"])
				continue
			
			if "parentId" not in node:
				continue
			
			parent_data = self.driver.execute_cdp_cmd("DOM.describeNode", {
	            "backendNodeId": int(node["parentId"])
	        })["node"]
			
			if "attributes" in parent_data:
				check_and_add_highlight(node_id, parent_data["attributes"])
				
		return highlight_map


	def _get_accessibility_tree_info(self) -> tuple[str, dict[str, Any]]:
		"""
		Extrai a árvore de acessibilidade usando o Chrome DevTools Protocol via driver.execute_cdp_cmd.
		"""
		driver = self.driver
		try:
			tree_data = driver.execute_cdp_cmd("Accessibility.getFullAXTree", {})
			accessibility_tree: AccessibilityTree = tree_data.get("nodes", [])
			highlight_map = self._filter_nodes(accessibility_tree)
			tree_str, _ = parse_accessibility_tree(accessibility_tree, highlight_map)
			return accessibility_tree, tree_str, highlight_map
		except Exception as e:
			logger.error(f"[Accessibility] Erro ao capturar árvore de acessibilidade: {e}")
			return "", {}
	
	def _highlight_elements(self, nodes, highlight_map, selector_map):
		paths = []
		for node in nodes:
			if "backendDOMNodeId" not in node: continue
			node_id = node["backendDOMNodeId"]
			if node_id not in highlight_map: continue
			node_highlight_index = highlight_map[node_id]
			x_path = selector_map[node_highlight_index].xpath
			paths.append({
				"path": x_path,
				"index": node_highlight_index
			})

		js_code = resources.read_text('browser_use.dom', 'highlightElements.js')
		args_str = f"{{ paths: {paths} }}"
		self.driver.execute_script(f"({js_code})({args_str})")

	# region - Clickable elements
	async def get_clickable_elements(
		self,
		highlight_elements: bool = True,
		focus_element: int = -1,
		viewport_expansion: int = 0,
	) -> DOMState:
		element_tree = await self._build_dom_tree(highlight_elements, focus_element, viewport_expansion)
		selector_map = self._create_selector_map(element_tree)
		a11y_tree, tree_str, highlight_map = self._get_accessibility_tree_info()
		self._highlight_elements(a11y_tree, highlight_map, selector_map)

		return DOMState(element_tree=None, selector_map=selector_map, a11y_tree=tree_str)

	async def _build_dom_tree(
		self,
		highlight_elements: bool,
		focus_element: int,
		viewport_expansion: int,
	) -> DOMElementNode:
		js_code = resources.read_text('browser_use.dom', 'buildDomTree.js')

		# Convert args to JavaScript format
		args_str = f"{{ doHighlightElements: {str(highlight_elements).lower()}, focusHighlightIndex: {focus_element}, viewportExpansion: {viewport_expansion} }}"
		
		# Execute JavaScript in Selenium
		eval_page = self.driver.execute_script(f"return ({js_code})({args_str})")
		
		html_to_dict = self._parse_node(eval_page)

		if html_to_dict is None or not isinstance(html_to_dict, DOMElementNode):
			raise ValueError('Failed to parse HTML to dictionary')

		return html_to_dict

	def _create_selector_map(self, element_tree: DOMElementNode) -> SelectorMap:
		selector_map = {}

		def process_node(node: DOMBaseNode):
			if isinstance(node, DOMElementNode):
				if node.highlight_index is not None:
					selector_map[node.highlight_index] = node

				for child in node.children:
					process_node(child)

		process_node(element_tree)
		return selector_map

	def _parse_node(
		self,
		node_data: dict,
		parent: Optional[DOMElementNode] = None,
	) -> Optional[DOMBaseNode]:
		if not node_data:
			return None

		if node_data.get('type') == 'TEXT_NODE':
			text_node = DOMTextNode(
				text=node_data['text'],
				is_visible=node_data['isVisible'],
				parent=parent
			)
			return text_node

		tag_name = node_data['tagName']

		# Parse coordinates if they exist
		viewport_coordinates = None
		page_coordinates = None
		viewport_info = None

		if 'viewportCoordinates' in node_data:
			viewport_coordinates = CoordinateSet(
				top_left=Coordinates(**node_data['viewportCoordinates']['topLeft']),
				top_right=Coordinates(**node_data['viewportCoordinates']['topRight']),
				bottom_left=Coordinates(**node_data['viewportCoordinates']['bottomLeft']),
				bottom_right=Coordinates(**node_data['viewportCoordinates']['bottomRight']),
				center=Coordinates(**node_data['viewportCoordinates']['center']),
				width=node_data['viewportCoordinates']['width'],
				height=node_data['viewportCoordinates']['height'],
			)

		if 'pageCoordinates' in node_data:
			page_coordinates = CoordinateSet(
				top_left=Coordinates(**node_data['pageCoordinates']['topLeft']),
				top_right=Coordinates(**node_data['pageCoordinates']['topRight']),
				bottom_left=Coordinates(**node_data['pageCoordinates']['bottomLeft']),
				bottom_right=Coordinates(**node_data['pageCoordinates']['bottomRight']),
				center=Coordinates(**node_data['pageCoordinates']['center']),
				width=node_data['pageCoordinates']['width'],
				height=node_data['pageCoordinates']['height'],
			)

		if 'viewport' in node_data:
			viewport_info = ViewportInfo(
				scroll_x=node_data['viewport']['scrollX'],
				scroll_y=node_data['viewport']['scrollY'],
				width=node_data['viewport']['width'],
				height=node_data['viewport']['height'],
			)

		element_node = DOMElementNode(
			tag_name=tag_name,
			xpath=node_data['xpath'],
			attributes=node_data.get('attributes', {}),
			children=[],  # Initialize empty, will fill later
			is_visible=node_data.get('isVisible', False),
			is_interactive=node_data.get('isInteractive', False),
			is_top_element=node_data.get('isTopElement', False),
			highlight_index=node_data.get('highlightIndex'),
			shadow_root=node_data.get('shadowRoot', False),
			parent=parent,
			viewport_coordinates=viewport_coordinates,
			page_coordinates=page_coordinates,
			viewport_info=viewport_info,
		)

		children: list[DOMBaseNode] = []
		for child in node_data.get('children', []):
			if child is not None:
				child_node = self._parse_node(child, parent=element_node)
				if child_node is not None:
					children.append(child_node)

		element_node.children = children

		return element_node

	# endregion
