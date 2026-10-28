# Gemini Tool Calling Skill — Agrimind Agentic

Guidelines for defining tools and LangChain agent integration with Gemini models:

## Tool Definition
- Tools must be defined using `@tool` decorator from `langchain_core.tools`.
- Each tool function must have clear docstrings explaining input arguments and return formats.
- Gemini function calling relies on typed parameters and docstrings for intent matching.

## Vision Diagnosis
- For vision tool (`tools/disease.py`), handle base64 or file upload bytes.
- Pass images to Gemini using `google-genai` SDK or `langchain-google-genai`.
