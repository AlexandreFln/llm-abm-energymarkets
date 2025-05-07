from mesa import Agent
import numpy as np
from typing import Optional, Dict, Any
from src.energy_market.utils.llm_decision import LLMDecisionMaker

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
        self.llm_decision_maker = LLMDecisionMaker()
        
    def update_resources(self, amount: float) -> None:
        """Update agent's resources by adding/subtracting amount."""
        self.resources += amount
        
    def record_transaction(self, 
                         transaction_type: str,
                         amount: float,
                         price: float,
                         counterparty_id: str) -> None:
        """Record a transaction in the agent's history and update resources.
        
        Args:
            transaction_type: Type of transaction (buy/sell/cost)
            amount: Amount of energy traded
            price: Price per unit
            counterparty_id: ID of the other party in transaction
        """
        total_value = amount * price
        
        transaction = {
            'timestamp': self.model._steps,
            'type': transaction_type,
            'amount': amount,
            'price': price,
            'counterparty': counterparty_id,
            'total_value': total_value,
        }

        counterpart_transaction = transaction.copy()
        
        counterpart = self.model.get_agent(counterparty_id)
        # Update profit based on transaction type
        if transaction_type == 'sell':
            self.update_resources(total_value)  # Revenue from sale
            counterpart.update_resources(-total_value)
            is_renewable = self.is_renewable()
            counterpart_transaction['type'] = 'buy'
            counterpart_transaction['counterparty'] = self.unique_id
            counterpart_transaction['is_renewable'] = is_renewable
            transaction['is_renewable'] = is_renewable
            # Only producer agents record a 'sell' transaction with utilities
            self.utility_contracts[counterpart.unique_id] = {
                    'accepted': True,
                    'utility_id': counterpart.unique_id,
                    'amount': amount,
                    'price': price,
                    'duration': self.min_contract_duration,
                    'remaining_duration': self.min_contract_duration,
                    'is_renewable': is_renewable
                    }
            counterpart.producer_contracts[self.unique_id] = {
                    'accepted': True,
                    'utility_id': self.unique_id,
                    'amount': amount,
                    'price': price,
                    'duration': self.min_contract_duration,
                    'remaining_duration': self.min_contract_duration,
                    'is_renewable': is_renewable
                    }
            
        elif transaction_type == 'buy':
            self.update_resources(-total_value)  # Cost of purchase
            counterpart.update_resources(total_value)
            counterpart_transaction['type'] = 'sell'
            counterpart_transaction['counterparty'] = self.unique_id
            from src.energy_market.agents.consumer import ConsumerAgent
            from src.energy_market.agents.utility import UtilityAgent
            from src.energy_market.agents.prosumer import ProsumerAgent
            if isinstance(self, ConsumerAgent):
                if isinstance(counterpart, UtilityAgent):
                    is_renewable = counterpart.renewable_quota > 0.5
                    counterpart_transaction['is_renewable'] = is_renewable
                    transaction['is_renewable'] = is_renewable
                    counterpart.customer_base[self.unique_id] = {
                        'id': self.unique_id,
                        'amount': amount,
                        'price': price,
                        'avg_consumption': self.energy_needs,
                        'last_purchase': self.model._steps,
                        'is_renewable': is_renewable,
                        }
                if isinstance(counterpart, ProsumerAgent):
                    counterpart_transaction['is_renewable'] = True
                    transaction['is_renewable'] = True

            elif isinstance(self, UtilityAgent):
                # Producer pays production costs
                counterpart.update_resources(-counterpart.base_production_cost*amount)
                is_renewable = counterpart.is_renewable()
                counterpart_transaction['is_renewable'] = is_renewable
                transaction['is_renewable'] = is_renewable
                self.producer_contracts[counterpart.unique_id] = {
                    'accepted': True,
                    'producer_id': counterpart.unique_id,
                    'amount': amount,
                    'price': price,
                    'duration': counterpart.min_contract_duration,
                    'remaining_duration': counterpart.min_contract_duration,
                    'is_renewable': is_renewable
                    }
                counterpart.utility_contracts[self.unique_id] = {
                    'accepted': True,
                    'utility_id': self.unique_id,
                    'amount': amount,
                    'price': price,
                    'duration': counterpart.min_contract_duration,
                    'remaining_duration': counterpart.min_contract_duration,
                    'is_renewable': is_renewable
                    }
                
        else:   # Cost of maintenance, upgrade or production
            self.update_resources(-price)        
            self.transaction_history.append(transaction)
            return
        
        self.transaction_history.append(transaction)
        counterpart.transaction_history.append(counterpart_transaction)
        
    def get_transaction_summary(self) -> Dict[str, float]:
        """Get summary statistics of agent's transactions."""
        if not self.transaction_history:
            return {'total_volume': 0, 'total_value': 0, 'avg_price': 0, 'renewable_score': 0}
            
        total_volume = sum(t['amount'] for t in self.transaction_history)
        total_value = sum(t['total_value'] for t in self.transaction_history)
        avg_price = total_value / total_volume if total_volume > 0 else 0
        renewable_score = sum(t['is_renewable'] for t in self.transaction_history if t['type'] in ['buy', 'sell']) / len(self.transaction_history)
        
        return {
            'total_volume': total_volume,
            'total_value': total_value,
            'avg_price': avg_price,
            'renewable_score': renewable_score,
        }
        
    def step(self) -> None:
        """Base step function to be implemented by child classes."""
        pass

    async def step_async(self) -> None:
        """Execute one step of the agent's behavior asynchronously."""
        pass 