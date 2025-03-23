from typing import Dict, Any, Optional
import json
from langchain_ollama import OllamaLLM
import time

class LLMDecisionMaker:
    """Class for making agent decisions using LLMs."""
    
    def __init__(self, 
                 model_name: str = "llama3.2:3b-instruct-fp16",
                 timeout: float = 5.0):
        """Initialize LLM decision maker.
        
        Args:
            model_name: Name of the Ollama model to use
            timeout: Timeout in seconds for LLM calls
        """
        self.llm = OllamaLLM(
            model=model_name,
            timeout=timeout
        )
        
    def _format_state_for_prompt(self, state: Dict[str, Any]) -> str:
        """Format agent state for prompt.
        
        Args:
            state: Agent state dictionary
            
        Returns:
            str: Formatted state string
        """
        # Convert numeric values to strings with limited precision
        formatted_state = {}
        for key, value in state.items():
            if isinstance(value, (float, int)):
                formatted_state[key] = f"{value:.2f}"
            elif isinstance(value, list) and len(value) > 5:
                formatted_state[key] = value[-5:]  # Only show last 5 items
            else:
                formatted_state[key] = value
                
        return json.dumps(formatted_state, indent=2)
        
    def _safe_llm_call(self, prompt: str, default_response: Dict[str, Any]) -> Dict[str, Any]:
        """Make an LLM call with error handling and timeout.
        
        Args:
            prompt: The prompt to send to the LLM
            default_response: Default response to use if LLM call fails
            
        Returns:
            Dict containing the decision
        """
        try:
            response = self.llm.invoke(prompt)
            return json.loads(response)
        except (json.JSONDecodeError, Exception) as e:
            print(f"LLM call failed: {e}. Using default response.")
            return default_response
        
    def get_consumer_decision(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Get consumer decision about energy purchases.
        
        Args:
            state: Current state of the consumer agent
            
        Returns:
            Dict containing decision details
        """
        default_response = {
            "action": "wait",
            "max_price": state.get("max_price_tolerance", 100),
            "target_amount": state.get("energy_needs", 0),
            "prefer_renewable": state.get("green_energy_preference", 0.5) > 0.5
        }
        
        prompt = f"""You are an energy consumer making decisions about energy purchases.
Given your current state:

{self._format_state_for_prompt(state)}

Decide whether to:
1. Buy energy from a utility company
2. Buy energy from local prosumers
3. Wait for better prices

Consider:
- Your current resources and energy needs
- Available prices and your price tolerance
- Your preference for renewable energy
- Your transaction history

Respond with a JSON object containing:
- "action": "buy_utility", "buy_local", or "wait"
- "max_price": Maximum price willing to pay
- "target_amount": Amount of energy to purchase
- "prefer_renewable": Whether to prioritize renewable sources

Example response:
{
    "action": "buy_utility",
    "max_price": 120.0,
    "target_amount": 100.0,
    "prefer_renewable": true
}
"""
        return self._safe_llm_call(prompt, default_response)
        
    def get_prosumer_decision(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Get prosumer decision about energy production and sales.
        
        Args:
            state: Current state of the prosumer agent
            
        Returns:
            Dict containing decision details
        """
        default_response = {
            "sell_amount": 0.0,
            "selling_price": state.get("current_price", 100),
            "use_storage": 0.0,
            "store_amount": state.get("current_production", 0),
            "consider_upgrade": False
        }
        
        prompt = f"""You are a prosumer (consumer who also produces energy) making decisions about energy production and sales.
Given your current state:

{self._format_state_for_prompt(state)}

Decide how to manage your energy production and storage.
Consider:
- Your production capacity and efficiency
- Current market prices and trends
- Your storage levels and capacity
- Your own energy needs
- Potential for capacity upgrades

Respond with a JSON object containing:
- "sell_amount": Amount of energy to sell
- "selling_price": Price to offer energy at
- "use_storage": Amount of stored energy to use
- "store_amount": Amount of energy to store
- "consider_upgrade": Whether to consider a capacity upgrade

Example response:
{
    "sell_amount": 50.0,
    "selling_price": 90.0,
    "use_storage": 20.0,
    "store_amount": 30.0,
    "consider_upgrade": false
}
"""
        return self._safe_llm_call(prompt, default_response)
        
    def get_producer_decision(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Get producer decision about energy production and pricing.
        
        Args:
            state: Current state of the producer agent
            
        Returns:
            Dict containing decision details
        """
        default_response = {
            "production_level": state.get("max_capacity", 0) * 0.8,
            "price": state.get("current_price", 100),
            "accept_contracts": True,
            "min_contract_duration": 30,
            "consider_upgrade": False
        }
        
        prompt = f"""You are an energy producer making decisions about production levels and pricing.
Given your current state:

{self._format_state_for_prompt(state)}

Decide on your production strategy.
Consider:
- Your production capacity and costs
- Market demand and competition
- Current contracts and obligations
- Regulatory environment (carbon tax)
- Potential for capacity upgrades

Respond with a JSON object containing:
- "production_level": Target production level
- "price": Selling price per unit
- "accept_contracts": Whether to accept new contracts
- "min_contract_duration": Minimum contract duration to accept
- "consider_upgrade": Whether to consider a capacity upgrade

Example response:
{
    "production_level": 800.0,
    "price": 95.0,
    "accept_contracts": true,
    "min_contract_duration": 30,
    "consider_upgrade": true
}
"""
        return self._safe_llm_call(prompt, default_response)
        
    def get_utility_decision(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Get utility decision about energy procurement and pricing.
        
        Args:
            state: Current state of the utility agent
            
        Returns:
            Dict containing decision details
        """
        default_response = {
            "target_contracts": 1,
            "max_purchase_price": state.get("current_buying_price", 80),
            "selling_price": state.get("current_selling_price", 100),
            "renewable_target": state.get("renewable_quota", 0.2),
            "storage_strategy": "maintain"
        }
        
        prompt = f"""You are an energy utility company making decisions about energy procurement and pricing.
Given your current state:

{self._format_state_for_prompt(state)}

Decide on your market strategy.
Consider:
- Your current contracts and prices
- Customer demand and behavior
- Renewable energy quotas
- Market competition
- Regulatory requirements

Respond with a JSON object containing:
- "target_contracts": Number of new contracts to seek
- "max_purchase_price": Maximum price to pay for energy
- "selling_price": Price to sell energy at
- "renewable_target": Target percentage of renewable energy
- "storage_strategy": "increase", "decrease", or "maintain"

Example response:
{
    "target_contracts": 3,
    "max_purchase_price": 85.0,
    "selling_price": 110.0,
    "renewable_target": 0.25,
    "storage_strategy": "increase"
}
"""
        return self._safe_llm_call(prompt, default_response)
        
    def get_regulator_decision(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Get regulator decision about market intervention.
        
        Args:
            state: Current state of the regulator agent
            
        Returns:
            Dict containing decision details
        """
        default_response = {
            "adjust_carbon_tax": 0.0,
            "price_intervention": False,
            "max_price_increase": state.get("max_price_increase", 0.2),
            "enforce_renewable_quota": True,
            "issue_warnings": []
        }
        
        prompt = f"""You are an energy market regulator making decisions about market intervention.
Given your current state:

{self._format_state_for_prompt(state)}

Decide on regulatory actions.
Consider:
- Market concentration and competition
- Price stability and affordability
- Renewable energy adoption
- Recent violations and fines
- Overall market health

Respond with a JSON object containing:
- "adjust_carbon_tax": Percentage change in carbon tax (-10 to +10)
- "price_intervention": Whether to intervene in pricing
- "max_price_increase": Maximum allowed price increase
- "enforce_renewable_quota": Whether to strictly enforce quotas
- "issue_warnings": List of warning types to issue

Example response:
{
    "adjust_carbon_tax": 5.0,
    "price_intervention": true,
    "max_price_increase": 0.15,
    "enforce_renewable_quota": true,
    "issue_warnings": ["price_gouging", "market_concentration"]
}
"""
        return self._safe_llm_call(prompt, default_response) 