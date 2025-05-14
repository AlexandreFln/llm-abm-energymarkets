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
            'renewable_preference': self.renewable_preference,
            'transaction_history': self.transaction_history[-5:] if self.transaction_history else [],
            'market_time': self.model._steps,
        }
        
    def _execute_decision(self, decision: Dict[str, Any]) -> None:
        """Execute the agent's decision.
        
        Args:
            decision: The decision made by the agent
        """
        if not decision or not decision.best_offer:
            try:
                # Chose last transaction if possible
                last_transaction = [t for t in self.transaction_history if t['type'] == 'buy'][-1]
                seller_id = last_transaction['counterparty']
                amount = min(last_transaction['amount'], self.energy_needs)
                price = last_transaction['price']

            except IndexError as e:
                # Choose offer with cheapest price among utilities
                print(f"      Failed to retrieve last transaction from transaction_history {self.unique_id}: {str(e)}")
                print(f"      Transaction history: {self.transaction_history}")
                print(f"      Picking available offer with cheapest price...")
                available_offers = self.model.get_available_offers() 
                utilities_offers = sorted([u for u in available_offers if 'utility' in u['seller_id']], key=lambda u: u['price'])
                best_offer = utilities_offers[0]
                seller_id = best_offer['seller_id']
                amount = min(best_offer['amount'], self.energy_needs)
                price = best_offer['price']
        
        else:
            best_offer = decision.best_offer
            seller_id = best_offer.seller_id
            amount = min(best_offer.amount, self.energy_needs)
            price = best_offer.price
        
        if not seller_id or amount <= 0 or price <= 0:
            available_offers = self.model.get_available_offers() 
            utilities_offers = sorted([u for u in available_offers if 'utility' in u['seller_id']], key=lambda u: u['price'])
            best_offer = utilities_offers[0]
            seller_id = best_offer['seller_id']
            amount = min(best_offer['amount'], self.energy_needs)
            price = best_offer['price']
            
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
        # Get available offers from the market
        available_offers = self.model.get_available_offers()
        # Get agent's state for decision making
        state = self._get_state()
        # Make decision using LLM asynchronously
        decision = await self.llm_decision_maker.get_consumer_decision_async(
            state, available_offers
        )
        # Execute decision
        self._execute_decision(decision)

        # Add variation in energy needs
        noise = 0.2 * np.random.random()  # Max variation of +20% or -20%
        # Decide whether it's an increase or decrease in consumption
        if noise > 0.5:
            noise *= -1 
        self.energy_needs *= (1 + noise)

        # Receive an income to pay energy needs
        self.resources += 1000