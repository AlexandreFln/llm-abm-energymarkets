# LLM-Powered Energy Market Simulation

The global transition to sustainable energy systems is one of the most pressing challenges of our time. As renewable energy sources proliferate and new market mechanisms emerge, understanding the complex interactions between market participants, regulatory policies, and technological innovation becomes increasingly vital. Traditional modeling approaches often fall short in capturing the nuanced, adaptive, and strategic behaviors of real-world actors in energy markets.
**This project aims to bridge that gap by combining Agent-Based Modeling (ABM) with the power of Large Language Models (LLMs) to simulate a dynamic, realistic, and richly interactive energy market.**

## What is this simulation?
This simulation is a research and experimentation platform designed to model the behavior of diverse agents—consumers, prosumers, energy producers, utilities, and regulators—within a competitive energy market. Each agent is endowed with LLM-powered decision-making capabilities, enabling them to reason, negotiate, and adapt their strategies in response to evolving market conditions, policy changes, and the actions of other agents.

## Why LLM-powered agents?
By leveraging LLMs, agents in this simulation can:
- Interpret complex market signals and historical data
- Formulate and adapt strategies in natural language
- Respond to incentives, regulations, and market shocks in a human-like manner
- Engage in negotiation, contract formation, and policy compliance with greater realism
This approach allows for the exploration of emergent phenomena that arise from the interplay of intelligent, adaptive agents—phenomena that are difficult to predict or analyze using purely rule-based or equation-driven models

## What can you do with this simulation?
- **Test Policy Scenarios**: Evaluate the impact of carbon taxes, renewable incentives, and regulatory interventions on market outcomes.
- **Study Market Dynamics**: Observe how prices, supply-demand balance, renewable adoption, and market concentration evolve over time.
- **Analyze Agent Behavior**: Investigate how different agent types strategize, cooperate, or compete under various market conditions.
- **Generate Insights**: Produce detailed analytics and visualizations to inform research, policy design, or educational purposes.


## Features

- Multiple agent types with distinct behaviors:
  - **Consumers**: Purchase energy from utilities or local prosumers
  - **Prosumers**: Both produce and consume energy, can sell excess
  - **Energy Producers**: Generate and sell energy to utilities
  - **Utilities**: Buy from producers and sell to consumers
  - **Regulator**: Oversees market dynamics and implements policies
<br>
- LLM-powered decision making for all agents
<br>
- Market mechanisms:
  - Dynamic pricing based on supply and demand
  - Contract-based energy trading
  - Renewable energy incentives
  - Carbon taxation
  - Market concentration monitoring
<br>
- Comprehensive analytics and visualization:
  - Price trends
  - Supply-demand balance
  - Renewable energy adoption
  - Market concentration
  - Agent resources and profits
  - Detailed simulation reports

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/llm-abm-energymarkets.git
cd llm-abm-energymarkets
```

2. Install dependencies using Poetry:
```bash
poetry install
```

3. Install and start Ollama:
```bash
# Follow instructions at https://ollama.ai to install Ollama
ollama pull llama3.2:3b-instruct-fp16
```

## Usage

Run the simulation using the command-line interface:

```bash
poetry run python -m energy_market [options]
```

Available options:
- `--num-steps`: Number of simulation steps (default: 168, one week of hourly steps)
- `--num-consumers`: Number of consumer agents (default: 100)
- `--num-prosumers`: Number of prosumer agents (default: 20)
- `--num-producers`: Number of producer agents (default: 10)
- `--num-utilities`: Number of utility agents (default: 5)
- `--initial-price`: Initial energy price (default: 100.0)
- `--carbon-tax`: Carbon tax rate (default: 10.0)
- `--renewable-incentive`: Renewable energy incentive (default: 5.0)
- `--output-dir`: Output directory (default: results_YYYY-MM-DD_HH-MM-SS)

Example:
```bash
poetry run python -m energy_market --num-steps 336 --num-consumers 200 --carbon-tax 15.0
```

## Project Structure

```
src/energy_market/
├── agents/
│   ├── base.py          # Base agent class
│   ├── consumer.py      # Consumer agent
│   ├── prosumer.py      # Prosumer agent
│   ├── producer.py      # Energy producer agent
│   ├── utility.py       # Utility agent
│   └── regulator.py     # Market regulator agent
├── models/
│   └── energy_market.py # Main market model
├── utils/
│   └── llm_decision.py  # LLM-based decision making
├── simulation.py        # Simulation runner and analysis
└── __main__.py         # CLI entry point
```

## Output

The simulation generates the following outputs in the specified directory:

1. Data files:
   - `model_data.csv`: Time series of market-level metrics
   - `agent_data.csv`: Time series of agent-level metrics
   - `simulation_report.csv`: Summary statistics and insights

2. Visualizations:
   - `price_trends.png`: Energy price evolution
   - `supply_demand.png`: Supply-demand balance
   - `renewable_ratio.png`: Renewable energy adoption
   - `market_concentration.png`: Market concentration (HHI)
   - `agent_resources.png`: Distribution of agent resources
   - `agent_profits.png`: Distribution of agent profits

## Agent Decision Making

Each agent type uses LLM-powered decision making with specialized prompts:

1. **Consumers**:
   - Evaluate utility and prosumer offers
   - Consider price, renewable sources, and history
   - Make purchase decisions

2. **Prosumers**:
   - Manage energy production and storage
   - Set selling prices
   - Consider capacity upgrades

3. **Energy Producers**:
   - Determine production levels
   - Set prices and negotiate contracts
   - Plan capacity investments

4. **Utilities**:
   - Manage energy procurement
   - Set consumer prices
   - Balance renewable quotas

5. **Regulator**:
   - Monitor market health
   - Adjust carbon tax
   - Enforce regulations

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.