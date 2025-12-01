from typing import Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")
    RATE_LIMITING_ENABLE: bool = False
    RATE_LIMITING_FREQUENCY: str = "2/3seconds"

    # National team competition expected tournament sizes
    # Can be overridden via environment variables:
    # TOURNAMENT_SIZE_FIWC=48, TOURNAMENT_SIZE_EURO=24, etc.
    # Format: TOURNAMENT_SIZE_{COMPETITION_ID}=<number>
    TOURNAMENT_SIZE_FIWC: Optional[int] = Field(default=32, description="World Cup expected participants")
    TOURNAMENT_SIZE_EURO: Optional[int] = Field(default=24, description="UEFA Euro expected participants")
    TOURNAMENT_SIZE_COPA: Optional[int] = Field(default=12, description="Copa America expected participants")
    TOURNAMENT_SIZE_AFAC: Optional[int] = Field(default=24, description="AFC Asian Cup expected participants")
    TOURNAMENT_SIZE_GOCU: Optional[int] = Field(default=16, description="Gold Cup expected participants")
    TOURNAMENT_SIZE_AFCN: Optional[int] = Field(default=24, description="Africa Cup of Nations expected participants")

    @field_validator(
        "TOURNAMENT_SIZE_FIWC",
        "TOURNAMENT_SIZE_EURO",
        "TOURNAMENT_SIZE_COPA",
        "TOURNAMENT_SIZE_AFAC",
        "TOURNAMENT_SIZE_GOCU",
        "TOURNAMENT_SIZE_AFCN",
    )
    @classmethod
    def validate_tournament_size(cls, v: Optional[int]) -> Optional[int]:
        """Validate tournament size is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("Tournament size must be a positive integer")
        return v

    def get_tournament_size(self, competition_id: str) -> Optional[int]:
        """
        Get expected tournament size for a competition ID.

        Args:
            competition_id: The competition ID (e.g., "FIWC", "EURO")

        Returns:
            Optional[int]: The expected tournament size, or None if not configured
        """
        size_map = {
            "FIWC": self.TOURNAMENT_SIZE_FIWC,
            "EURO": self.TOURNAMENT_SIZE_EURO,
            "COPA": self.TOURNAMENT_SIZE_COPA,
            "AFAC": self.TOURNAMENT_SIZE_AFAC,
            "GOCU": self.TOURNAMENT_SIZE_GOCU,
            "AFCN": self.TOURNAMENT_SIZE_AFCN,
        }
        return size_map.get(competition_id)


settings = Settings()
