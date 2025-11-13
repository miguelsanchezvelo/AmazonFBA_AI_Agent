#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Base Sub-Agent Class

Sub-agents are specialized workers that handle complex, multi-step workflows
under the direction of parent agents. They have their own lifecycle but are
coordinated by their parent agent.

Key Differences from Agents:
- Sub-agents are instantiated by parent agents (not by orchestrator)
- Sub-agents have a parent reference and share parent's logger
- Sub-agents focus on a specific multi-step workflow
- Sub-agents return results to parent for integration

Example:
    >>> supplier_agent = SupplierAgent()
    >>> sub_agent = SupplierResearchSubAgent(parent_agent=supplier_agent)
    >>> result = await sub_agent.execute_workflow({...})
"""

from typing import Any, Dict, Optional, Type
from datetime import datetime
import logging

from backend.agents.base_agent import BaseAgent


class BaseSubAgent:
    """
    Base class for all sub-agents.
    
    Sub-agents handle complex multi-step workflows and are coordinated
    by their parent agent.
    
    Attributes:
        parent: Reference to parent agent
        name: Name of this sub-agent
        logger: Logger (inherited from parent)
    """
    
    def __init__(self, parent_agent: BaseAgent):
        """
        Initialize sub-agent.
        
        Args:
            parent_agent: Parent agent that created this sub-agent
        """
        self.parent = parent_agent
        self.name = self.__class__.__name__
        self.logger = parent_agent.logger
        self.created_at = datetime.now()
        
    async def execute_workflow(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the sub-agent's workflow.
        
        This method should implement the multi-step workflow that
        this sub-agent is responsible for.
        
        Args:
            task: Task definition with parameters
            
        Returns:
            Result dictionary with workflow output
            
        Raises:
            NotImplementedError: Subclasses must implement this method
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement execute_workflow()"
        )
    
    async def initialize(self) -> None:
        """
        Initialize sub-agent resources.
        
        Called before executing workflow. Can be overridden by subclasses
        to set up resources specific to this sub-agent.
        """
        self.logger.info(f"{self.name} initialized")
    
    async def cleanup(self) -> None:
        """
        Clean up sub-agent resources.
        
        Called after workflow completes. Can be overridden by subclasses
        to clean up resources.
        """
        self.logger.info(f"{self.name} cleanup completed")
    
    def log_step(self, step_num: int, step_name: str, details: Optional[str] = None) -> None:
        """
        Log a workflow step.
        
        Args:
            step_num: Step number
            step_name: Name of step
            details: Optional details about the step
        """
        msg = f"[{self.name}] Step {step_num}: {step_name}"
        if details:
            msg += f" - {details}"
        self.logger.info(msg)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert sub-agent info to dictionary."""
        return {
            "name": self.name,
            "parent": self.parent.name,
            "created_at": self.created_at.isoformat(),
            "status": "active"
        }

