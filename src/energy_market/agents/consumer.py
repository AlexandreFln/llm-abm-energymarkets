from typing import Dict, Any, Optional
import numpy as np

from .base import EnergyMarketAgent

class ConsumerAgent(EnergyMarketAgent):
    """Consumer agent that purchases energy from utilities or prosumers."""
    #TODO: remove price tolerance ?
    def __init__(self,
                 unique_id: str,
                 model: Any,
                 persona: str,
                 initial_resources: float = 1000.0,
                 energy_needs: float = 100.0,
                 max_price_tolerance: float = 150.0,
                 min_price_tolerance: float = 50.0,
                 green_energy_preference: float = 0.5):
        """Initialize consumer agent.
        
        Args:
            unique_id: Unique identifier for the agent
            model: The model instance the agent belongs to
            persona: The agent's personality/behavior type
            initial_resources: Starting monetary resources
            energy_needs: Amount of energy needed per step
            max_price_tolerance: Maximum price willing to pay per unit
            min_price_tolerance: Minimum price considered suspicious/too good to be true
            green_energy_preference: Preference for renewable energy (0-1)
        """
        super().__init__(unique_id, model, persona, initial_resources)
        self.energy_needs = energy_needs
        self.max_price_tolerance = max_price_tolerance
        self.min_price_tolerance = min_price_tolerance
        self.green_energy_preference = green_energy_preference
        self.current_utility: Optional[str] = None
        self.energy_balance = 0.0
    
    #TODO: replace with LLM decision
    def evaluate_offer(self, price: float, is_renewable: bool) -> float:
        """Evaluate an energy offer based on price and source.
        
        Args:
            price: Offered price per unit
            is_renewable: Whether the energy is from renewable sources
            
        Returns:
            float: Score for the offer (higher is better)
        """
        if price > self.max_price_tolerance or price < self.min_price_tolerance:
            return 0.0
            
        price_score = 1.0 - (price / self.max_price_tolerance)
        renewable_score = self.green_energy_preference if is_renewable else 0.0
        
        return 0.7 * price_score + 0.3 * renewable_score
        
    def purchase_energy(self, seller_id: str, amount: float, price: float) -> bool:
        """Attempt to purchase energy from a seller.
        
        Args:
            seller_id: ID of the selling agent
            amount: Amount of energy to purchase
            price: Price per unit
            
        Returns:
            bool: Whether the purchase was successful
        """
        total_cost = amount * price
        if total_cost > self.resources:
            return False
            
        self.update_resources(-total_cost)
        self.energy_balance += amount
        self.record_transaction('buy', amount, price, seller_id)
        return True
        
    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the consumer for decision making."""
        return {
            'resources': self.resources,
            'energy_needs': self.energy_needs,
            'energy_balance': self.energy_balance,
            'max_price_tolerance': self.max_price_tolerance,
            'green_preference': self.green_energy_preference,
            'current_utility': self.current_utility,
            'transaction_history': self.transaction_history[-5:] if self.transaction_history else []
        }
        
    def step(self) -> None:
        """Execute one step of the consumer agent."""
        # Reset energy balance for new step
        self.energy_balance = 0.0
        
        # Get available offers from utilities and prosumers
        market_state = self.model.get_market_state()
        best_offer = None
        best_score = -1

        
        # for offer in market_state['offers']:
        #     score = self.evaluate_offer(offer['price'], offer['is_renewable'])
        #     if score > best_score:
        #         best_score = score
        #         best_offer = offer
        
        # Get LLM decision about best offer
        decision = self.llm_decision_maker.get_consumer_decision({
            **self.get_state(),
            'available_offers': market_state['offers']
        })
        
        best_offer = decision.get('best_offer')
        best_score = decision.get('best_score', -1)

        if best_offer and best_score > 0:
            success = self.purchase_energy(
                best_offer['seller_id'],
                min(self.energy_needs, best_offer['amount']),
                best_offer['price']
            )
            if success:
                self.current_utility = best_offer['seller_id'] 