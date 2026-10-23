"""Request model for POST /predict (twelve flat fields, same as training)."""

from pydantic import BaseModel, ConfigDict, Field


class PredictRequest(BaseModel):
    # strict: no coercion of "3" to 3; extra: any unknown field (cnt, casual,
    # registered, typos) is rejected with 422.
    model_config = ConfigDict(strict=True, extra="forbid")

    season: int = Field(ge=1, le=4)
    yr: int = Field(ge=0, le=1)
    mnth: int = Field(ge=1, le=12)
    hr: int = Field(ge=0, le=23)
    holiday: int = Field(ge=0, le=1)
    weekday: int = Field(ge=0, le=6)
    workingday: int = Field(ge=0, le=1)
    weathersit: int = Field(ge=1, le=4)
    temp: float = Field(ge=0, le=1, allow_inf_nan=False)
    atemp: float = Field(ge=0, le=1, allow_inf_nan=False)
    hum: float = Field(ge=0, le=1, allow_inf_nan=False)
    windspeed: float = Field(ge=0, le=1, allow_inf_nan=False)