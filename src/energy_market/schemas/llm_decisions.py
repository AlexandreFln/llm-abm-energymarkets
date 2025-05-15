from pydantic import BaseModel, Field
from typing import List, Optional

class EnergyOffer(BaseModel):
    """Schema for energy offer details."""
    seller_id: str = Field(description="ID of the selling agent")
    amount: float = Field(description="Amount of energy offered")
    price: float = Field(description="Price per unit")
    is_renewable: bool = Field(description="Whether the energy is from renewable sources")

class ConsumerDecision(BaseModel):
    """Schema for consumer LLM decisions."""
    best_offer: EnergyOffer | None = Field(description="The best energy offer available")
    best_score: float = Field(description="Score of the best offer (0-100)")

class ProsumerDecision(BaseModel):
    """Schema for prosumer LLM decisions."""
    sell_amount: float = Field(description="Amount of energy to sell")
    selling_price: float = Field(description="Price to offer energy at")
    use_storage: float = Field(description="Amount of stored energy to use")
    store_amount: float = Field(description="Amount of energy to store")
    consider_upgrade: bool = Field(description="Whether to consider a capacity upgrade")

class UtilityContract(BaseModel):
    """Schema for utility contract details."""
    utility_id: str = Field(description="ID of the producer")
    amount_supplied: float = Field(description="Amount of energy to buy")
    spot_price: Optional[float] = Field(description="Spot price of a unit of energy sold")

class ProducerDecision(BaseModel):
    """Schema for producer LLM decisions."""
    utility_contracts: List[UtilityContract] = Field(description="Contract filled with the utility")

class EnergyContract(BaseModel):
    """Schema for energy amounts."""
    producer_id: str = Field(description="ID of the producer")
    amount: float = Field(description="Amount of energy to buy")

class UtilityDecision(BaseModel):
    """Schema for utility LLM decisions."""
    selling_price: float = Field(description="Price to sell a unit of energy")
    producer_contracts: List[EnergyContract] = Field(description="Contracts signed with producers")


class RegulatorDecision(BaseModel):
    """Schema for regulator LLM decisions."""
    adjust_carbon_tax: float = Field(description="Percentage change in carbon tax (-10 to +10)")
    max_price_increase: float = Field(description="Maximum allowed price increase")
    enforce_renewable_quota: bool = Field(description="Whether to strictly enforce quotas")