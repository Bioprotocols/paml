"""
The IntervalConstraint class defines the functions corresponding to the dynamically generated labop class IntervalConstraint
"""

import uml.inner as inner
from uml.constraint import Constraint


class IntervalConstraint(inner.IntervalConstraint, Constraint):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
