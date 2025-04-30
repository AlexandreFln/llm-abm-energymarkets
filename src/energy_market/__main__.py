import argparse
from pathlib import Path
from datetime import datetime
import asyncio

from simulation import EnergyMarketSimulation
from src.energy_market.logging_system import SimulationLogger

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Run energy market simulation with LLM-powered agents.'
    )
    
    parser.add_argument(
        '--num-steps',
        type=int,
        default=3,
        help='Number of simulation steps (default: 168, one week of hourly steps)'
    )
    
    parser.add_argument(
        '--num-consumers',
        type=int,
        default=3,
        help='Number of consumer agents (default: 100)'
    )
    
    parser.add_argument(
        '--num-prosumers',
        type=int,
        default=2,
        help='Number of prosumer agents (default: 20)'
    )
    
    parser.add_argument(
        '--num-producers',
        type=int,
        default=2,
        help='Number of producer agents (default: 10)'
    )
    
    parser.add_argument(
        '--num-utilities',
        type=int,
        default=2,
        help='Number of utility agents (default: 5)'
    )
    
    parser.add_argument(
        '--initial-price',
        type=float,
        default=100.0,
        help='Initial energy price (default: 100.0)'
    )
    
    parser.add_argument(
        '--carbon-tax',
        type=float,
        default=10.0,
        help='Carbon tax rate (default: 10.0)'
    )
    
    parser.add_argument(
        '--renewable-incentive',
        type=float,
        default=5.0,
        help='Renewable energy incentive (default: 5.0)'
    )
    
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='Output directory (default: results_YYYY-MM-DD_HH-MM-SS)'
    )
    
    return parser.parse_args()

def main():
    """Main function to run the simulation."""
    args = parse_args()
    
    # Create output directory with timestamp if not specified
    if args.output_dir is None:
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
        output_dir = Path.cwd() / f'results/results_{timestamp}'
    else:
        output_dir = Path(args.output_dir)
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("\nInitializing energy market simulation...")
    print(f"Configuration:")
    print(f"  - Number of steps: {args.num_steps}")
    print(f"  - Consumers: {args.num_consumers}")
    print(f"  - Prosumers: {args.num_prosumers}")
    print(f"  - Producers: {args.num_producers}")
    print(f"  - Utilities: {args.num_utilities}")
    print(f"  - Carbon tax: {args.carbon_tax}")
    print(f"  - Output directory: {output_dir}")
    
    try:
        # Initialize and run simulation
        simulation = EnergyMarketSimulation(
            num_consumers=args.num_consumers,
            num_prosumers=args.num_prosumers,
            num_producers=args.num_producers,
            num_utilities=args.num_utilities,
            initial_price=args.initial_price,
            carbon_tax_rate=args.carbon_tax,
            renewable_incentive=args.renewable_incentive,
            output_dir=str(output_dir)
        )
        
        # Initialize logger with the output directory
        logger = SimulationLogger(base_dir=str(output_dir))
        logger.start_new_run()
        
        print("\nStarting simulation...")
        asyncio.run(simulation.run_and_analyze(args.num_steps, logger))
        print("\nSimulation completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user.")
        if output_dir.exists():
            print(f"Partial results saved in: {output_dir}")
        return 1
        
    except Exception as e:
        print(f"\n\nError during simulation: {e}")
        import traceback
        traceback.print_exc()
        if output_dir.exists():
            print(f"Partial results may be available in: {output_dir}")
        return 1
        
    return 0

if __name__ == '__main__':
    import sys
    sys.exit(main())