import pytest
import numpy as np
from pathlib import Path

from src.energy_market.simulation import EnergyMarketSimulation
from src.energy_market.models.energy_market import EnergyMarketModel
from src.energy_market.agents.consumer import ConsumerAgent
from src.energy_market.agents.prosumer import ProsumerAgent
from src.energy_market.agents.producer import EnergyProducerAgent
from src.energy_market.agents.utility import UtilityAgent
from src.energy_market.agents.regulator import RegulatorAgent

@pytest.fixture
def simulation():
    """Create a test simulation instance."""
    return EnergyMarketSimulation(
        num_consumers=10,
        num_prosumers=5,
        num_producers=3,
        num_utilities=2,
        initial_price=100.0,
        carbon_tax_rate=10.0,
        renewable_incentive=5.0,
        output_dir='test_results'
    )

def test_simulation_initialization(simulation):
    """Test that simulation is initialized correctly."""
    assert isinstance(simulation.model, EnergyMarketModel)
    assert len(simulation.model.agents['consumers']) == 10
    assert len(simulation.model.agents['prosumers']) == 5
    assert len(simulation.model.agents['producers']) == 3
    assert len(simulation.model.agents['utilities']) == 2
    assert simulation.model.agents['regulator'] is not None
    
def test_consumer_agent():
    """Test consumer agent initialization and basic functionality."""
    model = EnergyMarketModel()
    consumer = ConsumerAgent(
        unique_id="test_consumer",
        model=model,
        persona="default",
        initial_resources=1000.0,
        energy_needs=100.0
    )
    
    assert consumer.resources == 1000.0
    assert consumer.energy_needs == 100.0
    assert consumer.profit == 0.0
    
    # Test purchase functionality
    success = consumer.purchase_energy("test_seller", 50.0, 10.0)
    assert success
    assert consumer.resources == 500.0  # 1000 - (50 * 10)
    assert len(consumer.transaction_history) == 1
    
def test_prosumer_agent():
    """Test prosumer agent initialization and basic functionality."""
    model = EnergyMarketModel()
    prosumer = ProsumerAgent(
        unique_id="test_prosumer",
        model=model,
        persona="default",
        production_type="solar",
        initial_resources=2000.0,
        energy_needs=100.0,
        max_production_capacity=200.0
    )
    
    assert prosumer.resources == 2000.0
    assert prosumer.max_production_capacity == 200.0
    assert prosumer.energy_stored == 0.0
    
    # Test storage functionality
    excess = prosumer.store_energy(150.0)
    assert prosumer.energy_stored == 150.0
    assert excess == 0.0
    
def test_producer_agent():
    """Test producer agent initialization and basic functionality."""
    model = EnergyMarketModel()
    producer = EnergyProducerAgent(
        unique_id="test_producer",
        model=model,
        persona="default",
        production_type="solar",
        initial_resources=10000.0,
        max_capacity=1000.0
    )
    
    assert producer.resources == 10000.0
    assert producer.max_capacity == 1000.0
    assert producer.is_renewable()
    
    # Test contract negotiation
    contract = producer.negotiate_contract("test_utility", 500.0, 30)
    assert contract['accepted']
    assert contract['amount'] == 500.0
    assert contract['duration'] == 30
    
def test_utility_agent():
    """Test utility agent initialization and basic functionality."""
    model = EnergyMarketModel()
    utility = UtilityAgent(
        unique_id="test_utility",
        model=model,
        persona="eco_friendly",
        initial_resources=50000.0,
        renewable_quota=0.2
    )
    
    assert utility.resources == 50000.0
    assert utility.renewable_quota == 0.2
    assert len(utility.producer_contracts) == 0
    
    # Test energy selling
    result = utility.sell_energy("test_customer", 100.0)
    assert not result['success']  # Should fail due to no available energy
    
def test_regulator_agent():
    """Test regulator agent initialization and basic functionality."""
    model = EnergyMarketModel()
    regulator = RegulatorAgent(
        unique_id="test_regulator",
        model=model,
        base_carbon_tax=10.0
    )
    
    assert regulator.current_carbon_tax == 10.0
    assert len(regulator.violations['price_gouging']) == 0
    
    # Test fine calculation
    violation = {
        'type': 'price_gouging',
        'price': 150.0,
        'threshold': 100.0
    }
    fine = regulator.calculate_fine_amount(violation)
    assert fine == 100.0  # (150 - 100) * 2
    
def test_simulation_step(simulation):
    """Test that simulation can run steps without errors."""
    try:
        simulation.run(num_steps=5)
        assert simulation.model.schedule.time == 5
    except Exception as e:
        pytest.fail(f"Simulation step failed with error: {e}")
        
def test_data_collection(simulation):
    """Test that data collection works correctly."""
    simulation.run(num_steps=5)
    
    model_data = simulation.get_model_data()
    agent_data = simulation.get_agent_data()
    
    assert len(model_data) == 5  # One row per step
    assert not model_data.empty
    assert not agent_data.empty
    
def test_report_generation(simulation):
    """Test that report generation works correctly."""
    simulation.run(num_steps=5)
    report = simulation.generate_report()
    
    assert 'price_statistics' in report
    assert 'renewable_statistics' in report
    assert 'market_efficiency' in report
    assert 'agent_performance' in report
    
def test_output_files(simulation):
    """Test that output files are created correctly."""
    simulation.run_and_analyze(num_steps=5)
    output_dir = Path('test_results')
    
    assert output_dir.exists()
    assert (output_dir / 'model_data.csv').exists()
    assert (output_dir / 'agent_data.csv').exists()
    assert (output_dir / 'simulation_report.csv').exists()
    assert (output_dir / 'price_trends.png').exists()
    
    # Clean up test files
    for file in output_dir.glob('*'):
        file.unlink()
    output_dir.rmdir() 