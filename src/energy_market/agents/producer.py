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
        self.maintenance_cost_rate = maintenance_cost_rate
        self.upgrade_cost = upgrade_cost
        self.upgrade_capacity_increase = upgrade_capacity_increase
        self.min_profit_margin = min_profit_margin
        
        # Dynamic state variables
        self.current_production = max_production_capacity * 0.8  # Start at 80% of capacity
        self.current_price = base_production_cost * (1 + min_profit_margin * 2)
        self.utility_contracts: Dict[str, Dict[str, Any]] = {}
        self.production_efficiency = 1.0
        self.min_contract_duration = 3
        
    def is_renewable(self) -> bool:
        """Check if the production type is renewable."""
        return self.production_type in ["solar", "wind", "hydro"]
        
    def negotiate_contract(self, 
                         utility_id: str, 
                         amount: float, 
                         duration: int) -> Dict[str, Any]:
        """Negotiate a contract with a utility.
        
        Args:
            utility_id: ID of the utility
            amount: Requested amount of energy per step
            duration: Contract duration in steps
            
        Returns:
            Dict containing contract terms
        """
        # Check if we can fulfill the contract
        available_capacity = self.max_production_capacity
        for contract in self.utility_contracts.values():
            available_capacity -= contract['amount']
            
        if amount > available_capacity:
            return {'accepted': False, 'reason': 'Insufficient capacity'}
            
        # Calculate contract price with volume discount
        volume_discount = min(0.1, amount / self.max_production_capacity * 0.2)
        contract_price = self.current_price * (1 - volume_discount)
        
        # Create contract terms
        contract = {
            'accepted': True,
            'utility_id': utility_id,
            'amount': amount,
            'price': contract_price,
            'duration': duration,
            'remaining_duration': duration,
            'is_renewable': self.is_renewable()
        }
        
        self.utility_contracts[utility_id] = contract
        return contract
        
    def manage_contracts(self) -> None:
        """Manage existing contracts and update their status."""
        expired_contracts = []
        
        for utility_id, contract in self.utility_contracts.items():
            if contract['remaining_duration'] <= 0:
                expired_contracts.append(utility_id)
                continue
            
            # Update contract duration
            contract['remaining_duration'] -= 1
            
        # Remove expired contracts
        for utility_id in expired_contracts:
            del self.utility_contracts[utility_id]
        
    def maintain_facility(self) -> None:
        """Perform facility maintenance and update efficiency."""
        maintenance_cost = self.max_production_capacity * self.maintenance_cost_rate
        
        # Record maintenance cost as a transaction and update resources
        self.record_transaction('cost_maintenance', 0, maintenance_cost, self.unique_id)
        
        # Random events can affect efficiency
        event_chance = np.random.random()
        if event_chance < 0.05:  # 5% chance of efficiency drop
            self.production_efficiency *= 0.95
        elif event_chance > 0.95:  # 5% chance of efficiency improvement
            self.production_efficiency = min(1.0, self.production_efficiency * 1.05)
            
    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the producer."""
        state = {
            'resources': self.resources,
            'profit': self.profit,
            'transaction_history': self.transaction_history[-5:] if self.transaction_history else [],
            'persona': self.persona,
            'production_type': self.production_type,
            'max_production_capacity': self.max_production_capacity,
            'current_production': self.current_production,
            'current_price': self.current_price,
            'production_efficiency': self.production_efficiency,
            'contracts': list(self.utility_contracts.values()),
            'is_renewable': self.is_renewable()
        }
        return state
    
    async def step_async(self) -> None:
        """Execute one step of the producer agent."""
        # Maintain facility and update efficiency
        self.maintain_facility()
        
        # Fulfill existing contracts
        self.manage_contracts()
        
        # Get current state
        state = self.get_state()
        market_state = self.model.get_market_state()
        
        # Get LLM decision about production strategy
        decision = await self.llm_decision_maker.get_producer_decision_async(
            state=state,
            market_state=market_state,
        )
        
        # Apply LLM decisions
        self.current_production = min(
            decision.production_level,
            self.max_production_capacity
        )
        self.current_price = decision.price
        
        # Update contract acceptance policy
        self.accept_contracts = decision.accept_contracts
        self.min_contract_duration = decision.min_contract_duration
        
        # Consider capacity upgrade based on LLM decision
        if decision.consider_upgrade:
            print(f"    {self.unique_id} upgrades its production capacity of {self.upgrade_capacity_increase} for a cost of {self.upgrade_cost}")
            self.max_production_capacity += self.upgrade_capacity_increase
            self.update_resources(-self.upgrade_cost)