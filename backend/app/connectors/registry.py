"""Connector registry."""
from typing import Dict, Type
from app.connectors.base import ITSMConnector
from app.connectors.jira import JiraConnector

CONNECTOR_REGISTRY: Dict[str, Type[ITSMConnector]] = {
    "jira": JiraConnector,
}


def get_connector_class(tool: str) -> Type[ITSMConnector]:
    cls = CONNECTOR_REGISTRY.get(tool.lower())
    if not cls:
        raise ValueError(f"Unknown ITSM tool: {tool}. Registered: {list(CONNECTOR_REGISTRY)}")
    return cls
