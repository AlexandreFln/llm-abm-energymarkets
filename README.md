# LLM-Powered Energy Market Simulation

This project implements an Agent-Based Model (ABM) of an energy market with LLM-powered decision-making agents. The simulation models interactions between consumers, prosumers, energy producers, utilities, and a market regulator to study market dynamics, renewable energy adoption, and policy impacts.

## Features

- Multiple agent types with distinct behaviors:
  - **Consumers**: Purchase energy from utilities or local prosumers
  - **Prosumers**: Both produce and consume energy, can sell excess
  - **Energy Producers**: Generate and sell energy to utilities
  - **Utilities**: Buy from producers and sell to consumers
  - **Regulator**: Oversees market dynamics and implements policies

- LLM-powered decision making for all agents
- Market mechanisms:
  - Dynamic pricing based on supply and demand
  - Contract-based energy trading
  - Renewable energy incentives
  - Carbon taxation
  - Market concentration monitoring

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