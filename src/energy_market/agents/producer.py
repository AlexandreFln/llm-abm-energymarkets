from typing import Dict, Any, Optional
import numpy as np

from src.energy_market.agents.base import EnergyMarketAgent
from src.energy_market.constants import PRODUCTION_TYPES

class EnergyProducerAgent(EnergyMarketAgent):
    """Energy producer agent that generates and sells energy to utilities."""
    
    def __init__(self,
                 unique_id: str,
                 model: Any,
                 persona: str,
                 production_type: str,
                 initial_resources: float = 10000.0,
                 max_production_capacity: float = 1000.0,
                 base_production_cost: float = 30.0,
                 fixed_production_costs: float = 300.0,
                 maintenance_cost_rate: float = 0.02,
                 upgrade_cost: float = 5000.0,
                 upgrade_capacity_increase: float = 200.0,
                 min_profit_margin: float = 0.15):
        """Initialize energy producer agent.
        
        Args:
            unique_id: Unique identifier for the agent
            model: The model instance the agent belongs to
            persona: The agent's personality/behavior type
            production_type: Type of energy production facility
            initial_resources: Starting monetary resources
            max_production_capacity: Maximum production capacity per step
            base_production_cost: Base cost per unit of energy produced
            fixed_production_costs: Fixed production costs per step
            maintenance_cost_rate: Maintenance cost as fraction of capacity
            upgrade_cost: Cost to upgrade production capacity
            upgrade_capacity_increase: Amount capacity increases per upgrade
            min_profit_margin: Minimum acceptable profit margin
        """
        super().__init__(unique_id, model, persona, initial_resources)
        
        if production_type not in PRODUCTION_TYPES:
            raise ValueError(
                f"Invalid production type. Must be one of: {PRODUCTION_TYPES}"
            )
            
        self.production_type = production_type
        self.max_production_capacity = max_production_capacity
        self.base_production_cost = base_production_cost
        self.fixed_production_costs = fixed_production_costs
        self.maintenance_cost_rate = maintenance_cost_rate
        self.upgrade_cost = upgrade_cost
        self.upgrade_capacity_increase = upgrade_capacity_increase
        self.min_profit_margin = min_profit_margin
        
        # Dynamic state variables
        self.current_production = max_production_capacity * 0.8  # Start at 80% of capacity
        self.current_price = base_production_cost * (1 + min_profit_margin * 2)
        self.utility_contracts: Dict[str, Dict[str, Any]] = {}
        
    def is_renewable(self) -> bool:
        """Check if the production type is renewable."""
        return self.production_type in ["solar", "wind", "hydro"]
        

    async def step_async(self) -> None:
        """Execute one step of the producer agent."""

        # Get LLM decision about production strategy
        # Properly format utility contracts for the LLM
        prompt_utility_contracts = {}
        for utility_id, contract in self.utility_contracts.items():
            if isinstance(contract, dict):
                # Extract the necessary information in a standardized format
                prompt_utility_contracts[utility_id] = {
                    'amount': contract.get('amount_contracted', 
                                          contract.get('amount', 0)),
                }
        
        decision = await self.llm_decision_maker.get_producer_decision_async(
            persona=self.persona,
            utility_contracts=prompt_utility_contracts,
            max_production_capacity=self.max_production_capacity,
            fixed_production_costs=self.fixed_production_costs,
            variable_production_costs=self.base_production_cost,
        )
        total_revenues = 0
        total_costs = 0
        self.current_production = 0

        agents_ids = self.model.get_agent_ids()
        # Filter out contracts with non-existent utilities
        decision.utility_contracts = [
            contract for contract in decision.utility_contracts 
            if contract.utility_id in agents_ids
        ]
        
        for utility_contract in decision.utility_contracts:
            amount_supplied = utility_contract.amount_supplied
            # Use base_production_cost as the default if spot_price is None
            spot_price = utility_contract.spot_price if utility_contract.spot_price is not None else self.current_price
            revenues = amount_supplied * spot_price
            costs = self.base_production_cost * amount_supplied + self.fixed_production_costs
            total_revenues += revenues
            total_costs += costs
            self.current_production += amount_supplied
            # Preserve existing values and add new ones
            if utility_contract.utility_id not in self.utility_contracts:
                self.utility_contracts[utility_contract.utility_id] = {}
                
            self.utility_contracts[utility_contract.utility_id].update({
                'amount_supplied': amount_supplied,
                'spot_price': spot_price,
                'revenues': revenues,
                'operational_costs': costs
            })
            
            utility = self.model.get_agent(utility_contract.utility_id)
            if utility is None:
                print(f"Utility {utility_contract.utility_id} not found. Skipping profit calculation.")
                continue
            if self.unique_id not in utility.producer_contracts:
                utility.producer_contracts[self.unique_id] = {}
            utility.producer_contracts[self.unique_id].update({
                'producer_id': self.unique_id,
                'amount_supplied': amount_supplied,
                'spot_price': spot_price,
            })
            utility_margin = utility.current_selling_price - spot_price
            utility.profit = utility_margin * amount_supplied
            utility.update_resources(utility.profit)
        # Only calculate mean price if there are valid spot prices
        if self.utility_contracts:
            decision_utilities = [u.utility_id for u in decision.utility_contracts]
            self.current_price = np.mean([c['spot_price'] for u_id, c in self.utility_contracts.items() if u_id in decision_utilities])
        self.profit = total_revenues - total_costs
        self.update_resources(self.profit)