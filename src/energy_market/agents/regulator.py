from typing import Dict, Any, List, Optional
import numpy as np

from .base import EnergyMarketAgent

class RegulatorAgent(EnergyMarketAgent):
    """Regulator agent that oversees market dynamics and implements policies."""
    
    def __init__(self,
                 unique_id: str,
                 model: Any,
                 persona: str = "balanced",
                 initial_resources: float = float('inf'),
                 base_carbon_tax: float = 10.0,
                 max_price_increase: float = 0.2,
                 min_renewable_ratio: float = 0.3,
                 market_concentration_threshold: float = 0.4):
        """Initialize regulator agent.
        
        Args:
            unique_id: Unique identifier for the agent
            model: The model instance the agent belongs to
            persona: The agent's personality/behavior type
            initial_resources: Starting monetary resources (infinite by default)
            base_carbon_tax: Base tax rate for carbon emissions
            max_price_increase: Maximum allowed price increase per step
            min_renewable_ratio: Minimum required renewable energy ratio
            market_concentration_threshold: HHI threshold for market concentration
        """
        super().__init__(unique_id, model, persona, initial_resources)
        
        # Policy parameters
        self.base_carbon_tax = base_carbon_tax
        self.current_carbon_tax = base_carbon_tax
        self.max_price_increase = max_price_increase
        self.min_renewable_ratio = min_renewable_ratio
        self.market_concentration_threshold = market_concentration_threshold
        
        # Market monitoring
        self.price_history: List[float] = []
        self.renewable_ratio_history: List[float] = []
        self.market_concentration_history: List[float] = []
        self.violations: Dict[str, List[Dict[str, Any]]] = {
            'price_gouging': [],
            'market_concentration': [],
            'renewable_quota': []
        }
        
    def calculate_market_concentration(self, market_state: Dict[str, Any]) -> float:
        """Calculate Herfindahl-Hirschman Index (HHI) for market concentration.
        
        Args:
            market_state: Current market state
            
        Returns:
            float: HHI value between 0 and 1
        """
        total_capacity = market_state['total_capacity']
        if total_capacity == 0:
            return 0.0
            
        # Calculate market shares and HHI
        market_shares = [
            (producer['capacity'] / total_capacity) ** 2
            for producer in market_state['producers'].values()
        ]
        
        return sum(market_shares)
        
    def detect_price_gouging(self, market_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Detect instances of price gouging.
        
        Args:
            market_state: Current market state
            
        Returns:
            List of violations with agent IDs and details
        """
        violations = []
        avg_price = market_state['average_price']
        
        # Check producer prices
        for producer_id, producer in market_state['producers'].items():
            if producer['price'] > avg_price * (1 + self.max_price_increase):
                violations.append({
                    'agent_id': producer_id,
                    'type': 'producer',
                    'price': producer['price'],
                    'threshold': avg_price * (1 + self.max_price_increase)
                })
                
        # Check utility prices
        for utility_id, utility in market_state['utilities'].items():
            if utility['selling_price'] > avg_price * (1 + self.max_price_increase):
                violations.append({
                    'agent_id': utility_id,
                    'type': 'utility',
                    'price': utility['selling_price'],
                    'threshold': avg_price * (1 + self.max_price_increase)
                })
                
        return violations
        
    def adjust_carbon_tax(self, market_state: Dict[str, Any]) -> None:
        """Adjust carbon tax based on renewable energy adoption.
        
        Args:
            market_state: Current market state
        """
        current_renewable_ratio = market_state['renewable_ratio']
        
        if current_renewable_ratio < self.min_renewable_ratio:
            # Increase carbon tax to incentivize renewables
            self.current_carbon_tax *= 1.1
        elif current_renewable_ratio > self.min_renewable_ratio * 1.5:
            # Gradually decrease carbon tax if well above target
            self.current_carbon_tax *= 0.95
            
        # Ensure tax doesn't fall below base rate
        self.current_carbon_tax = max(self.base_carbon_tax, self.current_carbon_tax)
        
    def issue_fine(self, agent_id: str, violation_type: str, amount: float) -> None:
        """Issue a fine to an agent for market violations.
        
        Args:
            agent_id: ID of the agent being fined
            violation_type: Type of violation
            amount: Fine amount
        """
        agent = self.model.get_agent(agent_id)
        if agent:
            agent.update_resources(-amount)
            self.record_transaction('fine', amount, 1.0, agent_id)
            
    def calculate_fine_amount(self, violation: Dict[str, Any]) -> float:
        """Calculate fine amount based on violation type and severity.
        
        Args:
            violation: Violation details
            
        Returns:
            float: Fine amount
        """
        if violation['type'] == 'price_gouging':
            # Fine based on how much price exceeds threshold
            excess = violation['price'] - violation['threshold']
            return excess * 2.0
        elif violation['type'] == 'market_concentration':
            # Fine based on market concentration excess
            excess = violation['concentration'] - self.market_concentration_threshold
            return excess * 10000.0
        elif violation['type'] == 'renewable_quota':
            # Fine based on shortfall from quota
            shortfall = self.min_renewable_ratio - violation['ratio']
            return shortfall * 5000.0
            
        return 0.0
        
    def enforce_regulations(self, market_state: Dict[str, Any]) -> None:
        """Enforce market regulations through fines and incentives.
        
        Args:
            market_state: Current market state
        """
        # Check for price gouging
        price_violations = self.detect_price_gouging(market_state)
        for violation in price_violations:
            fine_amount = self.calculate_fine_amount(violation)
            self.issue_fine(violation['agent_id'], 'price_gouging', fine_amount)
            self.violations['price_gouging'].append({
                'time': self.model.schedule.time,
                'agent_id': violation['agent_id'],
                'amount': fine_amount
            })
            
        # Check market concentration
        concentration = self.calculate_market_concentration(market_state)
        if concentration > self.market_concentration_threshold:
            # Find largest producers
            producers = sorted(
                market_state['producers'].items(),
                key=lambda x: x[1]['capacity'],
                reverse=True
            )
            for producer_id, info in producers[:2]:  # Fine top 2 contributors
                violation = {
                    'type': 'market_concentration',
                    'concentration': concentration
                }
                fine_amount = self.calculate_fine_amount(violation)
                self.issue_fine(producer_id, 'market_concentration', fine_amount)
                self.violations['market_concentration'].append({
                    'time': self.model.schedule.time,
                    'agent_id': producer_id,
                    'amount': fine_amount
                })
                
        # Check renewable energy quotas
        renewable_ratio = market_state['renewable_ratio']
        if renewable_ratio < self.min_renewable_ratio:
            for utility_id, utility in market_state['utilities'].items():
                if utility['renewable_ratio'] < self.min_renewable_ratio:
                    violation = {
                        'type': 'renewable_quota',
                        'ratio': utility['renewable_ratio']
                    }
                    fine_amount = self.calculate_fine_amount(violation)
                    self.issue_fine(utility_id, 'renewable_quota', fine_amount)
                    self.violations['renewable_quota'].append({
                        'time': self.model.schedule.time,
                        'agent_id': utility_id,
                        'amount': fine_amount
                    })
                    
    def get_state(self) -> Dict[str, Any]:
        """Get the current state of the regulator."""
        state = super().get_state()
        state.update({
            'current_carbon_tax': self.current_carbon_tax,
            'min_renewable_ratio': self.min_renewable_ratio,
            'market_concentration_threshold': self.market_concentration_threshold,
            'recent_violations': {
                k: v[-5:] for k, v in self.violations.items()  # Last 5 violations of each type
            }
        })
        return state
        
    def step(self) -> None:
        """Execute one step of the regulator agent."""
        # Get current market state
        market_state = self.model.get_market_state()
        
        # Update market monitoring metrics
        self.price_history.append(market_state['average_price'])
        self.renewable_ratio_history.append(market_state['renewable_ratio'])
        self.market_concentration_history.append(
            self.calculate_market_concentration(market_state)
        )
        
        # Keep history limited to recent values
        max_history = 168  # One week of hourly data
        if len(self.price_history) > max_history:
            self.price_history = self.price_history[-max_history:]
            self.renewable_ratio_history = self.renewable_ratio_history[-max_history:]
            self.market_concentration_history = self.market_concentration_history[-max_history:]
            
        # Adjust carbon tax based on renewable adoption
        self.adjust_carbon_tax(market_state)
        
        # Enforce regulations and issue fines
        self.enforce_regulations(market_state) 