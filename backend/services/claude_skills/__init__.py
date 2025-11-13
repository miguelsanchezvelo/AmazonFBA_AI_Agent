#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Claude Skills - Módulos especializados de razonamiento con Claude.

Este paquete contiene Skills especializadas que utilizan Claude
para tareas de razonamiento avanzado, análisis y generación de contenido.
"""

from backend.services.claude_skills.base_skill import BaseSkill, SkillResult
from backend.services.claude_skills.supplier_message_skill import SupplierMessageSkill
from backend.services.claude_skills.market_analysis_skill import MarketAnalysisSkill
from backend.services.claude_skills.supplier_evaluation_skill import SupplierEvaluationSkill
from backend.services.claude_skills.report_generation_skill import ReportGenerationSkill
from backend.services.claude_skills.pricing_strategy_skill import PricingStrategySkill
from backend.services.claude_skills.demand_forecasting_skill import DemandForecastingSkill
from backend.services.claude_skills.business_decision_skill import BusinessDecisionSkill

__all__ = [
    "BaseSkill",
    "SkillResult",
    "SupplierMessageSkill",
    "MarketAnalysisSkill",
    "SupplierEvaluationSkill",
    "ReportGenerationSkill",
    "PricingStrategySkill",
    "DemandForecastingSkill",
    "BusinessDecisionSkill",
]

