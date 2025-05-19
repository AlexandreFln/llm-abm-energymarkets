from typing import Dict, Any

from .base import EnergyMarketAgent
from .producer import EnergyProducerAgent

class UtilityAgent(EnergyMarketAgent):
    """Utility agent that buys from producers and sells to consumers."""
    
    def __init__(self,
                 unique_id: str,
                 model: Any,
                 persona: str,
                 initial_resources: float = 50000.0,
                 renewable_quota: float = 0.2,
                 min_profit_margin: float = 0.1,
                 storage_capacity: float = 500.0,
                 contract_duration: int = 3):
        """Initialize utility agent.
        
        Args:
            unique_id: Unique identifier for the agent
            model: The model instance the agent belongs to
            persona: The agent's personality/behavior type
            initial_resources: Starting monetary resources
            renewable_quota: Minimum fraction of energy from renewable sources
            min_profit_margin: Minimum acceptable profit margin
            storage_capacity: Maximum energy storage capacity
            contract_duration: Default duration for producer contracts
        """
            
        super().__init__(unique_id, model, persona, initial_resources)
        
        if persona not in self.model.personas:
            raise ValueError(
                f"Invalid persona. Must be one of: {self.model.personas}"
            )
        # Configuration
        self.renewable_quota = renewable_quota
        self.min_profit_margin = min_profit_margin
        self.storage_capacity = storage_capacity
        self.contract_duration = contract_duration
        
        # Dynamic state variables
        self.current_selling_price = 0.0
        self.producer_contracts: Dict[str, Dict[str, Any]] = {}
        self.customer_base: Dict[str, Dict[str, Any]] = {}

        
        # Initialize prices based on persona
        self._initialize_pricing_strategy()
        
    def _initialize_pricing_strategy(self) -> None:
        """Initialize pricing strategy based on persona."""
        market_price = self.model.initial_price
        
        if self.persona == "eco_friendly":
            # Bias towards renewable energy, accept lower margins
            self.min_profit_margin *= 0.8
            self.renewable_quota *= 1.5
        elif self.persona == "profit_driven":
            # Focus on maximizing profits
            self.min_profit_margin *= 1.2
            self.renewable_quota *= 0.8
            
        self.current_selling_price = market_price * (1 + self.min_profit_margin)
                    
        
    async def step_async(self) -> None:
        """Execute one step of the utility agent."""
        
        # 1. Retrieve energy amount needed for a given step
        energy_needs = sum(
            contract['amount'] for contract in self.customer_base.values()
        )
        # 2. Satisfy contracted producers and adjust purchases
        producers_for_llm = []
        producers = [
            agent for agent in self.model.schedule.agents 
            if isinstance(agent, EnergyProducerAgent)
        ]
        for producer in producers:
            max_production_capacity = producer.max_production_capacity
            producers_for_llm.append({
                'producer_id': producer.unique_id,
                'max_production_capacity': max_production_capacity,
                'spot_price': producer.current_price,
                'is_renewable': producer.is_renewable()
            })

        # Get LLM decision about utility strategy
        decision = await self.llm_decision_maker.get_utility_decision_async(
            persona=self.persona,
            energy_amount_to_supply=energy_needs,
            producers=producers_for_llm,
        )

        # 3. Aply and store decision
        self.current_selling_price = decision.selling_price

        for producer in decision.producer_contracts:
            producer_id = producer.producer_id
            amount_contracted = producer.amount
            producer_agent = self.model.get_agent(producer_id)
            
            # Add safety check to ensure producer_agent exists
            if producer_agent is None:
                print(f"Producer {producer_id} not found. Skipping contract.")
                continue
                
            self.producer_contracts[producer_id] = {
                'amount_contracted': amount_contracted,
                'is_renewable': producer_agent.is_renewable(),
            }

            producer_agent.utility_contracts[self.unique_id] = {
                'amount_contracted': amount_contracted,
                'is_renewable': producer_agent.is_renewable(),
            }
        