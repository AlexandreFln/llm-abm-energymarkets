import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from typing import Dict, Any, List, Optional
from pathlib import Path
import time
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.io as pio
import json

from models.energy_market import EnergyMarketModel

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
        
    async def run_async(self, num_steps: int = 10, logger=None) -> None:
        """Run simulation for specified number of steps asynchronously.
        
        Args:
            num_steps: Number of steps to run (default: 1 week of hourly steps)
            logger: Optional logger instance
        """
        print(f"\nRunning simulation for {num_steps} steps...")
        start_time = time.time()
        
        for step in range(num_steps):
            step_start = time.time()
            print(f"\nStep {step + 1}/{num_steps} ({(step + 1) / num_steps * 100:.1f}%)")
            
            # Execute model step asynchronously
            await self.model.step_async()
            
            # Log the step if logger is provided
            if logger:
                logger.log_step(self.model)
            
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
    
    def get_agenttype_data(self) -> Dict[str: pd.DataFrame]:
        """Get agent-type level data from simulation.
        
        Returns:
            Dict containing agent-type dataframes
        """
        agenttype_dict = {}
        for agent in self.model.agent_types:
            name = agent.__name__.lower()
            agent_df = self.model.datacollector.get_agenttype_vars_dataframe(agent)
            agent_df.index.name = 'Step'
            agenttype_dict[f"{name}_model_data"] = agent_df

        return agenttype_dict
        
    def generate_report(self) -> Dict[str, Any]:
        """Generate summary report of simulation results.
        
        Returns:
            Dict containing summary statistics and insights
        """
        model_data = self.get_model_data()
        agent_data = self.get_agent_data()
        agenttype_dict = self.get_agenttype_data()
        
        stats_list = ['mean', 'std', 'min', 'max']
        # Calculate summary statistics
        model_data['Supply_Demand_Ratio'] = model_data['Total_Production'] / model_data['Total_Demand']
        model_data_statistics = {f'{col}_statistics': model_data.describe().loc[stats_list][col].to_dict() for col in model_data.columns}
        # Calculate market efficiency metrics
        price_volatility = model_data['Average_Price'].std() / model_data['Average_Price'].mean()
        # Calculate agent performance metrics
        final_resources = agent_data.xs(
            agent_data.index.get_level_values('Step').max(),
            level='Step'
        )['Resources'].dropna()  # Drop NaN values
        
        final_profits = agent_data.xs(
            agent_data.index.get_level_values('Step').max(),
            level='Step'
        )['Profit'].dropna()  # Drop NaN values
        
        # Calculate means and standard deviations with proper NaN handling
        resources_mean = final_resources.mean() if not final_resources.empty else 0
        resources_std = final_resources.std() if not final_resources.empty else 0
        profits_mean = final_profits.mean() if not final_profits.empty else 0
        profits_std = final_profits.std() if not final_profits.empty else 0
        
        # Calculate agent type statistics
        agenttype_stats = {}
        for agent_type, agenttype_data in agenttype_dict.items():
            agenttype_stats[agent_type] = {f'{col}_statistics': agenttype_data[agent_type].describe().loc[stats_list][col].to_dict() for col in model_data.columns}
        
        return {
            'model_statistics': model_data_statistics,
            'price_volatility': price_volatility,
            'agent_performance': {
                'avg_final_resources': resources_mean,
                'avg_final_profit': profits_mean,
                'resource_inequality': resources_std / resources_mean if resources_mean != 0 else 0,
                'profit_inequality': profits_std / profits_mean if profits_mean != 0 else 0
            },
            'agenttype_statistics': agenttype_stats
        }
        
    def save_data(self) -> None:
        """Save simulation data to CSV files."""
        model_data = self.get_model_data()
        agent_data = self.get_agent_data()
        agenttype_dict = self.get_agenttype_data()
        
        
        model_data.to_csv(self.output_dir / 'model_data.csv')
        agent_data.to_csv(self.output_dir / 'agent_data.csv')
        for agent_type, agenttype_data in agenttype_dict.items():
            agenttype_data.to_csv(self.output_dir / f'{agent_type}_data.csv')
        
        # Save summary report
        report = self.generate_report()
        pd.DataFrame(report).to_csv(self.output_dir / 'simulation_report.csv')

        
    def calculate_advanced_kpis(self) -> Dict[str, Any]:
        """Calculate advanced KPIs for the simulation."""
        model_data = self.get_model_data()
        agent_data = self.get_agent_data()
        agent_data = agent_data.drop('regulator', level=1, axis=0)  # Drop regulator causing for which no KPIs are calculated
        
        # Market Efficiency KPIs
        price_volatility = np.std(model_data['Average_Price'])
        market_efficiency = 1 - np.mean(
            np.abs(
                (model_data['Total_Production'] - model_data['Total_Demand']) /
                model_data['Total_Demand']
            )
        )
        
        # Sustainability KPIs
        renewable_penetration = np.mean(model_data['Renewable_Ratio'])
        renewable_stability = 1 - np.std(model_data['Renewable_Ratio'])
        
        # Market Competition KPIs
        market_concentration = model_data['Market_Concentration'].dropna()
        avg_market_concentration = np.mean(market_concentration)
        
        # Economic Impact KPIs
        final_step = agent_data.index.get_level_values('Step').max()
        initial_resources = agent_data.xs(0, level='Step')['Resources']
        final_resources = agent_data.xs(final_step, level='Step')['Resources']
        
        # Calculate growth rates and inequalities
        economic_growth = (np.mean(final_resources) - np.mean(initial_resources)) / np.mean(initial_resources)
        
        # Agent-Level Performance KPIs
        # TODO DEBUG : CHECK AGENT_DATA DF KEYS
        agent_types = agent_data.index.get_level_values('AgentID').unique()
        agent_performance = {}
        
        for agent_type in agent_types:
            type_data = agent_data.xs(agent_type, level='AgentID')
            
            # Calculate type-specific metrics
            avg_profit = np.mean(type_data['Profit'])
            profit_volatility = np.std(type_data['Profit'])
            
            avg_resources = np.mean(type_data['Resources'])
            resources_volatility = np.std(type_data['Resources'])
            
            # Market participation rate (if applicable)
            # if 'trades_completed' in type_data.columns:
            #     participation = (type_data['trades_completed'] > 0).mean()
            # else:
            #     participation = None
            
            # # Strategy adaptation (if applicable)
            # if 'strategy_changes' in type_data.columns:
            #     strategy_changes = type_data['strategy_changes'].mean()
            # else:
            #     strategy_changes = None
            
            # # Resource utilization (if applicable)
            # if all(col in type_data.columns for col in ['production', 'max_production_capacity']):
            #     resource_utilization = (
            #         type_data['production'] / type_data['max_production_capacity']
            #     ).mean()
            # else:
            #     resource_utilization = None
            
            # Store metrics for this agent type
            agent_performance[agent_type] = {
                'avg_profit': avg_profit,
                'profit_volatility': profit_volatility,
                'avg_resources': avg_resources,
                'resources_volatility': resources_volatility,
                # 'market_participation': participation,
                # 'strategy_adaptability': strategy_changes,
                # 'resource_utilization': resource_utilization
            }
        
        return {
            'market_efficiency': {
                'price_volatility': price_volatility,
                'supply_demand_mismatch': market_efficiency
            },
            'sustainability': {
                'renewable_penetration': renewable_penetration,
                'renewable_stability': renewable_stability
            },
            'market_competition': {
                'avg_concentration': avg_market_concentration,
            },
            'economic_impact': {
                'economic_growth': economic_growth
            },
            'agent_performance': agent_performance
        }
    
    def _calculate_gini(self, array: np.ndarray) -> float:
        """Calculate Gini coefficient of inequality."""
        array = array.flatten()
        if np.amin(array) < 0:
            array -= np.amin(array)
        array += 0.0000001
        array = np.sort(array)
        index = np.arange(1, array.shape[0] + 1)
        n = array.shape[0]
        return ((np.sum((2 * index - n - 1) * array)) / (n * np.sum(array)))

    def create_interactive_dashboard(self, save: bool = True) -> None:
        """Create an interactive Plotly dashboard with all KPIs."""
        model_data = self.get_model_data()
        advanced_kpis = self.calculate_advanced_kpis()
        
        # Create subplot figure
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                'Energy Price Trends',
                'Supply and Demand Balance',
                'Renewable Energy Ratio',
                'Market Concentration',
                'Economic Growth',
                'Social Equity (Gini)'
            )
        )
        
        # 1. Price Trends
        fig.add_trace(
            go.Scatter(
                x=model_data.index,
                y=model_data['Average_Price'],
                name='Average Price',
                line=dict(color='blue')
            ),
            row=1, col=1
        )
        
        # 2. Supply-Demand
        fig.add_trace(
            go.Scatter(
                x=model_data.index,
                y=model_data['Total_Production'],
                name='Supply',
                line=dict(color='green')
            ),
            row=1, col=2
        )
        fig.add_trace(
            go.Scatter(
                x=model_data.index,
                y=model_data['Total_Demand'],
                name='Demand',
                line=dict(color='red')
            ),
            row=1, col=2
        )
        
        # 3. Renewable Ratio
        fig.add_trace(
            go.Scatter(
                x=model_data.index,
                y=model_data['Renewable_Ratio'],
                name='Renewable Ratio',
                line=dict(color='green')
            ),
            row=2, col=1
        )
        fig.add_hline(
            y=0.3,
            line_dash="dash",
            line_color="red",
            annotation_text="Target",
            row=2, col=1
        )
        
        # 4. Market Concentration
        fig.add_trace(
            go.Scatter(
                x=model_data.index,
                y=model_data['Market_Concentration'],
                name='HHI',
                line=dict(color='purple')
            ),
            row=2, col=2
        )
        
        # 5. Economic Growth
        agent_data = self.get_agent_data()
        resources_over_time = agent_data['Resources'].groupby('Step').mean()
        fig.add_trace(
            go.Scatter(
                x=resources_over_time.index,
                y=resources_over_time.values,
                name='Avg Resources',
                line=dict(color='orange')
            ),
            row=3, col=1
        )
        
        # 6. Social Equity
        # gini_over_time = []
        # for step in agent_data.index.get_level_values('Step').unique():
        #     step_resources = agent_data.xs(step, level='Step')['Resources'].values
        #     gini_over_time.append(self._calculate_gini(step_resources))
        
        # fig.add_trace(
        #     go.Scatter(
        #         x=model_data.index,
        #         y=gini_over_time,
        #         name='Gini Coefficient',
        #         line=dict(color='red')
        #     ),
        #     row=3, col=2
        # )
        
        # Update layout
        fig.update_layout(
            height=1200,
            width=1600,
            title_text="Energy Market Simulation Dashboard",
            showlegend=True,
            template="plotly_white"
        )
        
        if save:
            # Save as interactive HTML
            pio.write_html(fig, str(self.output_dir / 'interactive_dashboard.html'))
            # Save as static image for thesis
            # pio.write_image(fig, str(self.output_dir / 'dashboard.png'), scale=2)
            
            # Save KPIs to JSON
            with open(self.output_dir / 'advanced_kpis.json', 'w') as f:
                json.dump(advanced_kpis, f, indent=2)
            
            # Create a formatted markdown report
            self._create_markdown_report(advanced_kpis)
    
    def _create_markdown_report(self, kpis: Dict[str, Any]) -> None:
        """Create a formatted markdown report for thesis inclusion."""
        report = f"""# Energy Market Simulation Results

## Key Performance Indicators

### Market Efficiency
- Price Volatility: {kpis['market_efficiency']['price_volatility']:.3f}
- Supply-Demand Mismatch: {kpis['market_efficiency']['supply_demand_mismatch']:.3f}

### Sustainability
- Renewable Energy Penetration: {kpis['sustainability']['renewable_penetration']:.3f}
- Renewable Stability: {kpis['sustainability']['renewable_stability']:.3f}

### Market Competition
- Average Market Concentration (HHI): {kpis['market_competition']['avg_concentration']:.3f}

### Economic Impact
- Economic Growth: {kpis['economic_impact']['economic_growth']:.3f}

### Agent Performance
"""
        # Add agent-specific performance metrics
        for agent_type, metrics in kpis['agent_performance'].items():
            report += f"\n#### {agent_type}\n"
            report += f"- Average Profit: {metrics['avg_profit']:.3f}\n"
            report += f"- Profit Volatility: {metrics['profit_volatility']:.3f}\n"
            
            # if metrics['market_participation'] is not None:
            #     report += f"- Market Participation Rate: {metrics['market_participation']:.3f}\n"
            
            # if metrics['strategy_adaptability'] is not None:
            #     report += f"- Strategy Changes per Step: {metrics['strategy_adaptability']:.3f}\n"
            
            # if metrics['resource_utilization'] is not None:
            #     report += f"- Resource Utilization Rate: {metrics['resource_utilization']:.3f}\n"

        report += """
## Visualization
Interactive visualizations can be found in `interactive_dashboard.html`
Static visualizations for thesis inclusion can be found in `dashboard.png`
"""
        
        with open(self.output_dir / 'simulation_report.md', 'w') as f:
            f.write(report)
        
    async def run_and_analyze(self, num_steps: int = 10, logger = None) -> None:
        """Run simulation and generate all analyses."""
        await self.run_async(num_steps, logger)
        self.save_data()
        self.create_interactive_dashboard()
        print("\nAnalysis complete! Check the output directory for:")
        print("1. interactive_dashboard.html - Interactive Plotly dashboard")
        print("2. dashboard.png - Static dashboard for thesis")
        print("3. advanced_kpis.json - Detailed KPI metrics")
        print("4. simulation_report.md - Formatted report for thesis inclusion") 