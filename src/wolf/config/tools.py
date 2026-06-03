"""
Baseline tools for config handling
"""
from collections import UserDict
from jinja2 import Environment, FileSystemLoader, load
from pathlib import Path
from typing import Any, Dict
import yaml

class YAMLConfig(UserDict):
    """
    A base yaml config
    """
    def read(self, yaml_string: str) -> Dict[Any, Any]:
        """
        Read a yaml config to dict
        """
        return yaml.safe_load(yaml_string)

    def dump(self, data, path: Path | None = None) -> None:
        """
        Dump the config
        """
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, encoding='utf-8')

class Jinja2:
    """
    placeholder for Jinja2 template handling
    """
    def __init__(self, path: Path | None = None) -> None:
        self.loader = FileSystemLoader
        self.env = Environment(loader=self.loader)
        self.path = path

    def load(self) -> str | None:
        """
        placeholder for loading a Jinja2 template
        """
        template = self.env.get_template(self.path)
        return template

    def dump(self) -> str | None:
        """
        placeholder for dumping a Jinja2 template
        """
        template = load()
        rendered = template.render()
        return rendered
