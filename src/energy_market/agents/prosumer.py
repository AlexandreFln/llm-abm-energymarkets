from typing import Dict, Any
import numpy as np

from .consumer import ConsumerAgent

class ProsumerAgent(ConsumerAgent):
    """Prosumer agent that can both produce and consume energy."""
    def __init__(self,
                 unique_id: str,
                 model: Any,
                 persona: str,
                 production_type: str = "solar",
                 initial_resources: float = 2000.0,
                 energy_needs: float = 100.0,
                 max_production_capacity: float = 200.0,
                 storage_capacity: float = 300.0,
                 maintenance_cost_rate: float = 0.05,
                 upgrade_cost: float = 1000.0,
                 upgrade_capacity_increase: float = 50.0,
                 green_energy_preference: float = 0.7):
        """Initialize prosumer agent.
        
        Args:
            unique_id: Unique identifier for the agent
            model: The model instance the agent belongs to
            persona: The agent's personality/behavior type
            production_type: Type of energy production (solar, wind, etc.)
            initial_resources: Starting monetary resources
            energy_needs: Amount of energy needed per step
            max_production_capacity: Maximum energy production per step
            storage_capacity: Maximum energy storage capacity
            maintenance_cost_rate: Maintenance cost as fraction of capacity
            upgrade_cost: Cost to upgrade production capacity
            upgrade_capacity_increase: Amount capacity increases per upgrade
            green_energy_preference: Preference for renewable energy (0-1)
        """
        super().__init__(
            unique_id=unique_id,
            model=model,
            persona=persona,
            initial_resources=initial_resources,
            energy_needs=energy_needs,
            renewable_preference=green_energy_preference
        )
        self.production_type = production_type
        self.max_production_capacity = max_production_capacity
        self.storage_capacity = storage_capacity
        self.maintenance_cost_rate = maintenance_cost_rate
        self.upgrade_cost = upgrade_cost
        self.upgrade_capacity_increase = upgrade_capacity_increase
        
        # Dynamic state variables
        self.energy_price = 0.0
        self.current_consumption = 0.0
        self.current_production = 0.0
        self.energy_stored = 0.0
        self.selling_price = 100.0  # Initial selling price
        self.connected_to_grid = True
        
    def calculate_production(self) -> float:
        """Calculate energy production for current step based on conditions."""
        if self.production_type == "solar":
            # Simulate solar production with daily and weather variations
            time_of_day = (self.model.schedule.time % 24) / 24.0  # Day time between 0 and 1
            #TODO: TEST TO DELETE
            print(f"###########\nAgent {self.unique_id} at step {self.model.schedule.steps}")
            print('Day Time :', time_of_day)
            print("###########\n")
            # END OF TEST
            day_factor = np.sin(np.pi * time_of_day) ** 2  # Peak at noon --> sinus function simulates sun movement
            weather_factor = np.random.uniform(0.7, 1.0)  # Random weather impact
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
        
    def pay_maintenance(self) -> None:
        """Pay maintenance costs based on capacity."""
        maintenance_cost = self.max_production_capacity * self.maintenance_cost_rate
        # Record maintenance cost as a transaction and update resources
        self.record_transaction('maintenance_cost', 0, maintenance_cost, self.unique_id)
        
    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the prosumer."""
        state = {
            'resources': self.resources,
            'profit': self.profit,
            'transaction_history': self.transaction_history[-5:] if self.transaction_history else [],
            'production_type': self.production_type,
            'max_production_capacity': self.max_production_capacity,
            'energy_price': self.energy_price,
            'current_consumption': self.current_consumption,
            'current_production': self.current_production,
            'energy_stored': self.energy_stored,
            'storage_capacity': self.storage_capacity,
            'selling_price': self.selling_price,
            'connected_to_grid': self.connected_to_grid
        }
        return state
    
    async def step_async(self) -> None:
        """Execute one step of the prosumer agent."""
        # Calculate production and pay maintenance
        self.current_production = self.calculate_production()
        self.pay_maintenance()
        
        # Get current state
        state = self.get_state()
        market_state = self.model.get_market_state()

        # Get LLM decision about energy management strategy
        decision = await self.llm_decision_maker.get_prosumer_decision_async(
            state=state,
            market_state=market_state,
            )
        
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
        
        else:
            # Still some energy needed to supply
            await super().step_async()

        # Sell remaining production based on LLM decision
        if remaining_production > 0:
            self.selling_price = decision.selling_price
            market_state['offers'].append({
                    'seller_id': self.unique_id,
                    'seller_type': 'prosumer',
                    'price': self.selling_price,
                    'amount': remaining_production,
                    'is_renewable': True
                    })
            
        # Consider capacity upgrade based on LLM decision
        if decision.consider_upgrade:
            self.max_production_capacity += self.upgrade_capacity_increase
            self.update_resources(-self.upgrade_cost)