"""
Ollama Local LLM Client for InsightIQ.

Provides low-latency, secure communication with the locally running Ollama runtime
(default: Qwen 2.5 3B on http://localhost:11434).
Includes health checks, structured JSON response mode, and timeout protection.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_LLM_MODEL = os.getenv("LLM_MODEL", "qwen2.5:3b")


class OllamaClient:
    """Client for local Ollama LLM execution."""

    def __init__(self, base_url: str = OLLAMA_BASE_URL, default_model: str = DEFAULT_LLM_MODEL, timeout: int = 45):
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout

    def is_available(self) -> bool:
        """Checks if the local Ollama daemon is reachable."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=3)
            return resp.status_code == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """Lists all locally pulled models in Ollama."""
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return [m.get("name") for m in data.get("models", [])]
            return []
        except Exception as e:
            logger.warning(f"Failed to query Ollama models: {e}")
            return []

    def has_model(self, model_name: Optional[str] = None) -> bool:
        """Checks if a specific model or the default model is pulled."""
        target = model_name or self.default_model
        models = self.list_models()
        return any(target in m for m in models)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        format_json: bool = False,
    ) -> str:
        """
        Generates text completion from Ollama.
        """
        selected_model = model or self.default_model
        payload = {
            "model": selected_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt
        if format_json:
            payload["format"] = "json"

        try:
            resp = requests.post(f"{self.base_url}/api/generate", json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "").strip()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama generation request failed: {e}")
            raise RuntimeError(f"Ollama generation error: {e}") from e

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.1,
        format_json: bool = False,
    ) -> str:
        """
        Generates a chat response from Ollama.
        """
        selected_model = model or self.default_model
        payload = {
            "model": selected_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        if format_json:
            payload["format"] = "json"

        try:
            resp = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "").strip()
        except requests.exceptions.RequestException as e:
            logger.error(f"Ollama chat request failed: {e}")
            raise RuntimeError(f"Ollama chat error: {e}") from e
