"""
工作流模块

``base`` 提供可复用的图生命周期与通用节点，具体工作流只声明差异与连线。
"""
from .base import (
    ACCEPTED,
    REJECTED,
    BaseWorkflow,
    EvaluatorSpec,
    GeneratorSpec,
    LlmWorkflow,
    ReferenceSpec,
    ReviewSpec,
    SaveSpec,
    Section,
)
from .generate_npc_workflow import MODEL_PROGRESS_EVENT, GenerateNpcWorkflow
from .state import NpcState, initial_state

__all__ = [
    "BaseWorkflow",
    "LlmWorkflow",
    "Section",
    "ReferenceSpec",
    "GeneratorSpec",
    "EvaluatorSpec",
    "ReviewSpec",
    "SaveSpec",
    "ACCEPTED",
    "REJECTED",
    "NpcState",
    "initial_state",
    "GenerateNpcWorkflow",
    "MODEL_PROGRESS_EVENT",
]
