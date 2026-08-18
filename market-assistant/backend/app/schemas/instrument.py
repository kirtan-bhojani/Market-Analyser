from typing import Literal

from pydantic import BaseModel, ConfigDict

AssetClass = Literal["crypto", "equity"]


class InstrumentIn(BaseModel):
    symbol: str
    asset_class: AssetClass
    exchange: str


class InstrumentPatch(BaseModel):
    active: bool | None = None


class InstrumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    asset_class: AssetClass
    exchange: str
    active: bool
    delayed: bool
    delay_minutes: int
