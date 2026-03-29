"""
AI Prompts — Infrastructure Layer.

Prompts are infrastructure concerns because they:
- Contain LLM-specific formatting and instructions
- May vary by provider (Gemini vs OpenAI vs Claude)
- Are implementation details, not domain logic

The domain/application layer should not depend on prompt wording.
"""

from tacto.infrastructure.ai.prompts.level1_prompts import Level1Prompts

__all__ = ["Level1Prompts"]
