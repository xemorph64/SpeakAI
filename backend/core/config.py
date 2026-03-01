"""
SpeakAI — Backend Configuration

Centralised settings loaded from environment variables.
"""

import os
from dataclasses import dataclass, field
from typing import Set


@dataclass
class ServerConfig:
    host: str = "0.0.0.0"
    port: int = 8080
    cors_origins: Set[str] = field(default_factory=lambda: {
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
    })

    def __post_init__(self):
        self.host = os.getenv("HOST", self.host)
        self.port = int(os.getenv("PORT", str(self.port)))


@dataclass
class SDKConfig:
    stream_api_key: str = ""
    stream_api_secret: str = ""
    google_api_key: str = ""
    gemini_realtime_model: str = "gemini-2.5-flash-native-audio-preview-12-2025"

    def __post_init__(self):
        self.stream_api_key = os.getenv("STREAM_API_KEY", "")
        self.stream_api_secret = os.getenv("STREAM_API_SECRET", "")
        self.google_api_key = os.getenv("GOOGLE_API_KEY", "")
        self.gemini_realtime_model = os.getenv(
            "GEMINI_REALTIME_MODEL", self.gemini_realtime_model
        )
        # Bridge key names used by the Vision Agents SDK
        if self.stream_api_key and not os.getenv("API_KEY"):
            os.environ["API_KEY"] = self.stream_api_key
        if self.stream_api_secret and not os.getenv("API_SECRET"):
            os.environ["API_SECRET"] = self.stream_api_secret

    @property
    def has_all_keys(self) -> bool:
        return bool(self.stream_api_key and self.stream_api_secret and self.google_api_key)


server_cfg = ServerConfig()
sdk_cfg = SDKConfig()
