"""
Control Execution Layer
Orchestrates the entire system: simulation → prediction → optimization → execution.
Manages the system state and logging.
"""

from dataclasses import dataclass, field
from typing import Dict, List
import pandas as pd
from datetime import datetime

from .simulator import DemandSimulator
from .model import LoadPredictionModel
from .optimizer import LoadOptimizer, OptimizationResult


@dataclass
class SystemState:
    """Represents the current state of the transformer system."""
    timestamp: datetime
    hour: int
    current_loads: Dict[str, float]  # Actual loads at this hour
    total_current_load: float
    predicted_load: float
    transformer_capacity: float
    is_overloaded: bool
    optimization_result: OptimizationResult = None
    
    def to_dict(self):
        """Convert state to dictionary for logging."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'hour': self.hour,
            'current_loads': self.current_loads,
            'total_current_load': self.total_current_load,
            'predicted_load': self.predicted_load,
            'capacity': self.transformer_capacity,
            'is_overloaded': self.is_overloaded,
            'optimization_actions': self.optimization_result.actions if self.optimization_result else []
        }


class SystemController:
    """
    Main controller that orchestrates the entire load optimization system.
    Integrates simulator, predictor, and optimizer.
    """
    
    def __init__(self, transformer_capacity=150.0, verbose=True):
        """
        Initialize the system controller.
        
        Args:
            transformer_capacity: Max safe transformer load (units)
            verbose: Whether to log detailed information
        """
        self.capacity = transformer_capacity
        self.verbose = verbose
        
        # Initialize components
        self.simulator = DemandSimulator()
        self.predictor = LoadPredictionModel()
        self.optimizer = LoadOptimizer(transformer_capacity=transformer_capacity)
        
        # Generate and train on 24-hour profile
        self.demand_profile = self.simulator.generate_24h_profile()
        self.predictor.train(self.demand_profile)
        
        # System history
        self.state_history: List[SystemState] = []
        self.action_log: List[str] = []
        
        if self.verbose:
            print(f"[INIT] System Controller initialized")
            print(f"[INIT] Transformer capacity: {self.capacity} units")
            print(f"[INIT] Predictor trained on synthetic 24-hour data")
    
    def execute_hour(self, hour: int) -> SystemState:
        """
        Execute system control for a single hour.
        
        Flow:
        1. Get current loads from demand profile
        2. Predict next-hour load
        3. Check if overloaded
        4. Optimize if needed
        5. Return updated system state
        
        Args:
            hour: Hour index (0-23)
        
        Returns:
            SystemState: Current system state
        """
        if hour < 0 or hour >= len(self.demand_profile):
            raise ValueError(f"Hour must be between 0 and 23, got {hour}")
        
        # Get current loads from profile
        row = self.demand_profile.iloc[hour]
        timestamp = row['timestamp']
        current_loads = {
            'hospital': float(row['hospital']),
            'residential': float(row['residential']),
            'commercial': float(row['commercial']),
            'ev_charging': float(row['ev_charging'])
        }
        total_current = sum(current_loads.values())
        
        # Predict next-hour load
        predicted_load = self.predictor.predict_next_hour(hour, current_loads)
        
        # Check if overloaded
        is_overloaded = self.optimizer.is_overloaded(predicted_load)
        
        # Optimize if needed
        optimization_result = None
        if is_overloaded:
            optimization_result = self.optimizer.optimize(predicted_load, current_loads)
            current_loads = optimization_result.optimized_loads
        
        # Create state snapshot
        state = SystemState(
            timestamp=timestamp,
            hour=hour,
            current_loads=current_loads,
            total_current_load=sum(current_loads.values()),
            predicted_load=predicted_load,
            transformer_capacity=self.capacity,
            is_overloaded=is_overloaded,
            optimization_result=optimization_result
        )
        
        # Log state
        self.state_history.append(state)
        
        if self.verbose:
            self._log_hour_execution(state, total_current)
        
        return state
    
    def execute_24h(self) -> List[SystemState]:
        """
        Execute system control for full 24-hour period.
        
        Returns:
            List[SystemState]: States for each hour
        """
        if self.verbose:
            print("\n" + "=" * 80)
            print("EXECUTING 24-HOUR SYSTEM CONTROL")
            print("=" * 80 + "\n")
        
        states = []
        for hour in range(24):
            state = self.execute_hour(hour)
            states.append(state)
        
        if self.verbose:
            self._print_summary()
        
        return states
    
    def _log_hour_execution(self, state: SystemState, original_total: float):
        """Log execution details for an hour."""
        print(f"\n[{state.hour:02d}:00] ", end='')
        
        if state.is_overloaded:
            print(f"⚠️  OVERLOAD: Pred={state.predicted_load:.1f} > Cap={state.transformer_capacity}")
            if state.optimization_result:
                reduction = original_total - state.total_current_load
                print(f"         → Shedding {reduction:.1f} units | New total: {state.total_current_load:.1f}")
                for action in state.optimization_result.actions[1:-1]:  # Skip first and last (summary actions)
                    if action.startswith("Reduced"):
                        print(f"         → {action}")
        else:
            print(f"✓ Normal: {state.total_current_load:.1f} ≤ {state.transformer_capacity} (Pred: {state.predicted_load:.1f})")
    
    def _print_summary(self):
        """Print summary of 24-hour execution."""
        print("\n" + "=" * 80)
        print("24-HOUR EXECUTION SUMMARY")
        print("=" * 80)
        
        overload_hours = [s for s in self.state_history if s.is_overloaded]
        optimized_hours = [s for s in self.state_history if s.optimization_result]
        
        print(f"\nTotal Hours: {len(self.state_history)}")
        print(f"Overload Hours: {len(overload_hours)}")
        print(f"Optimized Hours (loads shed): {len(optimized_hours)}")
        
        if optimized_hours:
            total_shed = sum(
                s.optimization_result.predicted_load - s.optimization_result.optimized_load
                for s in optimized_hours
            )
            print(f"Total Load Shed: {total_shed:.2f} units")
            
            print("\nOverload Prevention Actions:")
            for state in optimized_hours:
                print(f"  Hour {state.hour:02d}: Shed {state.optimization_result.predicted_load - state.optimization_result.optimized_load:.2f} units")
        
        loads_data = {
            'hour': [s.hour for s in self.state_history],
            'total_load': [s.total_current_load for s in self.state_history],
            'capacity': [s.transformer_capacity for s in self.state_history],
            'overloaded': [s.is_overloaded for s in self.state_history]
        }
        
        summary_df = pd.DataFrame(loads_data)
        peak_load = summary_df['total_load'].max()
        min_load = summary_df['total_load'].min()
        avg_load = summary_df['total_load'].mean()
        
        print(f"\nLoad Statistics:")
        print(f"  Peak Load: {peak_load:.2f} units")
        print(f"  Min Load: {min_load:.2f} units")
        print(f"  Avg Load: {avg_load:.2f} units")
        print(f"  Capacity: {self.capacity} units")
    
    def get_state_history_dataframe(self) -> pd.DataFrame:
        """
        Convert state history to DataFrame for analysis.
        
        Returns:
            pd.DataFrame: Historical states
        """
        data = {
            'hour': [s.hour for s in self.state_history],
            'timestamp': [s.timestamp for s in self.state_history],
            'total_load': [s.total_current_load for s in self.state_history],
            'predicted_load': [s.predicted_load for s in self.state_history],
            'capacity': [s.transformer_capacity for s in self.state_history],
            'is_overloaded': [s.is_overloaded for s in self.state_history],
            'hospital': [s.current_loads['hospital'] for s in self.state_history],
            'residential': [s.current_loads['residential'] for s in self.state_history],
            'commercial': [s.current_loads['commercial'] for s in self.state_history],
            'ev_charging': [s.current_loads['ev_charging'] for s in self.state_history],
        }
        
        return pd.DataFrame(data)


def main():
    """Example usage of the SystemController."""
    # Initialize and execute
    controller = SystemController(transformer_capacity=150.0, verbose=True)
    states = controller.execute_24h()
    
    # Get results as DataFrame
    df = controller.get_state_history_dataframe()
    
    print("\n" + "=" * 80)
    print("DETAILED 24-HOUR STATE LOG")
    print("=" * 80)
    print(df.to_string(index=False))
    
    return controller, df


if __name__ == "__main__":
    main()
