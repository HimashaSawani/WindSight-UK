import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_cutoff_and_cors_are_loaded_as_validated_settings() -> None:
    settings = Settings(
        decision_cutoff_local_time="11:30:00",
        frontend_origins="https://dashboard.example,http://localhost:5173",
    )

    assert settings.decision_cutoff_local_time.isoformat() == "11:30:00"
    assert settings.cors_origins == [
        "https://dashboard.example",
        "http://localhost:5173",
    ]


def test_invalid_decision_cutoff_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(decision_cutoff_local_time="25:99:00")
