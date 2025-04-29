from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field

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

class ProducerDecision(BaseModel):
    """Schema for producer LLM decisions."""
    production_level: float = Field(description="Target production level")
    price: float = Field(description="Selling price per unit")
    accept_contracts: bool = Field(description="Whether to accept new contracts")
    min_contract_duration: int = Field(description="Minimum contract duration to accept")
    consider_upgrade: bool = Field(description="Whether to consider a capacity upgrade")

class UtilityDecision(BaseModel):
    """Schema for utility LLM decisions."""
    target_contracts: int = Field(description="Number of new contracts to seek")
    max_purchase_price: float = Field(description="Maximum price to pay for energy")
    selling_price: float = Field(description="Price to sell energy at")
    renewable_target: float = Field(description="Target percentage of renewable energy")
    storage_strategy: str = Field(description="'increase', 'decrease', or 'maintain'")

class RegulatorDecision(BaseModel):
    """Schema for regulator LLM decisions."""
    adjust_carbon_tax: float = Field(description="Percentage change in carbon tax (-10 to +10)")
    price_intervention: bool = Field(description="Whether to intervene in pricing")
    max_price_increase: float = Field(description="Maximum allowed price increase")
    enforce_renewable_quota: bool = Field(description="Whether to strictly enforce quotas")
    issue_warnings: List[str] = Field(description="List of warning types to issue") 