from typing import Dict, Any, List, Optional
import numpy as np
from mesa import Model
from mesa.time import RandomActivation, SimultaneousActivation
from mesa.datacollection import DataCollector

from ..agents.consumer import ConsumerAgent
from ..agents.prosumer import ProsumerAgent
from ..agents.producer import EnergyProducerAgent
from ..agents.utility import UtilityAgent
from ..agents.regulator import RegulatorAgent

class EnergyMarketModel(Model):
    """Energy market model with multiple agent types."""
    
    def __init__(self,
                 num_consumers: int = 100,
                 num_prosumers: int = 20,
                 num_producers: int = 10,
                 num_utilities: int = 5,
                 initial_price: float = 100.0,
                 carbon_tax_rate: float = 10.0,
                 renewable_incentive: float = 5.0):
        """Initialize energy market model.
        
        Args:
            num_consumers: Number of consumer agents
            num_prosumers: Number of prosumer agents
            num_producers: Number of producer agents
            num_utilities: Number of utility agents
            initial_price: Initial energy price
            carbon_tax_rate: Tax rate for carbon emissions
            renewable_incentive: Incentive for renewable energy
        """
        super().__init__()
        
        # Market parameters
        self.num_consumers = num_consumers
        self.num_prosumers = num_prosumers
        self.num_producers = num_producers
        self.num_utilities = num_utilities
        self.initial_price = initial_price
        self.carbon_tax_rate = carbon_tax_rate
        self.renewable_incentive = renewable_incentive
        
        # Initialize schedule
        self.schedule = RandomActivation(self)
        # self.schedule = SimultaneousActivation(self)

        
        # Initialize agent storage
        self.market_agents: Dict[str, Dict[str, Any]] = {
            'consumers': {},
            'prosumers': {},
            'producers': {},
            'utilities': {},
            'regulator': None
        }
        
        self._create_agents()
        
        # Initialize data collection
        self.datacollector = DataCollector(
            model_reporters={
                "Average_Price": lambda m: self.get_market_state()['average_price'],
                "Total_Production": lambda m: self.get_market_state()['total_supply'],
                "Total_Demand": lambda m: self.get_market_state()['total_demand'],
                "Renewable_Ratio": lambda m: self.get_market_state()['renewable_ratio'],
                "Market_Concentration": lambda m: self.get_market_state()['market_concentration']
            },
            agent_reporters={
                "Resources": "resources",
                "Profit": "profit"
            }
        )
        
    def _create_agents(self) -> None:
        """Create and initialize all agents in the market."""
        # Create consumers
        for i in range(self.num_consumers):
            consumer = ConsumerAgent(
                unique_id=f"consumer_{i}",
                model=self,
                persona="default",
                initial_resources=np.random.uniform(500, 2000),
                energy_needs=np.random.uniform(50, 150)
            )
            self.schedule.add(consumer)
            self.market_agents['consumers'][consumer.unique_id] = consumer
            
        # Create prosumers
        production_types = ["solar", "wind"]
        for i in range(self.num_prosumers):
            prosumer = ProsumerAgent(
                unique_id=f"prosumer_{i}",
                model=self,
                persona="default",
                production_type=production_types[i % len(production_types)],
                initial_resources=np.random.uniform(2000, 5000),
                energy_needs=np.random.uniform(50, 150),
                max_production_capacity=np.random.uniform(100, 300)
            )
            self.schedule.add(prosumer)
            self.market_agents['prosumers'][prosumer.unique_id] = prosumer
            
        # Create producers
        production_types = ["oil", "gas", "coal", "nuclear", "solar", "wind", "hydro"]
        for i in range(self.num_producers):
            producer = EnergyProducerAgent(
                unique_id=f"producer_{i}",
                model=self,
                persona="default",
                production_type=production_types[i % len(production_types)],
                initial_resources=np.random.uniform(10000, 50000),
                max_capacity=np.random.uniform(500, 2000)
            )
            self.schedule.add(producer)
            self.market_agents['producers'][producer.unique_id] = producer
            
        # Create utilities
        personas = ["eco_friendly", "profit_driven", "balanced"]
        for i in range(self.num_utilities):
            utility = UtilityAgent(
                unique_id=f"utility_{i}",
                model=self,
                persona=personas[i % len(personas)],
                initial_resources=np.random.uniform(50000, 100000),
                renewable_quota=0.2 if personas[i % len(personas)] == "eco_friendly" else 0.1
            )
            self.schedule.add(utility)
            self.market_agents['utilities'][utility.unique_id] = utility
            
        # Create regulator
        regulator = RegulatorAgent(
            unique_id="regulator",
            model=self,
            base_carbon_tax=self.carbon_tax_rate
        )
        self.schedule.add(regulator)
        self.market_agents['regulator'] = regulator
        
    def get_agent(self, agent_id: str) -> Optional[Any]:
        """Get agent by ID.
        
        Args:
            agent_id: Unique identifier of the agent
            
        Returns:
            Agent instance or None if not found
        """
        for agent_type in self.market_agents.values():
            if isinstance(agent_type, dict):
                if agent_id in agent_type:
                    return agent_type[agent_id]
            elif isinstance(agent_type, RegulatorAgent) and agent_type.unique_id == agent_id:
                return agent_type
        return None
        
    def get_carbon_tax_rate(self) -> float:
        """Get current carbon tax rate."""
        if self.market_agents['regulator']:
            return self.market_agents['regulator'].current_carbon_tax
        return self.carbon_tax_rate
        
    def request_producer_contract(self,
                                producer_id: str,
                                utility_id: str,
                                amount: float,
                                duration: int) -> Dict[str, Any]:
        """Request a contract from a producer.
        
        Args:
            producer_id: ID of the producer
            utility_id: ID of the requesting utility
            amount: Amount of energy requested
            duration: Contract duration
            
        Returns:
            Dict containing contract terms
        """
        producer = self.get_agent(producer_id)
        if producer and isinstance(producer, EnergyProducerAgent):
            return producer.negotiate_contract(utility_id, amount, duration)
        return {'accepted': False, 'reason': 'Producer not found'}
        
    def get_market_state(self) -> Dict[str, Any]:
        """Get current state of the market.
        
        Returns:
            Dict containing market metrics and state
        """
        # Calculate total supply and demand
        total_supply = sum(
            producer.current_production
            for producer in self.market_agents['producers'].values()
        )
        total_demand = sum(
            consumer.energy_needs
            for consumer in self.market_agents['consumers'].values()
        ) + sum(
            prosumer.energy_needs
            for prosumer in self.market_agents['prosumers'].values()
        )
        
        # Calculate average prices
        producer_prices = [
            producer.current_price
            for producer in self.market_agents['producers'].values()
        ]
        utility_prices = [
            utility.current_selling_price
            for utility in self.market_agents['utilities'].values()
        ]
        avg_price = np.mean(producer_prices + utility_prices) if producer_prices or utility_prices else self.initial_price
        
        # Calculate renewable ratio
        total_production = sum(
            producer.current_production
            for producer in self.market_agents['producers'].values()
        )
        renewable_production = sum(
            producer.current_production
            for producer in self.market_agents['producers'].values()
            if producer.is_renewable()
        )
        renewable_ratio = (
            renewable_production / total_production if total_production > 0 else 0
        )
        
        # Calculate market concentration using Herfindahl-Hirschman Index (HHI)
        total_capacity = sum(
            producer.max_capacity
            for producer in self.market_agents['producers'].values()
        )
        market_shares = [
            (producer.max_capacity / total_capacity) ** 2
            for producer in self.market_agents['producers'].values()
        ] if total_capacity > 0 else []
        market_concentration = sum(market_shares)
        
        # Get available producers for contracting
        available_producers = {
            producer.unique_id: {
                'capacity': producer.max_capacity,
                'price': producer.current_price,
                'is_renewable': producer.is_renewable()
            }
            for producer in self.market_agents['producers'].values()
        }
        
        # Collect available offers from utilities and prosumers
        offers = []
        
        # Add utility offers
        for utility in self.market_agents['utilities'].values():
            offers.append({
                'seller_id': utility.unique_id,
                'seller_type': 'utility',
                'price': utility.current_selling_price,
                'amount': sum(c['amount'] for c in utility.producer_contracts.values()) if hasattr(utility, 'producer_contracts') else 0,
                'is_renewable': utility.renewable_quota > 0.5,  # Utilities mix different sources
            })
        
        # Add prosumer offers
        for prosumer in self.market_agents['prosumers'].values():
            if prosumer.energy_stored > 0 or prosumer.current_production > prosumer.energy_needs:
                offers.append({
                    'seller_id': prosumer.unique_id,
                    'seller_type': 'prosumer',
                    'price': prosumer.selling_price,
                    'amount': prosumer.energy_stored + max(0, prosumer.current_production - prosumer.energy_needs),
                    'is_renewable': True  # Prosumers use renewable sources
                })
        
        return {
            'total_supply': total_supply,
            'total_demand': total_demand,
            'average_price': avg_price,
            'spot_price': avg_price * 1.1,  # Spot market premium
            'renewable_ratio': renewable_ratio,
            'market_concentration': market_concentration,
            'carbon_tax_rate': self.get_carbon_tax_rate(),
            'total_capacity': total_capacity,
            'available_producers': available_producers,
            'producers': {
                p.unique_id: {
                    'capacity': p.max_capacity,
                    'price': p.current_price,
                    'production': p.current_production
                }
                for p in self.market_agents['producers'].values()
            },
            'utilities': {
                u.unique_id: {
                    'selling_price': u.current_selling_price,
                    'renewable_ratio': sum(
                        1 for c in u.producer_contracts.values()
                        if c['is_renewable']
                    ) / len(u.producer_contracts) if u.producer_contracts else 0
                }
                for u in self.market_agents['utilities'].values()
            },
            'offers': offers
        }
        
    def step(self) -> None:
        """Execute one step of the model."""
        print("\nExecuting model step...")
        
        # Update market state
        market_state = self.get_market_state()
        print(f"  Market state: Price={market_state['average_price']:.2f}, Supply={market_state['total_supply']:.2f}, Demand={market_state['total_demand']:.2f}")
        
        # Execute agent steps in random order
        print("  Executing agent steps:")
        for agent in self.schedule.agents:
            print(f"    - {agent.__class__.__name__} {agent.unique_id}")
            agent.step()
        
        # Collect data
        print("  Collecting data...")
        self.datacollector.collect(self)
        print("  Step complete.\n") 