"""Inbound protocol contracts and presentation helpers.

CLI, future HTTP, and future MCP adapters translate requests and results here;
they do not own knowledge compilation or product-output rendering.
"""

from chew.interfaces.contracts import InterfaceProblem, InterfaceResponse

__all__ = ["InterfaceProblem", "InterfaceResponse"]
