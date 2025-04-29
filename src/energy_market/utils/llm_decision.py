from typing import Dict, Any, Optional
import json
import time
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.output_parsers import PydanticOutputParser
from ..prompts.system_prompts import (
    CONSUMER_PROMPT,
    PROSUMER_PROMPT,
    PRODUCER_PROMPT,
    UTILITY_PROMPT,
    REGULATOR_PROMPT
)
from ..schemas.llm_decisions import (
    ConsumerDecision,
    ProsumerDecision,
    ProducerDecision,
    UtilityDecision,
    RegulatorDecision
)

class LLMDecisionMaker:
    """Class for making agent decisions using LLMs."""
    
    def __init__(self, 
                 model_name: str = "llama3.2",
                 timeout: float = 5.0,
                 ):
        """Initialize LLM decision maker.
        
        Args:
            model_name: Name of the Ollama model to use
            timeout: Timeout in seconds for LLM calls
        """
        self.llm = ChatOllama(
            model=model_name,
            # timeout=timeout,
        )
        
        # Initialize output parsers for each agent type
        self.consumer_parser = PydanticOutputParser(pydantic_object=ConsumerDecision)
        self.prosumer_parser = PydanticOutputParser(pydantic_object=ProsumerDecision)
        self.producer_parser = PydanticOutputParser(pydantic_object=ProducerDecision)
        self.utility_parser = PydanticOutputParser(pydantic_object=UtilityDecision)
        self.regulator_parser = PydanticOutputParser(pydantic_object=RegulatorDecision)
        
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
            elif isinstance(value, list):
                formatted_state[key] = value[-5:]  # Only show last 5 items
            else:
                formatted_state[key] = value
                
        return json.dumps(formatted_state, indent=2)
        
    def _safe_llm_call(self, prompt: str, default_response: Dict[str, Any], 
                      agent_type: str = None) -> Dict[str, Any]:
        """Make an LLM call with error handling and timeout.
        
        Args:
            prompt: The prompt to send to the LLM
            default_response: Default response to use if LLM call fails
            agent_type: Type of agent making the decision
            
        Returns:
            Dict containing the decision
        """
        print("      Making LLM call...")
        start_time = time.time()
        
        # Get appropriate system prompt and parser based on agent type
        system_prompt = ""
        parser = None
        if agent_type == "consumer":
            system_prompt = CONSUMER_PROMPT
            parser = self.consumer_parser
        elif agent_type == "prosumer":
            system_prompt = PROSUMER_PROMPT
            parser = self.prosumer_parser
        elif agent_type == "producer":
            system_prompt = PRODUCER_PROMPT
            parser = self.producer_parser
        elif agent_type == "utility":
            system_prompt = UTILITY_PROMPT
            parser = self.utility_parser
        elif agent_type == "regulator":
            system_prompt = REGULATOR_PROMPT
            parser = self.regulator_parser
            
        # Add format instructions to system prompt
        system_prompt += f"\n\n{parser.get_format_instructions()}"
            
        # Combine system prompt with task prompt
        full_prompt = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=prompt)
        ]
        
        try:
            response = self.llm.invoke(full_prompt)
            print(f"      LLM call completed in {time.time() - start_time:.2f}s")
            
            # Parse the response
            try:
                decision = parser.parse(response.content)
                return decision
            except Exception as e:
                print(f"      Failed to validate LLM response: {str(e)}")
                print(f"      Raw response: {response.content}")
                print("      Using default response")
                return default_response
                
        except Exception as e:
            print(f"      LLM call failed after {time.time() - start_time:.2f}s: {str(e)}")
            print("      Using default response")
            return default_response
        
    def get_consumer_decision(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Get consumer decision about energy purchases.
        
        Args:
            state: Current state of the consumer agent
            
        Returns:
            Dict containing decision details
        """
        default_response = ConsumerDecision(
            best_offer=None,
            best_score=-1
        )
        
        prompt = f"""Given your current state:

{self._format_state_for_prompt(state)}

Among all available offers, choose the best offer and score it on a scale of 0 to 100.

Respond with a JSON object containing:
- "best_offer": The best offer (with seller_id, amount, price, is_renewable)
- "best_score": The score of the best offer

Example response:
{{
    "best_offer": {{"seller_id": "utility1", "amount": 100.0, "price": 120.0, "is_renewable": true}},
    "best_score": 85
}}
"""
        return self._safe_llm_call(prompt, default_response, "consumer")
        
    def get_prosumer_decision(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Get prosumer decision about energy production and sales.
        
        Args:
            state: Current state of the prosumer agent
            
        Returns:
            Dict containing decision details
        """
        default_response = ProsumerDecision(
            sell_amount=0.0,
            selling_price=state.get("selling_price", 100),
            use_storage=0.0,
            store_amount=state.get("current_production", 0),
            consider_upgrade=False
        )
        
        prompt = f"""Given your current state:

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
{{
    "sell_amount": 50.0,
    "selling_price": 90.0,
    "use_storage": 20.0,
    "store_amount": 30.0,
    "consider_upgrade": false
}}
"""
        return self._safe_llm_call(prompt, default_response, "prosumer")
        
    def get_producer_decision(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Get producer decision about energy production and pricing.
        
        Args:
            state: Current state of the producer agent
            
        Returns:
            Dict containing decision details
        """
        default_response = ProducerDecision(
            production_level=state.get("max_capacity", 0) * 0.8,
            price=state.get("current_price", 100),
            accept_contracts=True,
            min_contract_duration=30,
            consider_upgrade=False
        )
        
        prompt = f"""Given your current state:

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
{{
    "production_level": 800.0,
    "price": 95.0,
    "accept_contracts": true,
    "min_contract_duration": 30,
    "consider_upgrade": true
}}
"""
        return self._safe_llm_call(prompt, default_response, "producer")
        
    def get_utility_decision(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Get utility decision about energy procurement and pricing.
        
        Args:
            state: Current state of the utility agent
            
        Returns:
            Dict containing decision details
        """
        default_response = UtilityDecision(
            target_contracts=1,
            max_purchase_price=state.get("current_buying_price", 80),
            selling_price=state.get("current_selling_price", 100),
            renewable_target=state.get("renewable_quota", 0.2),
            storage_strategy="maintain"
        )
        
        prompt = f"""Given your current state:

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
{{
    "target_contracts": 3,
    "max_purchase_price": 85.0,
    "selling_price": 110.0,
    "renewable_target": 0.25,
    "storage_strategy": "increase"
}}
"""
        return self._safe_llm_call(prompt, default_response, "utility")
        
    def get_regulator_decision(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Get regulator decision about market intervention.
        
        Args:
            state: Current state of the regulator agent
            
        Returns:
            Dict containing decision details
        """
        default_response = RegulatorDecision(
            adjust_carbon_tax=0.0,
            price_intervention=False,
            max_price_increase=state.get("max_price_increase", 0.2),
            enforce_renewable_quota=True,
            issue_warnings=[]
        )
        
        prompt = f"""Given your current state:

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
{{
    "adjust_carbon_tax": 5.0,
    "price_intervention": true,
    "max_price_increase": 0.15,
    "enforce_renewable_quota": true,
    "issue_warnings": ["price_gouging", "market_concentration"]
}}
"""
        return self._safe_llm_call(prompt, default_response, "regulator") 