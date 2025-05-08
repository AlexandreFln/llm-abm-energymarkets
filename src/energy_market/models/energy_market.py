from typing import Dict, Any, List, Optional
import numpy as np
from mesa import Model
from mesa.time import RandomActivation
from mesa.datacollection import DataCollector
import asyncio

from src.energy_market.agents.base import EnergyMarketAgent
from src.energy_market.agents.consumer import ConsumerAgent
from src.energy_market.agents.prosumer import ProsumerAgent
from src.energy_market.agents.producer import EnergyProducerAgent
from src.energy_market.agents.utility import UtilityAgent
from src.energy_market.agents.regulator import RegulatorAgent

from src.energy_market import constants as C

class EnergyMarketModel(Model):
    """Energy market model with multiple agent types."""
    
    def __init__(self,
                 num_consumers: int = 100,
                 num_prosumers: int = 20,
                 num_producers: int = 10,
                 num_utilities: int = 5,
                 initial_price: float = 100.0,
                 carbon_tax_rate: float = 10.0,):
        """Initialize energy market model.
        
        Args:
            num_consumers: Number of consumer agents
            num_prosumers: Number of prosumer agents
            num_producers: Number of producer agents
            num_utilities: Number of utility agents
            initial_price: Initial energy price
            carbon_tax_rate: Tax rate for carbon emissions
        """
        super().__init__()
        
        # Market parameters
        self.num_consumers = num_consumers
        self.num_prosumers = num_prosumers
        self.num_producers = num_producers
        self.num_utilities = num_utilities
        self.initial_price = initial_price
        self.carbon_tax_rate = carbon_tax_rate
        self.personas = C.PERSONAS
        
        # Initialize schedule
        self.schedule = RandomActivation(self)
        
        # Initialize agent storage
        self.market_agents: Dict[str, Dict[str, Any]] = {
            'consumers': {},
            'prosumers': {},
            'producers': {},
            'utilities': {},
            'regulator': None
        }
        
        self._create_agents()
        
        # Helper functions for safe division
        def safe_division(numerator, denominator, default=0.0):
            return numerator / denominator if denominator != 0 else default
            
        def get_buy_transactions(agent):
            return [t for t in agent.transaction_history if t['type'] == 'buy']
            
        def get_sell_transactions(agent):
            return [t for t in agent.transaction_history if t['type'] == 'sell']
            
        def sum_transaction_values(transactions):
            return sum(t['total_value'] for t in transactions)
            
        def sum_transaction_amounts(transactions):
            return sum(t['amount'] for t in transactions)
        
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
                "Persona": "persona",
                "Resources": "resources",
                "Profit": "profit",
                "Transaction_History": "transaction_history",
                "Transaction_Summary": EnergyMarketAgent.get_transaction_summary,
            },
            agenttype_reporters={
                ConsumerAgent: {
                    'Energy_Consumption': lambda c: c.current_consumption,
                    'Energy_Cost': lambda c: sum(t['total_value'] for t in get_buy_transactions(c)
                                                 if t['timestamp'] == c.model._steps
                                                 ),
                },
                ProsumerAgent: {
                    'Production_Type': 'production_type',
                    'Energy_Consumption': lambda p: p.current_consumption,
                    'Energy_Cost': lambda p: sum_transaction_values(get_buy_transactions(p)),
                    'Energy_Production': lambda p: p.current_production,
                    'Revenues': lambda p: sum(t['total_value'] for t in get_sell_transactions(p)
                                              if t['timestamp'] == p.model._steps),
                    'Capacity_Utilization': lambda p: safe_division(
                        p.current_production, 
                        p.max_production_capacity
                    ),
                },
                EnergyProducerAgent: {
                    'Production_Type': 'production_type',
                    'Market_Share': lambda p: safe_division(
                        sum(t['amount'] for t in get_sell_transactions(p) if t['timestamp'] == p.model._steps),
                        p.model.get_market_state()['total_demand']
                    ),
                    'Energy_Volume_Produced': lambda p: p.current_production,
                    'Energy_Volume_Sold': lambda p: sum(t['amount'] for t in get_sell_transactions(p)
                                                        if t['timestamp'] == p.model._steps
                                                        ),
                    'Revenues': lambda p: sum(t['total_value'] for t in get_sell_transactions(p)
                                              if t['timestamp'] == p.model._steps
                                              ),
                    'Operational_Margin': lambda p: 1 - safe_division(
                        p.base_production_cost,
                        p.current_price,
                        default=1
                    ),
                    'Operational_Costs': lambda p: sum(t['price'] for t in p.transaction_history if t['type'] == 'cost'),
                    'Capacity_Utilization': lambda p: safe_division(
                        p.current_production,
                        p.max_production_capacity
                    ),
                },
                UtilityAgent: {
                    'Profit_Margin': lambda u: 1 - safe_division(
                        sum(t['total_value'] for t in get_buy_transactions(u) if t['timestamp'] == u.model._steps),
                        sum(t['total_value'] for t in get_sell_transactions(u) if t['timestamp'] == u.model._steps),
                        default=1
                    ),
                    'Energy_Procured': lambda u: sum(t['amount'] for t in get_buy_transactions(u)
                                                     if t['timestamp'] == u.model._steps
                                                     ),
                    'Renewable_Energy_Procured_(%)': lambda u: safe_division(
                        sum(t['amount'] for t in get_buy_transactions(u) if (t['is_renewable']) & (t['timestamp'] == u.model._steps)),
                        sum(t['amount'] for t in get_buy_transactions(u) if t['timestamp'] == u.model._steps),
                        ),
                    'Energy_Procurement_Costs': lambda u: sum(t['total_value'] for t in get_buy_transactions(u)
                                                              if t['timestamp'] == u.model._steps
                                                              ),
                    'Revenues': lambda u: sum(t['total_value'] for t in get_sell_transactions(u)
                                              if t['timestamp'] == u.model._steps
                                              ),
                    'Energy_Distributed': lambda u: sum(t['amount'] for t in get_sell_transactions(u)
                                                        if t['timestamp'] == u.model._steps
                                                        ),
                },
                RegulatorAgent: {
                    'Nb_Price_Intervention': lambda r: len([v for v in r.violations['price_gouging'] if v['time'] == r.model._steps]),
                    'Nb_Oligopoly_Intervention': lambda r: len([v for v in r.violations['market_concentration'] if v['time'] == r.model._steps]),
                    'Nb_Renewable_Intervention': lambda r: len([v for v in r.violations['renewable_quota'] if v['time'] == r.model._steps]),
                },
            },
        )
        
    def _create_agents(self) -> None:
        """Create all agents in the model."""
        # Create consumers
        for i in range(self.num_consumers):
            agent = ConsumerAgent(
                unique_id=f"consumer_{i}",
                model=self,
                persona="eco_friendly",  #str(np.random.choice(C.PERSONAS)[0]),
                initial_resources=np.random.randint(1000, 2000),
                energy_needs=np.random.randint(80, 150),
                renewable_preference=np.random.rand()
            )
            self.schedule.add(agent)
            self.market_agents['consumers'][agent.unique_id] = agent
            
        # Create prosumers
        for i in range(self.num_prosumers):
            agent = ProsumerAgent(
                unique_id=f"prosumer_{i}",
                model=self,
                persona="eco_friendly", #str(np.random.choice(C.PERSONAS)[0]),
                production_type="solar",  # or randomly choose between solar/wind
                initial_resources=np.random.randint(1000, 2000),
                energy_needs=np.random.randint(80, 150),
                max_production_capacity=np.random.randint(50, 100),
                storage_capacity=np.random.randint(10, 50),
                green_energy_preference=np.random.rand()
            )
            self.schedule.add(agent)
            self.market_agents['prosumers'][agent.unique_id] = agent

        # Create producers
        for i in range(self.num_producers):
            agent = EnergyProducerAgent(
                unique_id=f"producer_{i}",
                model=self,
                persona=str(np.random.choice(C.PERSONAS, 1)[0]),
                production_type='oil',  #np.random.choice(C.PRODUCTION_TYPES),
                initial_resources=np.random.randint(20000, 50000),
                max_production_capacity=np.random.randint(500, 1000),
                base_production_cost=np.random.randint(20, 50),
                maintenance_cost_rate=0.02,
                upgrade_cost=5000.0,
                upgrade_capacity_increase=2000.0,
                min_profit_margin=0.15
            )
            self.schedule.add(agent)
            self.market_agents['producers'][agent.unique_id] = agent

        # Create utilities
        for i in range(self.num_utilities):
            agent = UtilityAgent(
                unique_id=f"utility_{i}",
                model=self,
                persona="eco_friendly", #str(np.random.choice(C.PERSONAS, 1)[0]),
                initial_resources=np.random.randint(20000, 50000),
                renewable_quota=0.4*np.random.random(),
                min_profit_margin=0.1,
                storage_capacity=np.random.randint(400, 1500),
                contract_duration=np.random.randint(2, 6),
            )
            self.schedule.add(agent)
            self.market_agents['utilities'][agent.unique_id] = agent
            
        # Create regulator
        regulator = RegulatorAgent(
            unique_id="regulator",
            model=self,
            persona="eco_friendly",
            base_carbon_tax=self.carbon_tax_rate
        )
        self.schedule.add(regulator)
        self.market_agents['regulator'] = regulator
        
        # Connect consumers and producers to utilities
        consumers = [agent for agent in self.schedule.agents if isinstance(agent, ConsumerAgent)]   #Integrates also ProsumerAgents
        producers = [agent for agent in self.schedule.agents if isinstance(agent, EnergyProducerAgent)]
        utilities = [agent for agent in self.schedule.agents if isinstance(agent, UtilityAgent)]
        
        # First, connect consumers to utilities
        for consumer in consumers:
            # Randomly assign consumer to a utility
            utility = np.random.choice(utilities)
            utility.customer_base[consumer.unique_id] = {
                'id': consumer.unique_id,
                'avg_consumption': consumer.energy_needs,
                'amount': consumer.energy_needs, 
                'last_purchase': 0,
                'is_renewable': utility.renewable_quota > 0.5,
            }
        
        # Then, establish initial contracts between utilities and producers
        for utility in utilities:
            # Calculate utility's total energy needs from its customer base
            total_energy_needs = sum(
                customer['amount']
                for customer in utility.customer_base.values()
            )
            # Calculate how much energy we need to contract for
            remaining_needs = total_energy_needs
            # Try to contract with multiple producers until needs are met
            while remaining_needs > 0 and producers:
                # Select a random producer that hasn't been contracted with yet
                available_producers = [
                    p for p in producers 
                    if p.unique_id not in utility.producer_contracts
                ]
                if not available_producers:
                    break   
                producer = np.random.choice(available_producers)
                # Calculate how much capacity the producer has available
                contracted_capacity = sum(
                    contract.get('amount', 0) 
                    for contract in producer.utility_contracts.values()
                )
                available_capacity = producer.max_production_capacity - contracted_capacity
                if available_capacity <= 0:
                    continue
                # Calculate contract amount (up to remaining needs or available capacity)
                contract_amount = min(remaining_needs, available_capacity)
                
                # Create initial contract
                price = producer.base_production_cost * (1 + 2*producer.min_profit_margin)
                utility.record_transaction('buy', contract_amount, price, producer.unique_id)
                
                # Update remaining needs
                remaining_needs -= contract_amount
                
                # If producer is fully contracted, remove from available producers
                if contracted_capacity + contract_amount >= producer.max_production_capacity:
                    producers.remove(producer)

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
            sum(c.get('amount', 0) for c in utility.producer_contracts.values() if c['remaining_duration'] > 0)
            for utility in self.market_agents['utilities'].values()
        )
        total_demand = sum(
            consumer.energy_needs
            for consumer in self.market_agents['consumers'].values()
        ) + sum(
            prosumer.energy_needs
            for prosumer in self.market_agents['prosumers'].values()
        )
        # Calculate average prices
        utility_prices = [
            utility.current_selling_price
            for utility in self.market_agents['utilities'].values()
        ]
        producer_prices = [
            producer.current_selling_price
            for producer in self.market_agents['producers'].values()
        ]
        avg_price = np.mean(utility_prices) if utility_prices else self.initial_price

        avg_spot_price = np.mean(producer_prices) if producer_prices else self.initial_price
        
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
        energy_stored = sum(utility.energy_stored for utility in self.market_agents['utilities'].values())
        # Calculate market concentration using Herfindahl-Hirschman Index (HHI)
        total_capacity = sum(
            [producer.max_production_capacity
             for producer in self.market_agents['producers'].values()]
            +
            [prosumer.max_production_capacity
             for prosumer in self.market_agents['prosumers'].values()]
        )
        market_shares = [
            (producer.max_production_capacity / total_capacity) ** 2
            for producer in self.market_agents['producers'].values()
        ] if total_capacity > 0 else []
        market_concentration = sum(market_shares)
        
        # Get available producers for contracting
        available_producers = {
            producer.unique_id: {
                'capacity': producer.max_production_capacity,
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
            'total_production': total_production,
            'total_energy_stored': energy_stored,
            'average_price': avg_price,
            'average_spot_price': avg_spot_price,  # Spot market premium
            'renewable_ratio': renewable_ratio,
            'market_concentration': market_concentration,
            'carbon_tax_rate': self.get_carbon_tax_rate(),
            'total_capacity': total_capacity,
            'available_producers': available_producers,
            'producers': {
                p.unique_id: {
                    'capacity': p.max_production_capacity,
                    'price': p.current_price,
                    'production': p.current_production,
                    'is_renewable': p.is_renewable()
                }
                for p in self.market_agents['producers'].values()
            },
            'utilities': {
                u.unique_id: {
                    'selling_price': u.current_selling_price,
                    'renewable_ratio': sum(
                        1 for c in u.producer_contracts.values()
                        if c['is_renewable']
                    ) / len(u.producer_contracts) if u.producer_contracts else 0,
                    'energy_supply': sum(p['amount'] for p in u.producer_contracts.values() if p['accepted']),
                    'energy_demand': sum(c['amount'] for c in u.customer_base.values()),
                }
                for u in self.market_agents['utilities'].values()
            },
            'offers': offers
        }
        
    async def step_async(self) -> None:
        """Execute one step of the model with parallel agent execution."""
        # Run all agent step tasks concurrently
        print("\nExecuting model step asyncronously...")

        # Update market state
        market_state = self.get_market_state()
        print(f"  Market state: Price={market_state['average_price']:.2f}, Supply={market_state['total_supply']:.2f}, Demand={market_state['total_demand']:.2f}, Production={market_state['total_production']:.2f}, Energy Stored={market_state['total_energy_stored']:.2f}")
        
        # Store initial resources for each agent
        initial_resources = {agent.unique_id: agent.resources for agent in self.schedule.agents}
        
        # Create and gather all tasks
        tasks = [agent.step_async() for agent in self.schedule.agents]
        await asyncio.gather(*tasks)
        
        # Calculate profit after all tasks are completed
        for agent in self.schedule.agents:
            profit = agent.resources - initial_resources[agent.unique_id]
            agent.profit += profit
            print(f"    {agent.unique_id} made a profit of {profit}")
        
        # Collect data
        print("  Collecting data...")
        self.datacollector.collect(self)
        
        # Advance the schedule
        self.schedule.step()
        
        print("  Async step complete.\n") 
        
    def get_available_offers(self) -> List[Dict[str, Any]]:
        """Get all available energy offers from utilities and prosumers.
        
        Returns:
            List of available offers
        """
        offers = []
        
        for agent in self.schedule.agents:
            if isinstance(agent, ProsumerAgent):
                price = self.initial_price * (1 + 0.2 * np.random.random())
                amount = max(0, agent.current_production - agent.energy_needs)
                is_renewable = agent.production_type in ["solar", "wind", "hydro"]
            elif isinstance(agent, UtilityAgent):
                price = agent.current_selling_price
                contracts = agent.producer_contracts.values()
                amount = sum(contract['amount'] for contract in contracts if contract['accepted'] & (contract['duration']>0))
                if len(contracts) > 0:
                    is_renewable = (
                        sum(
                            contract.get('is_renewable', False) for contract in contracts if contract['accepted']
                            ) / len(contracts)) > 2/3
                else:
                    is_renewable = False
            else:
                continue

            offers.append({
                'seller_id': agent.unique_id,
                'amount': amount,
                'price': price,
                'is_renewable': is_renewable,
            })
            
        return offers