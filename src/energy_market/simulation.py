import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Any, List, Optional
from pathlib import Path
import time

from .models.energy_market import EnergyMarketModel

class EnergyMarketSimulation:
    """Class to run and analyze energy market simulations."""
    
    def __init__(self,
                 num_consumers: int = 100,
                 num_prosumers: int = 20,
                 num_producers: int = 10,
                 num_utilities: int = 5,
                 initial_price: float = 100.0,
                 carbon_tax_rate: float = 10.0,
                 renewable_incentive: float = 5.0,
                 output_dir: Optional[str] = None):
        """Initialize simulation.
        
        Args:
            num_consumers: Number of consumer agents
            num_prosumers: Number of prosumer agents
            num_producers: Number of producer agents
            num_utilities: Number of utility agents
            initial_price: Initial energy price
            carbon_tax_rate: Tax rate for carbon emissions
            renewable_incentive: Incentive for renewable energy
            output_dir: Directory to save outputs (default: current directory)
        """
        self.model = EnergyMarketModel(
            num_consumers=num_consumers,
            num_prosumers=num_prosumers,
            num_producers=num_producers,
            num_utilities=num_utilities,
            initial_price=initial_price,
            carbon_tax_rate=carbon_tax_rate,
            renewable_incentive=renewable_incentive
        )
        
        self.output_dir = Path(output_dir) if output_dir else Path.cwd()
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def run(self, num_steps: int = 168) -> None:
        """Run simulation for specified number of steps.
        
        Args:
            num_steps: Number of steps to run (default: 1 week of hourly steps)
        """
        print(f"\nRunning simulation for {num_steps} steps...")
        start_time = time.time()
        
        for step in range(num_steps):
            step_start = time.time()
            print(f"\nStep {step + 1}/{num_steps} ({(step + 1) / num_steps * 100:.1f}%)")
            
            # Execute model step
            self.model.step()
            
            # Show step timing
            step_time = time.time() - step_start
            total_time = time.time() - start_time
            avg_step_time = total_time / (step + 1)
            remaining_steps = num_steps - (step + 1)
            est_remaining = remaining_steps * avg_step_time
            
            print(f"Step time: {step_time:.1f}s, Avg: {avg_step_time:.1f}s, Est. remaining: {est_remaining/60:.1f}m")
        
        total_time = time.time() - start_time
        print(f"\nSimulation complete! Total time: {total_time/60:.1f}m")
            
    def get_model_data(self) -> pd.DataFrame:
        """Get model-level data from simulation.
        
        Returns:
            DataFrame containing model metrics over time
        """
        model_data = self.model.datacollector.get_model_vars_dataframe()
        model_data.index.name = 'Step'
        return model_data
        
    def get_agent_data(self) -> pd.DataFrame:
        """Get agent-level data from simulation.
        
        Returns:
            DataFrame containing agent metrics over time
        """
        agent_data = self.model.datacollector.get_agent_vars_dataframe()
        agent_data.index.names = ['Step', 'AgentID']
        return agent_data
        
    def plot_price_trends(self, save: bool = True) -> None:
        """Plot energy price trends over time."""
        model_data = self.get_model_data()
        
        plt.figure(figsize=(12, 6))
        plt.plot(model_data.index, model_data['Average_Price'], label='Average Price')
        plt.title('Energy Price Trends')
        plt.xlabel('Time Step')
        plt.ylabel('Price')
        plt.legend()
        plt.grid(True)
        
        if save:
            plt.savefig(self.output_dir / 'price_trends.png')
        plt.close()
        
    def plot_supply_demand(self, save: bool = True) -> None:
        """Plot supply and demand balance over time."""
        model_data = self.get_model_data()
        
        plt.figure(figsize=(12, 6))
        plt.plot(model_data.index, model_data['Total_Production'], label='Supply')
        plt.plot(model_data.index, model_data['Total_Demand'], label='Demand')
        plt.title('Supply and Demand Balance')
        plt.xlabel('Time Step')
        plt.ylabel('Energy Units')
        plt.legend()
        plt.grid(True)
        
        if save:
            plt.savefig(self.output_dir / 'supply_demand.png')
        plt.close()
        
    def plot_renewable_ratio(self, save: bool = True) -> None:
        """Plot renewable energy ratio over time."""
        model_data = self.get_model_data()
        
        plt.figure(figsize=(12, 6))
        plt.plot(model_data.index, model_data['Renewable_Ratio'])
        plt.axhline(y=0.3, color='r', linestyle='--', label='Target Ratio')
        plt.title('Renewable Energy Ratio')
        plt.xlabel('Time Step')
        plt.ylabel('Ratio')
        plt.legend()
        plt.grid(True)
        
        if save:
            plt.savefig(self.output_dir / 'renewable_ratio.png')
        plt.close()
        
    def plot_market_concentration(self, save: bool = True) -> None:
        """Plot market concentration (HHI) over time."""
        model_data = self.get_model_data()
        
        plt.figure(figsize=(12, 6))
        plt.plot(model_data.index, model_data['Market_Concentration'])
        plt.axhline(y=0.25, color='r', linestyle='--', label='High Concentration Threshold')
        plt.title('Market Concentration (HHI)')
        plt.xlabel('Time Step')
        plt.ylabel('HHI')
        plt.legend()
        plt.grid(True)
        
        if save:
            plt.savefig(self.output_dir / 'market_concentration.png')
        plt.close()
        
    def plot_agent_resources(self, save: bool = True) -> None:
        """Plot agent resources distribution over time."""
        agent_data = self.get_agent_data()
        resources = agent_data['Resources'].unstack()
        
        plt.figure(figsize=(12, 6))
        sns.boxplot(data=resources)
        plt.title('Distribution of Agent Resources')
        plt.xlabel('Time Step')
        plt.ylabel('Resources')
        plt.xticks(rotation=45)
        
        if save:
            plt.savefig(self.output_dir / 'agent_resources.png')
        plt.close()
        
    def plot_agent_profits(self, save: bool = True) -> None:
        """Plot agent profits distribution over time."""
        agent_data = self.get_agent_data()
        profits = agent_data['Profit'].unstack()
        
        plt.figure(figsize=(12, 6))
        sns.boxplot(data=profits)
        plt.title('Distribution of Agent Profits')
        plt.xlabel('Time Step')
        plt.ylabel('Profit')
        plt.xticks(rotation=45)
        
        if save:
            plt.savefig(self.output_dir / 'agent_profits.png')
        plt.close()
        
    def generate_report(self) -> Dict[str, Any]:
        """Generate summary report of simulation results.
        
        Returns:
            Dict containing summary statistics and insights
        """
        model_data = self.get_model_data()
        agent_data = self.get_agent_data()
        
        # Calculate summary statistics
        price_stats = model_data['Average_Price'].describe()
        renewable_stats = model_data['Renewable_Ratio'].describe()
        
        # Calculate market efficiency metrics
        supply_demand_ratio = (
            model_data['Total_Production'] / model_data['Total_Demand']
        ).mean()
        
        price_volatility = model_data['Average_Price'].std() / model_data['Average_Price'].mean()
        
        # Calculate agent performance metrics
        final_resources = agent_data.xs(
            agent_data.index.get_level_values('Step').max(),
            level='Step'
        )['Resources']
        
        final_profits = agent_data.xs(
            agent_data.index.get_level_values('Step').max(),
            level='Step'
        )['Profit']
        
        return {
            'price_statistics': {
                'mean': price_stats['mean'],
                'std': price_stats['std'],
                'min': price_stats['min'],
                'max': price_stats['max']
            },
            'renewable_statistics': {
                'mean': renewable_stats['mean'],
                'std': renewable_stats['std'],
                'min': renewable_stats['min'],
                'max': renewable_stats['max']
            },
            'market_efficiency': {
                'supply_demand_ratio': supply_demand_ratio,
                'price_volatility': price_volatility,
                'avg_market_concentration': model_data['Market_Concentration'].mean()
            },
            'agent_performance': {
                'avg_final_resources': final_resources.mean(),
                'avg_final_profit': final_profits.mean(),
                'resource_inequality': final_resources.std() / final_resources.mean(),
                'profit_inequality': final_profits.std() / final_profits.mean()
            }
        }
        
    def save_data(self) -> None:
        """Save simulation data to CSV files."""
        model_data = self.get_model_data()
        agent_data = self.get_agent_data()
        
        model_data.to_csv(self.output_dir / 'model_data.csv')
        agent_data.to_csv(self.output_dir / 'agent_data.csv')
        
        # Save summary report
        report = self.generate_report()
        pd.DataFrame(report).to_csv(self.output_dir / 'simulation_report.csv')
        
    def plot_all(self) -> None:
        """Generate all plots."""
        self.plot_price_trends()
        self.plot_supply_demand()
        self.plot_renewable_ratio()
        self.plot_market_concentration()
        self.plot_agent_resources()
        self.plot_agent_profits()
        
    def run_and_analyze(self, num_steps: int = 168) -> None:
        """Run simulation and generate all analyses.
        
        Args:
            num_steps: Number of steps to run
        """
        print("Running simulation...")
        self.run(num_steps)
        
        print("Generating plots...")
        self.plot_all()
        
        print("Saving data...")
        self.save_data()
        
        print("Simulation complete. Results saved to:", self.output_dir) 