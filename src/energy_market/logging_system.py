import os
import json
from datetime import datetime
from typing import Dict, Any, List
import numpy as np
from src.energy_market.agents.consumer import ConsumerAgent
from src.energy_market.agents.prosumer import ProsumerAgent
from src.energy_market.agents.producer import EnergyProducerAgent
from src.energy_market.agents.utility import UtilityAgent


class SimulationLogger:
    def __init__(self, base_dir: str = "logs"):
        """Initialize the logging system.
        
        Args:
            base_dir: Base directory for storing logs
        """
        self.base_dir = base_dir
        self.current_run_dir = None
        self.step_logs = []
        self.current_step = 0
        
    def start_new_run(self):
        """Create a new directory for the current simulation run."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.current_run_dir = os.path.join(self.base_dir, f"simulation_{timestamp}")
        os.makedirs(self.current_run_dir, exist_ok=True)
        self.step_logs = []
        self.current_step = 0
        
    def log_market_conditions(self, model: Any) -> Dict[str, Any]:
        """Log current market conditions.
        
        Args:
            model: The EnergyMarketModel instance
            
        Returns:
            Dictionary containing market conditions
        """
        # Collect market-wide statistics
        market_conditions = {
            "step": self.current_step,
            "timestamp": datetime.now().isoformat(),
            "total_agents": len(model.schedule.agents),
            "average_energy_price": np.mean([a.energy_price for a in model.schedule.agents 
                                           if hasattr(a, 'energy_price')]),
            "total_production": sum([a.production for a in model.schedule.agents 
                                   if hasattr(a, 'production')]),
            "total_consumption": sum([a.energy_needs for a in model.schedule.agents 
                                    if hasattr(a, 'energy_needs')]),
        }
        return market_conditions
    
    def log_agent_state(self, agent: Any) -> Dict[str, Any]:
        """Log the current state of an agent.
        
        Args:
            agent: The agent instance
            
        Returns:
            Dictionary containing agent state
        """
        agent_state = {
            "id": agent.unique_id,
            "type": agent.__class__.__name__,
            "persona": agent.persona,
            "resources": agent.resources,
            "profit": getattr(agent, 'profit', 0),
        }
        
        # Add type-specific attributes
        if isinstance(agent, (ConsumerAgent, ProsumerAgent)):
            agent_state.update({
                "energy_needs": agent.energy_needs,
            })
            
        if isinstance(agent, (ProsumerAgent, EnergyProducerAgent)):
            agent_state.update({
                "production": agent.production,
                "max_capacity": agent.max_capacity,
                "energy_stored": getattr(agent, 'energy_stored', 0),
            })
            
        if isinstance(agent, UtilityAgent):
            agent_state.update({
                "utility_type": agent.utility_type,
                "renewable_quota": agent.renewable_quota,
                "energy_purchased": agent.energy_purchased,
            })
            
        return agent_state
    
    def log_step(self, model: Any, agent_decisions: Dict[str, Dict[str, Any]]):
        """Log a complete simulation step.
        
        Args:
            model: The EnergyMarketModel instance
            agent_decisions: Dictionary mapping agent IDs to their decisions
        """
        step_log = {
            "market_conditions": self.log_market_conditions(model),
            "agents": {}
        }
        
        # Log state and decisions for each agent
        for agent in model.schedule.agents:
            agent_id = agent.unique_id
            step_log["agents"][agent_id] = {
                "state": self.log_agent_state(agent),
                "decisions": agent_decisions.get(agent_id, {})
            }
            
        self.step_logs.append(step_log)
        self.current_step += 1
        
    def save_logs(self):
        """Save all logs to files."""
        if not self.current_run_dir:
            raise RuntimeError("No active simulation run. Call start_new_run() first.")
            
        # Save step-by-step logs
        with open(os.path.join(self.current_run_dir, "simulation_logs.json"), "w") as f:
            json.dump(self.step_logs, f, indent=2)
            
        # Create a human-readable summary
        self._create_summary()
        
    def _create_summary(self):
        """Create a human-readable summary of the simulation."""
        summary_path = os.path.join(self.current_run_dir, "summary.txt")
        
        with open(summary_path, "w") as f:
            f.write("Simulation Summary\n")
            f.write("================\n\n")
            
            for step_log in self.step_logs:
                f.write(f"\nStep {step_log['market_conditions']['step']}\n")
                f.write("-" * 50 + "\n")
                
                # Write market conditions
                f.write("Market Conditions:\n")
                for key, value in step_log['market_conditions'].items():
                    if key not in ['step', 'timestamp']:
                        f.write(f"  {key}: {value}\n")
                
                # Write agent states and decisions
                f.write("\nAgent States and Decisions:\n")
                for agent_id, agent_data in step_log['agents'].items():
                    f.write(f"\n  Agent {agent_id}:\n")
                    f.write("    State:\n")
                    for key, value in agent_data['state'].items():
                        f.write(f"      {key}: {value}\n")
                    if agent_data['decisions']:
                        f.write("    Decisions:\n")
                        for key, value in agent_data['decisions'].items():
                            f.write(f"      {key}: {value}\n") 