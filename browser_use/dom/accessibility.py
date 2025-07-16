from typing import Any
from browser_use.dom.views import AccessibilityTree, AccessibilityTreeNode

IGNORED_ACTREE_PROPERTIES = {"busy", "live", "atomic", "containerLive"}
HIGHLIGHT_ATTRS = {"browser-user-highlight-id", "playwright-highlight-id"}


def parse_accessibility_tree(accessibility_tree: AccessibilityTree, highlight_map: dict[int, int]) -> tuple[str, dict[str, Any]]:
    node_id_to_idx = {node["nodeId"]: idx for idx, node in enumerate(accessibility_tree)}
    obs_nodes_info = {}

    # === Passo 1: encontrar todos os highlights ===
    highlight_ids = set()

    for node in accessibility_tree:
        props = node.get("properties", [])
        custom = node.get("customAttributes", {})

        has_highlight_attr = any(attr in custom for attr in HIGHLIGHT_ATTRS)
        has_highlight_prop = any(p.get("name") in HIGHLIGHT_ATTRS for p in props)

        if has_highlight_attr or has_highlight_prop:
            highlight_ids.add(node["nodeId"])

    # === Passo 2: marcar todos os descendentes ===
    def mark_descendants(node_id: str):
        if node_id not in node_id_to_idx:
            return
        node = accessibility_tree[node_id_to_idx[node_id]]
        for child_id in node.get("childIds", []):
            if child_id not in highlight_ids:
                highlight_ids.add(child_id)
                mark_descendants(child_id)

    for node_id in list(highlight_ids):
        mark_descendants(node_id)

    # === Passo 3: DFS ignorando highlights ===
    def dfs(idx: int, depth: int) -> str:
        node = accessibility_tree[idx]
        indent = "\t" * depth
        tree_str = ""
        valid_node = True
        node_id = str(highlight_map[node["backendDOMNodeId"]]) if "backendDOMNodeId" in node and node["backendDOMNodeId"] in highlight_map else ""

        try:
            role = node["role"]["value"]
            name = node["name"]["value"]

            node_str = f"[{node_id}] {role} {repr(name)}"
            properties = []

            for prop in node.get("properties", []):
                try:
                    if prop["name"] in IGNORED_ACTREE_PROPERTIES:
                        continue
                    properties.append(f'{prop["name"]}: {prop["value"]["value"]}')
                except KeyError:
                    continue

            if properties:
                node_str += " " + " ".join(properties)

            if "customAttributes" in node:
                for attr, value in node["customAttributes"].items():
                    node_str += f" [{attr}={value}]"

            # Filtros de "irrelevância" visual
            if not name.strip():
                if not properties:
                    if role in {
                        "generic", "img", "list", "strong", "paragraph", "banner", "navigation",
                        "Section", "LabelText", "Legend", "listitem"
                    }:
                        valid_node = False
                elif role in {"listitem"}:
                    valid_node = False

            if valid_node:
                tree_str += f"{indent}{node_str}"
                obs_nodes_info[node["nodeId"]] = {
                    "backend_id": node.get("backendDOMNodeId"),
                    "union_bound": node.get("union_bound"),
                    "text": node_str,
                }

        except Exception:
            valid_node = False

        for child_node_id in node.get("childIds", []):
            if child_node_id not in node_id_to_idx:
                continue
            child_depth = depth + 1 if valid_node else depth
            child_str = dfs(node_id_to_idx[child_node_id], child_depth)
            if child_str.strip():
                if tree_str:
                    tree_str += "\n"
                tree_str += child_str

        return tree_str

    tree_str = dfs(0, 0) if accessibility_tree else ""
    return tree_str, obs_nodes_info
