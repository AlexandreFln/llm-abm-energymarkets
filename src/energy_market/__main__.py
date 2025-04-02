import argparse
from pathlib import Path
from datetime import datetime

from energy_market.simulation import EnergyMarketSimulation

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
        default=2,
        help='Number of consumer agents (default: 100)'
    )
    
    parser.add_argument(
        '--num-prosumers',
        type=int,
        default=1,
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
        timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        output_dir = Path.cwd() / f'results/results_{timestamp}'
    else:
        output_dir = Path(args.output_dir)
        
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
        
        print("\nStarting simulation...")
        simulation.run_and_analyze(args.num_steps)
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