from mesa import Agent, Model
from mesa.time import RandomActivation
from mesa.space import MultiGrid
from mesa.datacollection import DataCollector
import numpy as np

from mesa import Agent
import numpy as np

PRODUCER_TYPE = [
    "OilAndGas",
    "RenewableEnergy",]

UTILITY_PERSONA = [
    "environmentally conscious",
    "greedy",
    "depressed"    
]


class EnergyMarketAgent(Agent):
    """Base class for all agents in the energy market."""
    def __init__(self, unique_id, model, persona, initial_resources):
        super().__init__(unique_id, model)
        self.persona = persona
        self.resources = initial_resources
        self.profit = 0

    def step(self):
        pass

class ConsumerAgent(EnergyMarketAgent):
    """Consumer agent that purchases energy."""
    def __init__(self,
                 unique_id,
                 model,
                 persona,
                 initial_resources=50,
                 energy_needs=5,
                 ):
        super().__init__(unique_id, model, persona, initial_resources)
        # Initialize parameters for consumer
        self.energy_needs: int = energy_needs
    
    def step(self):
        # Decision making for buying energy
        self.decide_energy_source()

    def decide_energy_source(self):
        """LLM decision tio do nothing, buy from main grid or buy from local grid."""
        # TODO: Implement LLM-based decision making for energy source selection
        print("I am consumer agent number: ", np.random.uniform(1, 1000))
        pass

class ProsumerAgent(ConsumerAgent):
    """Prosumer agent that can both consume and produce energy."""
    def __init__(self,
                 unique_id,
                 model,
                 persona,
                 initial_resources=50,
                 energy_needs=5,
                 max_capacity=1,  # Maximum production capacity
                 capacity_upgrade_cost=200,  # Amount of capacity increase per upgrade
                 capacity_upgrade_amount=1,  # Amount of capacity increase per upgrade
                 max_energy_stored=2,
                 ):
        super().__init__(unique_id, model, persona, initial_resources, energy_needs)
        # Initialize parameters for prosumer
        self.production = 0
        self.max_capacity = max_capacity 
        self.energy_stored = 0
        self.max_energy_stored = max_energy_stored
        self.energy_price = 0  # Price of energy sold on local grid
        self.capacity_upgrade_cost=capacity_upgrade_cost
        self.capacity_upgrade_amount=capacity_upgrade_amount
        
    def step(self):
        # super().step()
        self.decide_production_allocation()

    def decide_production_allocation(self, *args, **kwargs):
        """LLM decision local grid strategy."""
        # TODO: Implement LLM-based decision making for production allocation
        print("I am prosumer agent number: ", np.random.uniform(1, 1000))
        pass

class EnergyProducerAgent(EnergyMarketAgent):
    """Energy producer agent that generates and sells energy."""
    def __init__(self, 
                 unique_id,
                 model,
                 persona,
                 production_type,
                 initial_resources=1000, # Starting production level
                 production=100, # Starting production level
                 energy_price=50, # Price of energy for producers
                 production_cost=30,  # Base cost of production
                 max_capacity = 300,  # Maximum production capacity
                 capacity_upgrade_cost = 50000,  # Cost to upgrade capacity by capacity_upgrade_amount
                 capacity_upgrade_amount = 30,  # Amount of capacity increase per upgrade
                 ):
        super().__init__(unique_id, model, persona, initial_resources)
        self.resources = 1000  # Starting resources
        self.production = production
        self.energy_price = energy_price # Price of energy for producers
        self.production_type = production_type if production_type else str(np.random.choice(PRODUCER_TYPE))
        # self.cost_to_consumer = 20 if company_type == "UtilityProvider" else None  # Cost to consumer for utility providers
        self.max_capacity = max_capacity
        self.production_cost = production_cost
        self.capacity_upgrade_cost = capacity_upgrade_cost
        self.capacity_upgrade_amount = capacity_upgrade_amount
        self.profit = 0
        self.connections = {}  # Supply chain connections
        self.unmet_demand = 0
        
    def step(self):
        self.determine_production_strategy()
        
    def determine_production_strategy(self):
        # TODO: Implement LLM-based decision making for production strategy
        print("I am production agent number: ", np.random.uniform(1, 1000))
        pass

class UtilityAgent(EnergyMarketAgent):
    """Utility agent that buys from producers and sells to consumers."""
    def __init__(self,
                 unique_id,
                 model,
                 persona,
                 utility_type,
                 renewable_quota=0,
                 initial_resources=1000,
                 energy_price=0,
                 cost_to_consumer=20,
                ):
        super().__init__(unique_id, model, persona, initial_resources)
        self.utility_type = utility_type if utility_type else str(np.random.choice(UTILITY_PERSONA))
        self.renewable_quota = renewable_quota
        self.energy_price = energy_price
        self.cost_to_consumer = cost_to_consumer
        self.energy_purchased = 0
        self.suppliers = {}  # {supplier_id: purchase_amount}
        
    def step(self):
        self.determine_market_strategy()
        
    def determine_market_strategy(self):
        # TODO: Implement LLM-based decision making for market strategy
        print("I am utility agent number: ", np.random.uniform(1, 1000))
        pass

class RegulatorAgent(EnergyMarketAgent):
    """Regulator agent that oversees market dynamics."""
    def __init__(self, unique_id, model, persona):
        super().__init__(unique_id, model, persona, float('inf'))

    def step(self):
        self.evaluate_market_conditions()
        
    def evaluate_market_conditions(self):
        # TODO: Implement LLM-based decision making for market regulation
        print("I am regulator agent number: ", np.random.uniform(1, 1000))
        pass

from mesa import Model
from mesa.space import MultiGrid
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector

class EnergyMarketModel(Model):
    """Energy market model with multiple agent types."""
    def __init__(self, 
                 num_consumers=4,
                 num_prosumers=2,
                 num_producers=2,
                 num_utilities=2,
                 width=20, 
                 height=20):
        super().__init__()
        self.num_consumers = num_consumers
        self.num_prosumers = num_prosumers
        self.num_producers = num_producers
        self.num_utilities = num_utilities
        
        # self.grid = MultiGrid(width, height, True)
        self.schedule = RandomActivation(self)
        
        # Create agents
        self.create_agents()
        
        # Data collection
        self.datacollector = DataCollector(
            model_reporters={
                "Average_Price": lambda m: np.mean([a.energy_price for a in m.schedule.agents 
                                                  if isinstance(a, (ProsumerAgent, EnergyProducerAgent, UtilityAgent))]),
                "Total_Production": lambda m: sum([a.production for a in m.schedule.agents 
                                                 if isinstance(a, (ProsumerAgent, EnergyProducerAgent))])
            },
            agent_reporters={
                "Profit": "profit",
                "Resources": "resources"
            }
        )
    
    def create_agents(self):
        # Create consumers
        consumers = []
        for i in range(self.num_consumers):
            consumer = ConsumerAgent(
                unique_id=f"consumer_{i}", 
                model=self, 
                persona="default",
                # initial_resources=1000,
                # energy_needs=200,
                )
            self.schedule.add(consumer)
            consumers.append(consumer)
            
        # Create prosumers
        for i in range(self.num_prosumers):
            prosumer = ProsumerAgent(unique_id=f"prosumer_{i}", 
                                model=self, 
                              persona="default",
                            #   initial_resources=1000,
                            #   energy_needs=200,
                            #   max_capacity=np.random.uniform(100, 300)
                            )
            self.schedule.add(prosumer)
            
        # Create producers
        for i in range(self.num_producers):
            producer = EnergyProducerAgent(f"producer_{i}", self,
                                    persona="default",
                                    # initial_resources=10000,
                                    production_type="renewable" if i % 2 == 0 else "fossil",
                                    # max_capacity=(self.num_prosumers+self.num_consumers)*100,
                                    # production_costs=10 if i % 2 == 0 else 8,
                                    # energy_price=100,
            )
            self.schedule.add(producer)
            
        # Create utilities
        utility_types = ["eco-friendly", "balanced", "greedy"]
        for i in range(self.num_utilities):
            utility = UtilityAgent(f"utility_{i}", self,
                            persona="default",
                            # initial_resources=50000,
                            utility_type=utility_types[i % len(utility_types)],
                            )
            self.schedule.add(utility)
            
        # Create regulator
        # regulator = RegulatorAgent("regulator", self, persona="neutral")
        # self.schedule.add(regulator)
    
    def step(self):
        self.datacollector.collect(self)
        self.schedule.step() 