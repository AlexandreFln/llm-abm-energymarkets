from typing import Dict, Any, List
import json
import time
import asyncio
from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
from langchain.output_parsers import PydanticOutputParser
from src.energy_market.prompts.system_prompts import (
    CONSUMER_PROMPT,
    PROSUMER_PROMPT,
    PRODUCER_PROMPT,
    UTILITY_PROMPT,
    REGULATOR_PROMPT
)
from src.energy_market.schemas.llm_decisions import (
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
                #  timeout: float = 5.0,
                 ):
        """Initialize LLM decision maker.
        
        Args:
            model_name: Name of the Ollama model to use
            timeout: Timeout in seconds for LLM calls
        """
        self.llm = ChatOllama(
            model=model_name,
            temperature=0.8,
            # timeout=timeout,
        )
        
        # Initialize output parsers for each agent type
        self.consumer_parser = PydanticOutputParser(pydantic_object=ConsumerDecision)
        self.prosumer_parser = PydanticOutputParser(pydantic_object=ProsumerDecision)
        self.producer_parser = PydanticOutputParser(pydantic_object=ProducerDecision)
        self.utility_parser = PydanticOutputParser(pydantic_object=UtilityDecision)
        self.regulator_parser = PydanticOutputParser(pydantic_object=RegulatorDecision)
        
        # Create a semaphore to limit concurrent LLM calls
        self.semaphore = asyncio.Semaphore(30)  # Limit to 15 concurrent calls
        
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
        
    async def _safe_llm_call_async(self, prompt: str, default_response: Dict[str, Any], 
                                  agent_type: str = None) -> Dict[str, Any]:
        """Make an asynchronous LLM call with error handling and timeout.
        
        Args:
            prompt: The prompt to send to the LLM
            default_response: Default response to use if LLM call fails
            agent_type: Type of agent making the decision
            
        Returns:
            Dict containing the decision
        """
        print(f"      Making LLM call for {agent_type}...")
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
        
        # Use semaphore to limit concurrent calls
        async with self.semaphore:
            try:
                # Run LLM call in a thread pool to avoid blocking
                response = await asyncio.to_thread(self.llm.invoke, full_prompt)
                print(f"      LLM call for {agent_type} completed in {time.time() - start_time:.2f}s")
                
                # Parse the response
                try:
                    decision = parser.parse(response.content)
                    return decision
                except Exception as e:
                    print(f"      Failed to validate LLM response for {agent_type}: {str(e)}")
                    print(f"      Raw response: {response.content}")
                    print(f"      Using default response: {default_response}")
                    return default_response
                    
            except Exception as e:
                print(f"      LLM call for {agent_type} failed after {time.time() - start_time:.2f}s: {str(e)}")
                print(f"      Using default response: {default_response}")
                return default_response
    
        
    async def get_consumer_decision_async(self,
                                          state: Dict[str, Any],
                                          available_offers: List[Dict[str, Any]],
                                          ) -> Dict[str, Any]:
        """Get consumer decision about energy purchases asynchronously.
        
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
<current_state>
{self._format_state_for_prompt(state)}
</current_state>

Choose the best offer among the followings and score it on a scale of 0 to 100:
{available_offers}
"""
        return await self._safe_llm_call_async(prompt, default_response, "consumer")
        
    async def get_prosumer_decision_async(self, state: Dict[str, Any], market_state: Dict[str, Any]) -> Dict[str, Any]:
        """Get prosumer decision about energy production and sales asynchronously.
        
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
        
        prompt = f"""Decide how to manage your energy usage, production and storage given the following informations::
-Your current state:
<current_state>
{self._format_state_for_prompt(state)}
</current_state>

-Market state:
<market_state>
{self._format_state_for_prompt(market_state)}
</market_state>
"""
        return await self._safe_llm_call_async(prompt, default_response, "prosumer")
        
    async def get_producer_decision_async(self, state: Dict[str, Any], market_state: Dict[str, Any]) -> Dict[str, Any]:
        """Get producer decision about energy production and pricing asynchronously.
        
        Args:
            state: Current state of the producer agent
            
        Returns:
            Dict containing decision details
        """
        default_response = ProducerDecision(
            production_level=state.get("max_production_capacity", 0) * 0.8,
            price=state.get("current_price", 100),
            accept_contracts=True,
            min_contract_duration=3,
            consider_upgrade=False
        )
        
        prompt = f"""Decide on your production and pricing strategy given the following informations::
-Your current state:
<current_state>
{self._format_state_for_prompt(state)}
</current_state>

-Market state:
<market_state>
{self._format_state_for_prompt(market_state)}
</market_state>
"""
        return await self._safe_llm_call_async(prompt, default_response, "producer")
        
    async def get_utility_decision_async(self, state: Dict[str, Any], market_state: Dict[str, Any]) -> Dict[str, Any]:
        """Get utility decision about energy procurement and pricing asynchronously.
        
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
        
        prompt = f"""Decide on your market strategy given the following informations:
-Your current state:
<current_state>
{self._format_state_for_prompt(state)}
</current_state>

-Market state:
<market_state>
{self._format_state_for_prompt(market_state)}
</market_state>
"""
        return await self._safe_llm_call_async(prompt, default_response, "utility")
        
    async def get_regulator_decision_async(self, state: Dict[str, Any], market_state: Dict[str, Any]) -> Dict[str, Any]:
        """Get regulator decision about market intervention asynchronously.
        
        Args:
            state: Current state of the regulator agent
            
        Returns:
            Dict containing decision details
        """
        default_response = RegulatorDecision(
            adjust_carbon_tax=0.0,
            max_price_increase=state.get("max_price_increase", 0.2),
            enforce_renewable_quota=False,
        )
        
        prompt = f"""Decide on regulatory actions given the following informations:
-Your current state and past informations on high level state of the market :
<current_state_and_past_market>
{self._format_state_for_prompt(state)}
</current_state_and_past_market>

-Current market state:
<current_market_state>
{self._format_state_for_prompt(market_state)}
</current_market_state>
"""
        return await self._safe_llm_call_async(prompt, default_response, "regulator") 