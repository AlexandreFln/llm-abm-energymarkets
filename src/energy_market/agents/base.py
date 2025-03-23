from mesa import Agent
import numpy as np
from typing import Optional, Dict, Any

class EnergyMarketAgent(Agent):
    """Base class for all agents in the energy market."""
    
    def __init__(self, 
                 unique_id: str, 
                 model: Any, 
                 persona: str,
                 initial_resources: float):
        """Initialize base agent.
        
        Args:
            unique_id: Unique identifier for the agent
            model: The model instance the agent belongs to
            persona: The agent's personality/behavior type
            initial_resources: Starting monetary resources
        """
        super().__init__(unique_id, model)
        self.persona = persona
        self.resources = initial_resources
        self.profit = 0.0
        self.transaction_history: list[Dict[str, Any]] = []
        
    def update_resources(self, amount: float) -> None:
        """Update agent's resources by adding/subtracting amount."""
        self.resources += amount
        
    def record_transaction(self, 
                         transaction_type: str,
                         amount: float,
                         price: float,
                         counterparty_id: str) -> None:
        """Record a transaction in the agent's history.
        
        Args:
            transaction_type: Type of transaction (buy/sell)
            amount: Amount of energy traded
            price: Price per unit
            counterparty_id: ID of the other party in transaction
        """
        transaction = {
            'timestamp': self.model.schedule.time,
            'type': transaction_type,
            'amount': amount,
            'price': price,
            'counterparty': counterparty_id,
            'total_value': amount * price
        }
        self.transaction_history.append(transaction)
        
    def get_transaction_summary(self) -> Dict[str, float]:
        """Get summary statistics of agent's transactions."""
        if not self.transaction_history:
            return {'total_volume': 0, 'total_value': 0, 'avg_price': 0}
            
        total_volume = sum(t['amount'] for t in self.transaction_history)
        total_value = sum(t['total_value'] for t in self.transaction_history)
        avg_price = total_value / total_volume if total_volume > 0 else 0
        
        return {
            'total_volume': total_volume,
            'total_value': total_value,
            'avg_price': avg_price
        }
        
    def step(self) -> None:
        """Base step function to be implemented by child classes."""
        pass 