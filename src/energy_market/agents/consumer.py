import numpy as np

from typing import Dict, Any
from src.energy_market.agents.base import EnergyMarketAgent

class ConsumerAgent(EnergyMarketAgent):
    """Agent representing an energy consumer in the market."""
    
    def __init__(self, 
                 unique_id: str, 
                 model: Any, 
                 persona: str,
                 initial_resources: float,
                 energy_needs: float,
                 renewable_preference: float = 0.3):
        """Initialize consumer agent.
        
        Args:
            unique_id: Unique identifier for the agent
            model: The model instance the agent belongs to
            persona: The agent's personality/behavior type
            initial_resources: Starting monetary resources
            energy_needs: Base energy consumption needs
            renewable_preference: Preference for renewable energy (0-1)
        """
        super().__init__(unique_id, model, persona, initial_resources)
        self.energy_needs = energy_needs
        self.renewable_preference = renewable_preference
        self.energy_cost = 0
            
    async def step_async(self) -> None:
        """Execute one step of the consumer agent's behavior asynchronously."""
        # Add variation in energy needs
        noise = 0.2 * np.random.random()  # Max variation of +20% or -20%
        # Decide whether it's an increase or decrease in consumption
        if noise > 0.5:
            noise *= -1 
        self.energy_needs *= (1 + noise)
        
        if self.energy_needs == 0:
            self.energy_needs = np.random.randint(80, 250)

        utilities = [agent for agent in self.model.schedule.agents 
                     if agent.__class__.__name__ == "UtilityAgent"]
        utility_contracted = np.random.choice(utilities)
        utility_contracted.customer_base[self.unique_id] = {
            'timestamp': self.model._steps,
            'amount': self.energy_needs,
            'price': utility_contracted.current_selling_price,
        }
        self.profit = - self.energy_needs * utility_contracted.current_selling_price
        self.energy_cost = utility_contracted.current_selling_price