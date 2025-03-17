# Test script for the energy market model
from energy_market_temp import EnergyMarket

# Create and initialize the model
model = EnergyMarket()

# Run the model for 10 steps
for i in range(10):
    model.step()

# Get the data from the data collector
model_data = model.datacollector.get_model_vars_dataframe()
agent_data = model.datacollector.get_agent_vars_dataframe()

# Display the results
print("Model-level data:")
print(model_data)
print("\nAgent-level data:")
print(agent_data) 