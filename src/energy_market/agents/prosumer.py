from typing import Dict, Any, Optional
import numpy as np

from .consumer import ConsumerAgent

class ProsumerAgent(ConsumerAgent):
    """Prosumer agent that can both produce and consume energy."""
    #TODO: remove price tolerance ?
    def __init__(self,
                 unique_id: str,
                 model: Any,
                 persona: str,
                 production_type: str = "solar",
                 initial_resources: float = 2000.0,
                 energy_needs: float = 100.0,
                 max_price_tolerance: float = 150.0,
                 min_price_tolerance: float = 50.0,
                 green_energy_preference: float = 0.7,
                 max_production_capacity: float = 200.0,
                 storage_capacity: float = 300.0,
                 maintenance_cost_rate: float = 0.05,
                 upgrade_cost: float = 1000.0,
                 upgrade_capacity_increase: float = 50.0):
        """Initialize prosumer agent.
        
        Args:
            unique_id: Unique identifier for the agent
            model: The model instance the agent belongs to
            persona: The agent's personality/behavior type
            production_type: Type of energy production (solar, wind, etc.)
            initial_resources: Starting monetary resources
            energy_needs: Amount of energy needed per step
            max_price_tolerance: Maximum price willing to pay per unit
            min_price_tolerance: Minimum price considered suspicious
            green_energy_preference: Preference for renewable energy (0-1)
            max_production_capacity: Maximum energy production per step
            storage_capacity: Maximum energy storage capacity
            maintenance_cost_rate: Maintenance cost as fraction of capacity
            upgrade_cost: Cost to upgrade production capacity
            upgrade_capacity_increase: Amount capacity increases per upgrade
        """
        super().__init__(
            unique_id, model, persona, initial_resources,
            energy_needs, max_price_tolerance, min_price_tolerance,
            green_energy_preference
        )
        self.production_type = production_type
        self.max_production_capacity = max_production_capacity
        self.storage_capacity = storage_capacity
        self.maintenance_cost_rate = maintenance_cost_rate
        self.upgrade_cost = upgrade_cost
        self.upgrade_capacity_increase = upgrade_capacity_increase
        
        # Dynamic state variables
        self.current_production = 0.0
        self.energy_stored = 0.0
        self.selling_price = max_price_tolerance * 0.8  # Initial selling price
        self.connected_to_grid = True
        
    def calculate_production(self) -> float:
        """Calculate energy production for current step based on conditions."""
        if self.production_type == "solar":
            # Simulate solar production with daily and weather variations
            time_of_day = (self.model.schedule.time % 24) / 24.0  # Day time between 0 and 1
            day_factor = np.sin(np.pi * time_of_day) ** 2  # Peak at noon --> sinus function simulates sun movement
            weather_factor = np.random.uniform(0.6, 1.0)  # Random weather impact
            production = self.max_production_capacity * day_factor * weather_factor
        elif self.production_type == "wind":
            # Simulate wind production with more variability
            wind_factor = np.random.normal(0.7, 0.2)
            wind_factor = max(0, min(1, wind_factor))  # Clamp between 0 and 1
            production = self.max_production_capacity * wind_factor
        else:
            # Other types have more consistent output
            production = self.max_production_capacity * np.random.uniform(0.8, 1.0)
            
        return max(0, production)
        
    #TODO: remove maintenance costs ?
    def pay_maintenance(self) -> None:
        """Pay maintenance costs based on capacity."""
        maintenance_cost = self.max_production_capacity * self.maintenance_cost_rate
        self.update_resources(-maintenance_cost)
        
    def store_energy(self, amount: float) -> float:
        """Store energy up to storage capacity.
        
        Returns:
            float: Amount of energy that couldn't be stored
        """
        space_available = self.storage_capacity - self.energy_stored
        amount_stored = min(amount, space_available)
        self.energy_stored += amount_stored
        return amount - amount_stored
        
    def use_stored_energy(self, amount: float) -> float:
        """Use energy from storage.
        
        Returns:
            float: Amount of energy actually used
        """
        amount_used = min(amount, self.energy_stored)
        self.energy_stored -= amount_used
        return amount_used
    
    def adjust_selling_price(self) -> None:
        """Adjust selling price based on market conditions and inventory."""
        market_state = self.model.get_market_state()
        avg_market_price = market_state['average_price']
        storage_ratio = self.energy_stored / self.storage_capacity
        
        #TODO: use LLM decision making here
        # Adjust price based on storage levels and market price
        if storage_ratio > 0.8:  # High storage - lower price
            self.selling_price = min(
                self.selling_price,
                avg_market_price * 0.95
            )
        elif storage_ratio < 0.2:  # Low storage - raise price
            self.selling_price = min(
                self.max_price_tolerance,
                avg_market_price * 1.05
            )
        else:  # Normal storage - move toward market price
            self.selling_price = (self.selling_price + avg_market_price) / 2
            
    #TODO: use LLM decision making here
    def consider_upgrade(self) -> bool:
        """Consider upgrading production capacity.
        
        Returns:
            bool: Whether upgrade was performed
        """
        if self.resources < self.upgrade_cost * 2:  # Maintain safety margin
            return False
            
        # Calculate ROI based on recent transactions
        transaction_summary = self.get_transaction_summary()
        daily_revenue = transaction_summary['total_value'] / max(1, len(self.transaction_history))
        daily_production = transaction_summary['total_volume'] / max(1, len(self.transaction_history))
        
        if daily_production > self.max_production_capacity * 0.8:  # High utilization
            expected_increase = self.upgrade_capacity_increase * self.selling_price
            payback_days = self.upgrade_cost / expected_increase
            
            if payback_days < 30:  # Less than 30 days payback period
                self.update_resources(-self.upgrade_cost)
                self.max_production_capacity += self.upgrade_capacity_increase
                return True
                
        return False
        
    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the prosumer."""
        state = {
            'resources': self.resources,
            'profit': self.profit,
            'transaction_history': self.transaction_history[-5:] if self.transaction_history else [],
            'production_type': self.production_type,
            'max_production_capacity': self.max_production_capacity,
            'current_production': self.current_production,
            'energy_stored': self.energy_stored,
            'storage_capacity': self.storage_capacity,
            'selling_price': self.selling_price,
            'connected_to_grid': self.connected_to_grid
        }
        return state
    
    #TODO: use LLM decision making here for mix strategy between selling to local grid, storing energy, or buying from market
    def step(self) -> None:
        """Execute one step of the prosumer agent."""
        # Calculate production and pay maintenance
        self.current_production = self.calculate_production()
        self.pay_maintenance()
        
        # Get current state
        state = self.get_state()
        market_state = self.model.get_market_state()
        
        # Get LLM decision about energy management strategy
        decision = self.llm_decision_maker.get_prosumer_decision({
            **state,
            'market_state': market_state
        })
        
        # Apply LLM decisions
        energy_needed = self.energy_needs
        
        # Use stored energy based on LLM decision
        energy_from_storage = min(
            decision.use_storage,
            self.energy_stored
        )
        energy_needed -= energy_from_storage
        self.energy_stored -= energy_from_storage
        
        # Use current production
        energy_from_production = min(energy_needed, self.current_production)
        energy_needed -= energy_from_production
        remaining_production = self.current_production - energy_from_production
        
        # Store energy based on LLM decision
        if remaining_production > 0:
            amount_to_store = min(
                decision.store_amount,
                remaining_production,
                self.storage_capacity - self.energy_stored
            )
            self.energy_stored += amount_to_store
            remaining_production -= amount_to_store
            
        # Sell remaining production based on LLM decision
        if remaining_production > 0:
            self.selling_price = decision.selling_price
            self.model.add_energy_offer(
                self.unique_id,
                remaining_production,
                self.selling_price,
                True  # Always renewable
            )
            
        # Consider capacity upgrade based on LLM decision
        if decision.consider_upgrade:
            self.consider_upgrade() 