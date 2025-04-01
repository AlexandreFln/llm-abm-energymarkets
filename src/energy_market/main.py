import os
from pathlib import Path
from simulation import Simulation


# Set environment variables to remove timeout limits
os.environ['PYDEVD_WARN_EVALUATION_TIMEOUT'] = '0'  # Disable timeout warning
os.environ['PYDEVD_UNBLOCK_THREADS_TIMEOUT'] = '0'  # Disable thread unblocking
os.environ['PYDEVD_THREAD_DUMP_ON_WARN_EVALUATION_TIMEOUT'] = 'false'  # No thread dump
os.environ['PYDEVD_INTERRUPT_THREAD_TIMEOUT'] = '0'  # Disable interruption


def main():
    # Create output directory
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    # Initialize simulation with smaller configuration for testing
    simulation = Simulation(
        num_consumers=2,
        num_prosumers=1,
        num_producers=1,
        num_utilities=1,
        simulation_duration=10,  # Reduced duration for testing
        output_dir=output_dir
    )
    
    try:
        # Run simulation
        simulation.run()
        print("\nSimulation completed successfully!")
        
    except Exception as e:
        print(f"\nError during simulation: {str(e)}")
        raise


if __name__ == "__main__":
    main() 