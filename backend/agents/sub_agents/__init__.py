#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sub-agents Module

Sub-agents are specialized assistants that handle complex,
multi-step workflows under the direction of parent agents.

Sub-agents included:
- SupplierResearchSubAgent: Multi-source supplier research
- ProductLaunchSubAgent: Product launch workflow coordination
"""

from backend.agents.sub_agents.base_sub_agent import BaseSubAgent
from backend.agents.sub_agents.supplier_research_sub_agent import SupplierResearchSubAgent
from backend.agents.sub_agents.product_launch_sub_agent import ProductLaunchSubAgent

__all__ = [
    "BaseSubAgent",
    "SupplierResearchSubAgent",
    "ProductLaunchSubAgent",
]

