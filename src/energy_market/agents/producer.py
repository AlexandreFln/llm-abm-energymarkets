from typing import Dict, Any, List, Optional
import numpy as np

from .base import EnergyMarketAgent

class EnergyProducerAgent(EnergyMarketAgent):
    """Energy producer agent that generates and sells energy to utilities."""
    
    PRODUCTION_TYPES = ["oil", "gas", "coal", "nuclear", "solar", "wind", "hydro"]
    
    def __init__(self,
                 unique_id: str,
                 model: Any,
                 persona: str,
                 production_type: str,
                 initial_resources: float = 10000.0,
                 max_capacity: float = 1000.0,
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
            max_capacity: Maximum production capacity per step
            base_production_cost: Base cost per unit of energy produced
            maintenance_cost_rate: Maintenance cost as fraction of capacity
            upgrade_cost: Cost to upgrade production capacity
            upgrade_capacity_increase: Amount capacity increases per upgrade
            min_profit_margin: Minimum acceptable profit margin
        """
        super().__init__(unique_id, model, persona, initial_resources)
        
        if production_type not in self.PRODUCTION_TYPES:
            raise ValueError(f"Invalid production type. Must be one of: {self.PRODUCTION_TYPES}")
            
        self.production_type = production_type
        self.max_capacity = max_capacity
        self.base_production_cost = base_production_cost
        self.maintenance_cost_rate = maintenance_cost_rate
        self.upgrade_cost = upgrade_cost
        self.upgrade_capacity_increase = upgrade_capacity_increase
        self.min_profit_margin = min_profit_margin
        
        # Dynamic state variables
        self.current_production = 0.0
        self.current_price = base_production_cost * (1 + min_profit_margin * 2)
        self.utility_contracts: Dict[str, Dict[str, Any]] = {}
        self.production_efficiency = 1.0
        
    def is_renewable(self) -> bool:
        """Check if the production type is renewable."""
        return self.production_type in ["solar", "wind", "hydro"]
        
    def calculate_production_cost(self, amount: float) -> float:
        """Calculate the cost to produce a given amount of energy.
        
        Args:
            amount: Amount of energy to produce
            
        Returns:
            float: Total cost of production
        """
        # Base cost with efficiency factor
        base_cost = amount * self.base_production_cost / self.production_efficiency
        
        # Add maintenance cost
        maintenance = self.max_capacity * self.maintenance_cost_rate
        
        # Add carbon tax for non-renewable sources
        if not self.is_renewable():
            carbon_tax = amount * self.model.get_carbon_tax_rate()
        else:
            carbon_tax = 0
            
        return base_cost + maintenance + carbon_tax
        
    # TODO: use LLM decision making here
    def calculate_optimal_production(self) -> float:
        """Calculate optimal production level based on contracts and market conditions."""
        total_contracted = sum(
            contract['amount'] for contract in self.utility_contracts.values()
        )
        
        # Consider market demand beyond contracts
        market_state = self.model.get_market_state()
        market_demand = market_state['total_demand']
        market_supply = market_state['total_supply']
        
        # Calculate market share based on capacity
        total_capacity = market_state['total_capacity']
        market_share = self.max_capacity / total_capacity if total_capacity > 0 else 0
        
        # Estimate additional production for spot market
        potential_spot_demand = max(0, market_demand - market_supply) * market_share
        
        # Calculate optimal production considering costs and prices
        optimal_amount = total_contracted + potential_spot_demand
        optimal_amount = min(optimal_amount, self.max_capacity)
        
        # Ensure production cost allows for minimum profit margin
        max_iterations = 20  # Maximum number of iterations to prevent infinite loops
        min_threshold = 0.01  # Minimum production threshold (1% of max capacity)
        iteration = 0
        
        while optimal_amount > min_threshold * self.max_capacity and iteration < max_iterations:
            cost = self.calculate_production_cost(optimal_amount)
            if cost / optimal_amount * (1 + self.min_profit_margin) <= self.current_price:
                break
            optimal_amount *= 0.9  # Reduce by 10% and try again
            iteration += 1
            
        # If we hit the iteration limit, return the minimum threshold
        if iteration >= max_iterations:
            optimal_amount = min_threshold * self.max_capacity
            
        return optimal_amount
        
    # TODO: use LLM decision making here
    def adjust_price(self) -> None:
        """Adjust energy price based on market conditions and costs."""
        market_state = self.model.get_market_state()
        avg_market_price = market_state['average_price']
        
        # Calculate minimum viable price
        min_price = self.base_production_cost * (1 + self.min_profit_margin)
        
        if not self.is_renewable():
            min_price *= 1 + self.model.get_carbon_tax_rate()
            
        # Adjust price based on market conditions and production costs
        if self.current_production > self.max_capacity * 0.9:
            # High utilization - increase price
            target_price = max(avg_market_price * 1.1, min_price * 1.2)
        elif self.current_production < self.max_capacity * 0.5:
            # Low utilization - decrease price
            target_price = max(avg_market_price * 0.9, min_price)
        else:
            # Normal utilization - move toward market average
            target_price = max(avg_market_price, min_price)
            
        # Smooth price changes
        self.current_price = (self.current_price + target_price) / 2
        
    # TODO: use LLM decision making here
    def negotiate_contract(self, utility_id: str, amount: float, duration: int) -> Dict[str, Any]:
        """Negotiate a contract with a utility.
        
        Args:
            utility_id: ID of the utility
            amount: Requested amount of energy per step
            duration: Contract duration in steps
            
        Returns:
            Dict containing contract terms
        """
        # Check if we can fulfill the contract
        available_capacity = self.max_capacity
        for contract in self.utility_contracts.values():
            available_capacity -= contract['amount']
            
        if amount > available_capacity:
            return {'accepted': False, 'reason': 'Insufficient capacity'}
            
        # Calculate contract price with volume discount
        volume_discount = min(0.1, amount / self.max_capacity * 0.2)  # Up to 10% discount
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
        
    def fulfill_contracts(self) -> None:
        """Fulfill existing contracts and update their status."""
        expired_contracts = []
        
        for utility_id, contract in self.utility_contracts.items():
            if contract['remaining_duration'] <= 0:
                expired_contracts.append(utility_id)
                continue
                
            # Deliver contracted amount
            amount = contract['amount']
            price = contract['price']
            
            # Record transaction
            self.record_transaction('sell', amount, price, utility_id)
            self.update_resources(amount * price)
            
            # Update contract duration
            contract['remaining_duration'] -= 1
            
        # Remove expired contracts
        for utility_id in expired_contracts:
            del self.utility_contracts[utility_id]
            
    # TODO: use LLM decision making here
    def consider_upgrade(self) -> bool:
        """Consider upgrading production capacity.
        
        Returns:
            bool: Whether upgrade was performed
        """
        if self.resources < self.upgrade_cost * 2:  # Maintain safety margin
            return False
            
        # Calculate ROI based on recent performance
        transaction_summary = self.get_transaction_summary()
        daily_revenue = transaction_summary['total_value'] / max(1, len(self.transaction_history))
        daily_production = transaction_summary['total_volume'] / max(1, len(self.transaction_history))
        
        if daily_production > self.max_capacity * 0.8:  # High utilization
            expected_increase = self.upgrade_capacity_increase * self.current_price
            payback_days = self.upgrade_cost / expected_increase
            
            if payback_days < 60:  # Less than 60 days payback period
                self.update_resources(-self.upgrade_cost)
                self.max_capacity += self.upgrade_capacity_increase
                return True
                
        return False
        
    def maintain_facility(self) -> None:
        """Perform facility maintenance and update efficiency."""
        maintenance_cost = self.max_capacity * self.maintenance_cost_rate
        self.update_resources(-maintenance_cost)
        
        # Random events can affect efficiency
        event_chance = np.random.random()
        if event_chance < 0.05:  # 5% chance of efficiency drop
            self.production_efficiency *= 0.95
        elif event_chance > 0.95:  # 5% chance of efficiency improvement
            self.production_efficiency = min(1.0, self.production_efficiency * 1.05)
            
    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the producer."""
        state = super().get_state()
        state.update({
            'production_type': self.production_type,
            'max_capacity': self.max_capacity,
            'current_production': self.current_production,
            'current_price': self.current_price,
            'production_efficiency': self.production_efficiency,
            'contracts': list(self.utility_contracts.values()),
            'is_renewable': self.is_renewable()
        })
        return state
        
    def step(self) -> None:
        """Execute one step of the producer agent."""
        # Maintain facility and update efficiency
        self.maintain_facility()
        
        # Get current state
        state = self.get_state()
        market_state = self.model.get_market_state()
        
        # Get LLM decision about production strategy
        decision = self.llm_decision_maker.get_producer_decision({
            **state,
            'market_state': market_state
        })
        
        # Apply LLM decisions
        self.current_production = min(
            decision['production_level'],
            self.max_capacity
        )
        self.current_price = decision['price']
        
        # Fulfill existing contracts
        self.fulfill_contracts()
        
        # Consider upgrading capacity based on LLM decision
        if decision['consider_upgrade']:
            self.consider_upgrade() 