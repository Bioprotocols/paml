"""
The InitialNode class defines the functions corresponding to the dynamically generated labop class InitialNode
"""

import uml.inner as inner
from uml.control_node import ControlNode


class InitialNode(inner.InitialNode, ControlNode):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def dot_attrs(self):
        return {
            "label": "",
            "shape": "circle",
            "style": "filled",
            "fillcolor": "black",
        }
