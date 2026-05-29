"""Simple tests"""
from typing import Any, Dict, List
from wolf.dag.engine import DAGBuilder

# fixtures
def _make_config(
    task_id: str,
    task_type: str = "run",
    parent: str | None = None,
    dependency: str | None = None,
    command: str = "echo hello",
) -> Dict[str, Any]:
    """Return a minimal task-config dict."""
    return {
        "id": task_id,
        "type": task_type,
        "parent": parent,
        "dependency": dependency,
        "command": command,
    }

SIMPLE_LINEAR: List[Dict[str, Any]] = [
    _make_config("a", command="echo a"),
    _make_config("b", parent="a", dependency="a", command="echo b"),
    _make_config("c", parent="b", dependency="b", command="echo c"),
]

class TestDAGBuilderConstruction:
    """DAGBuilder.__init__ must build a correct config_map."""
 
    def test_config_map_keys_match_ids(self) -> None:
        builder = DAGBuilder(SIMPLE_LINEAR)
        assert set(builder.config_map.keys()) == {"a", "b", "c"}
