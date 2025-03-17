# llm-abm-energymarkets
A research repository on LLM-powered Agent-Based Modeling (ABM) for energy markets


# Phase 1: Research & Setup

## ✅ Define System Scope
Objective: Define the model scope, set up the development environment, and prepare data sources.
### Identify agent types

All agents have one goal which is to maximise their profit.

- **Consumer**:
    - Type: None
    - Attributes: persona, initial resources, energy mix, energy needs, buying price (from prosumers), distance from grid ?
    - Actions: do nothing, buy from utility, buy from local grid (prosumer)
<br> 
<br>

- **Prosumer (inherited from Consumer)**: consumer that also produces energy locally and can either sell it on the grid or use it for its personnal consumption 
    - Type: photovoltaic (PV), wind, other
    - Attributes: inherited from consumers, production level, max capacity of production, electricity storage level, selling price
    - Objects: maintainance rate of the PV, lifetime of the PV
    - Actions: inherited from consumer, change sell price on the local grid, change volume sold on the local grid, disconnect from local grid
<br> 
<br>

- **Energy producer**: generate energy and determine their production levels, facility upgrades, and pricing strategies
    - Type: oil, renewables
    - State: connected energy suppliers/utilities
    - Attributes: persona, initial resources, volume of production, max production capacity, production costs, price to sell energy to utility
    - Actions: change price to sell energy to utility, invest money to upgrade facility max capacity
<br> 
<br>

- **Energy utility**: purchase energy from producers and sell it to consumers
    - Type: eco-friendly, balanced, greedy
    - Attributes: persona, initial resources, selling price to consumer, volume of energy to deal, regulatory constraint (% of renewable to buy)
    - Actions: change price to sell energy to consumer, select energy supplier company, risk hedging by negotiating future contracts
<br> 
<br>

- ***Regulators***: dynamic regulation in reaction to market failures
    - Type: None
    - Attributes: persona
    - Actions: Penalties & incentives (fines on price gouging or reward green energy investments)


---

### Define market dynamics:

- Scenario 1: 
    -   Auction-based energy exchange for local grid
    -   Contracts with secured price for utility supplier
- Scenario 2: 
    - Auction-based trading for everything


---

### Select LLM use cases: 

- Consumer:
    - Decides wether to buy energy from utility or from the grid
    - Decides from which utility / grid node buy energy

- Prosumer (inherited from Consumer):
    - Decides wether to sell or consume energy produced

- Energy producer:
    - Determines energy production levels and selling prices
    - Decides whether to upgrade facilities to increase production limits (considering the associated costs)


- Utility:
    - Decides energy purchase amounts and consumer pricing to meet consumer demand
    - Randomly assigned one of three personas: [environmentally conscious, greedy, depressed]

- *Regulator*:
    - Decides wether to impose a policy to regulate the market