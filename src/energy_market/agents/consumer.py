from typing import Dict, Any
from .base import EnergyMarketAgent
from src.energy_market.utils.llm_decision import LLMDecisionMaker

class ConsumerAgent(EnergyMarketAgent):
    """Agent representing an energy consumer in the market."""
    
    def __init__(self, 
                 unique_id: str, 
                 model: Any, 
                 persona: str,
                 initial_resources: float,
                 energy_needs: float,
                 price_sensitivity: float = 0.5,
                 renewable_preference: float = 0.3):
        """Initialize consumer agent.
        
        Args:
            unique_id: Unique identifier for the agent
            model: The model instance the agent belongs to
            persona: The agent's personality/behavior type
            initial_resources: Starting monetary resources
            energy_needs: Base energy consumption needs
            price_sensitivity: How sensitive the agent is to price changes (0-1)
            renewable_preference: Preference for renewable energy (0-1)
        """
        super().__init__(unique_id, model, persona, initial_resources)
        self.energy_needs = energy_needs
        self.price_sensitivity = price_sensitivity
        self.renewable_preference = renewable_preference
        self.current_consumption = 0.0
        self.energy_price = 0.0
        
        
    def _get_state(self) -> Dict[str, Any]:
        """Get current state of the agent for decision making.
        
        Returns:
            Dict containing agent state
        """
        return {
            'id': self.unique_id,
            'persona': self.persona,
            'resources': self.resources,
            'energy_needs': self.energy_needs,
            'current_consumption': self.current_consumption,
            'energy_price': self.energy_price,
            'price_sensitivity': self.price_sensitivity,
            'renewable_preference': self.renewable_preference,
            'transaction_history': self.transaction_history[-5:] if self.transaction_history else [],
            'market_time': self.model.schedule.time,
        }
        
    def _execute_decision(self, decision: Dict[str, Any]) -> None:
        """Execute the agent's decision.
        
        Args:
            decision: The decision made by the agent
        """
        if not decision or 'best_offer' not in decision or not decision['best_offer']:
            return
            
        best_offer = decision['best_offer']
        seller_id = best_offer.get('seller_id')
        amount = min(best_offer.get('amount', 0), self.energy_needs)
        price = best_offer.get('price', 0)
        
        if not seller_id or amount <= 0 or price <= 0:
            return
            
        # Calculate total cost and ensure agent has enough resources for amount contracted
        if amount * price > self.resources:
            amount = self.resources / price
            
        if amount > 0:
            # Record and execute transaction
            self.record_transaction(
                transaction_type='buy',
                amount=amount,
                price=price,
                counterparty_id=seller_id
                ) 
            
            # Update agent state
            self.current_consumption = amount
            self.energy_price = price
            
            
    async def step_async(self) -> None:
        """Execute one step of the consumer agent's behavior asynchronously."""
        # initial_resources = self.resources
        # Get available offers from the market
        available_offers = self.model.get_available_offers()
        # Get agent's state for decision making
        state = self._get_state()
        # Make decision using LLM asynchronously
        decision = await self.llm_decision_maker.get_consumer_decision_async(
            state, available_offers
        )
        # Execute decision
        self._execute_decision(decision) #TODO DEBUG: check offer - amount - price

        # profit = self.resources - initial_resources
        # self.profit += profit
        # print(f"    {self.unique_id} made a profit of {profit}")