"""Compatibility exports for existing ``core`` imports."""

from simon.intents import Intent, RouteResult
from simon.nlu.natural_language_router import NaturalLanguageRouter
from simon.nlu.semantic_router import SemanticIntentRouter

__all__ = ["Intent", "NaturalLanguageRouter", "RouteResult", "SemanticIntentRouter"]
