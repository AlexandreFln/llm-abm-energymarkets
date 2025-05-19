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
                 upgrade_cost: float = 500.0,
                 upgrade_capacity_increase: float = 8.0,
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
        self.current_production = 0.0
        
    async def step_async(self) -> None:
        """Execute one step of the prosumer agent."""
        # Calculate production and pay maintenance
        self.current_production = self.calculate_production()
        # Apply LLM decisions
        energy_needs = self.energy_needs - self.current_production
        if energy_needs > 0:
            self.energy_needs = energy_needs
        else:
            self.energy_needs = 0
        
        await super().step_async()
        
    def calculate_production(self) -> float:
        """Calculate energy production for current step based on conditions."""
        if self.production_type == "solar":
            # Simulate solar production with daily and weather variations
            time_of_day = np.random.randint(0, 25) / 24.0  # Day time between 0 and 1
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
    