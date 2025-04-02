from typing import Dict, Any, List, Optional
import numpy as np

from .base import EnergyMarketAgent

class UtilityAgent(EnergyMarketAgent):
    """Utility agent that buys from producers and sells to consumers."""
    
    PERSONAS = ["eco_friendly", "profit_driven", "balanced"]
    
    def __init__(self,
                 unique_id: str,
                 model: Any,
                 persona: str,
                 initial_resources: float = 50000.0,
                 renewable_quota: float = 0.2,
                 min_profit_margin: float = 0.1,
                 storage_capacity: float = 500.0,
                 contract_duration: int = 30):
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
        if persona not in self.PERSONAS:
            raise ValueError(f"Invalid persona. Must be one of: {self.PERSONAS}")
            
        super().__init__(unique_id, model, persona, initial_resources)
        
        # Configuration
        self.renewable_quota = renewable_quota
        self.min_profit_margin = min_profit_margin
        self.storage_capacity = storage_capacity
        self.contract_duration = contract_duration
        
        # Dynamic state variables
        self.energy_stored = 0.0
        self.current_buying_price = 0.0  # Weighted average of contract prices
        self.current_selling_price = 0.0
        self.producer_contracts: Dict[str, Dict[str, Any]] = {}
        self.customer_base: Dict[str, Dict[str, Any]] = {}
        self.spot_market_purchases = 0.0
        
        # Initialize prices based on persona
        self._initialize_pricing_strategy()
        
    # TODO: use LLM decision making here
    def _initialize_pricing_strategy(self) -> None:
        """Initialize pricing strategy based on persona."""
        market_state = self.model.get_market_state()
        avg_market_price = market_state['average_price']
        
        if self.persona == "eco_friendly":
            # Bias towards renewable energy, accept lower margins
            self.min_profit_margin *= 0.8
            self.renewable_quota *= 1.5
        elif self.persona == "profit_driven":
            # Focus on maximizing profits
            self.min_profit_margin *= 1.2
            self.renewable_quota *= 0.8
            
        self.current_selling_price = avg_market_price * (1 + self.min_profit_margin)
    
    # TODO: use LLM decision making here
    def evaluate_producer_contract(self, 
                                 producer_id: str,
                                 contract: Dict[str, Any]) -> float:
        """Evaluate a proposed contract from a producer.
        
        Args:
            producer_id: ID of the producer
            contract: Contract terms
            
        Returns:
            float: Score for the contract (higher is better)
        """
        if not contract['accepted']:
            return 0.0
            
        # Base score on price competitiveness
        market_state = self.model.get_market_state()
        avg_market_price = market_state['average_price']
        price_score = 1.0 - (contract['price'] / avg_market_price)
        
        # Adjust for renewable preference
        renewable_score = 0.0
        if contract['is_renewable']:
            if self.persona == "eco_friendly":
                renewable_score = 0.4
            elif self.persona == "balanced":
                renewable_score = 0.2
            else:
                renewable_score = 0.1
                
        # Consider contract duration
        duration_score = min(0.2, contract['duration'] / 360)  # Cap at 1 year
        
        return 0.5 * price_score + 0.3 * renewable_score + 0.2 * duration_score
        
    def manage_producer_contracts(self) -> None:
        """Manage contracts with energy producers."""
        # Calculate current renewable ratio
        total_contracted = 0.0
        renewable_contracted = 0.0
        
        for contract in self.producer_contracts.values():
            amount = contract['amount']
            total_contracted += amount
            if contract['is_renewable']:
                renewable_contracted += amount
                
        renewable_ratio = (
            renewable_contracted / total_contracted if total_contracted > 0 else 0
        )
        
        # Estimate demand
        expected_demand = sum(
            customer['avg_consumption'] for customer in self.customer_base.values()
        )
        
        # Find available producers
        market_state = self.model.get_market_state()
        available_producers = market_state['available_producers']
        
        # Negotiate new contracts if needed
        for producer_id, producer_info in available_producers.items():
            if producer_id in self.producer_contracts:
                continue
                
            # Determine if we need more renewable or conventional energy
            need_renewable = renewable_ratio < self.renewable_quota
            if need_renewable != producer_info['is_renewable']:
                continue
                
            # Calculate desired contract amount
            desired_amount = max(0, expected_demand - total_contracted)
            if desired_amount <= 0:
                break
                
            # Request contract
            contract = self.model.request_producer_contract(
                producer_id,
                self.unique_id,
                desired_amount,
                self.contract_duration
            )
            
            # Evaluate and potentially accept contract
            score = self.evaluate_producer_contract(producer_id, contract)
            if score > 0:
                self.producer_contracts[producer_id] = contract
                total_contracted += contract['amount']
                if contract['is_renewable']:
                    renewable_contracted += contract['amount']
                    renewable_ratio = renewable_contracted / total_contracted
                    
    def calculate_selling_price(self) -> float:
        """Calculate the optimal selling price based on costs and market conditions."""
        # Calculate weighted average buying price
        total_amount = 0.0
        total_cost = 0.0
        
        for contract in self.producer_contracts.values():
            amount = contract['amount']
            total_amount += amount
            total_cost += amount * contract['price']
            
        if total_amount > 0:
            avg_buying_price = total_cost / total_amount
        else:
            market_state = self.model.get_market_state()
            avg_buying_price = market_state['average_price']
            
        # Add spot market purchases
        if self.spot_market_purchases > 0:
            market_state = self.model.get_market_state()
            total_amount += self.spot_market_purchases
            total_cost += self.spot_market_purchases * market_state['spot_price']
            avg_buying_price = total_cost / total_amount
            
        # Calculate minimum viable price
        min_price = avg_buying_price * (1 + self.min_profit_margin)
        
        # Adjust based on storage levels and market conditions
        storage_ratio = self.energy_stored / self.storage_capacity
        market_state = self.model.get_market_state()
        
        if storage_ratio < 0.2:  # Low storage
            target_price = max(min_price * 1.2, market_state['average_price'] * 1.1)
        elif storage_ratio > 0.8:  # High storage
            target_price = max(min_price, market_state['average_price'] * 0.95)
        else:  # Normal storage
            target_price = max(min_price, market_state['average_price'])
            
        # Smooth price changes
        return (self.current_selling_price + target_price) / 2
        
    def update_customer_base(self) -> None:
        """Update customer statistics and remove inactive customers."""
        inactive_customers = []
        
        for customer_id, customer in self.customer_base.items():
            if customer['last_purchase'] < self.model.schedule.time - 24:
                inactive_customers.append(customer_id)
            else:
                # Update average consumption
                recent_purchases = [
                    t['amount'] for t in self.transaction_history[-24:]
                    if t['counterparty'] == customer_id
                ]
                if recent_purchases:
                    customer['avg_consumption'] = sum(recent_purchases) / len(recent_purchases)
                    
        # Remove inactive customers
        for customer_id in inactive_customers:
            del self.customer_base[customer_id]
            
    def sell_energy(self, customer_id: str, amount: float) -> Dict[str, Any]:
        """Sell energy to a customer.
        
        Args:
            customer_id: ID of the customer
            amount: Amount of energy requested
            
        Returns:
            Dict with transaction details
        """
        # Check if we have enough energy
        available = self.energy_stored
        for contract in self.producer_contracts.values():
            available += contract['amount']
            
        if amount > available:
            return {
                'success': False,
                'amount': 0,
                'price': self.current_selling_price,
                'reason': 'Insufficient supply'
            }
            
        # Record transaction
        self.record_transaction('sell', amount, self.current_selling_price, customer_id)
        
        # Update customer info
        if customer_id not in self.customer_base:
            self.customer_base[customer_id] = {
                'first_purchase': self.model.schedule.time,
                'avg_consumption': amount
            }
        self.customer_base[customer_id]['last_purchase'] = self.model.schedule.time
        
        return {
            'success': True,
            'amount': amount,
            'price': self.current_selling_price
        }
        
    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the utility."""
        state = {
            'resources': self.resources,
            'profit': self.profit,
            'transaction_history': self.transaction_history[-5:] if self.transaction_history else [],
            'persona': self.persona,
            'renewable_quota': self.renewable_quota,
            'energy_stored': self.energy_stored,
            'storage_capacity': self.storage_capacity,
            'current_buying_price': self.current_buying_price,
            'current_selling_price': self.current_selling_price,
            'producer_contracts': list(self.producer_contracts.values()),
            'customer_count': len(self.customer_base),
            'spot_market_purchases': self.spot_market_purchases
        }
        return state
        
    def step(self) -> None:
        """Execute one step of the utility agent."""
        # Get current state
        state = self.get_state()
        market_state = self.model.get_market_state()
        
        # Get LLM decision about utility strategy
        decision = self.llm_decision_maker.get_utility_decision({
            **state,
            'market_state': market_state
        })
        
        # Apply LLM decisions
        self.renewable_quota = decision.renewable_target
        self.current_selling_price = decision.selling_price
        
        # Manage storage based on LLM decision
        if decision.storage_strategy == 'increase':
            # Buy more energy for storage
            self.spot_market_purchases = min(
                self.storage_capacity - self.energy_stored,
                market_state['available_supply']
            )
        elif decision.storage_strategy == 'decrease':
            # Sell stored energy
            amount_to_sell = min(
                self.energy_stored,
                market_state['available_demand']
            )
            if amount_to_sell > 0:
                self.model.add_energy_offer(
                    self.unique_id,
                    amount_to_sell,
                    self.current_selling_price,
                    False  # Not renewable
                )
                self.energy_stored -= amount_to_sell
                
        # Manage producer contracts
        self.manage_producer_contracts()
        
        # Update customer base
        self.update_customer_base()
        
        # Reset spot market purchases for new step
        self.spot_market_purchases = 0.0 