"""
Optimization Engine (Core Automation)
Implements constraint-based load optimization to prevent transformer overload.
Uses greedy approach: reduces lowest-priority loads first.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class OptimizationResult:
    """Result of an optimization run."""
    is_overload: bool
    predicted_load: float
    optimized_load: float
    original_loads: Dict[str, float]
    optimized_loads: Dict[str, float]
    actions: List[str]  # Log of which zones were reduced and by how much


class LoadOptimizer:
    """
    Optimizes load allocation to prevent transformer overload.
    Uses greedy algorithm: reduces lowest-priority loads first.
    """
    
    def __init__(self, transformer_capacity=150.0):
        """
        Initialize the optimizer.
        
        Args:
            transformer_capacity: Maximum safe load (units)
        """
        self.capacity = transformer_capacity
        
        # Zone priorities: lower value = higher priority (cannot be shed)
        self.zone_priorities = {
            'hospital': 1,      # Highest priority - NEVER reduce
            'residential': 2,
            'commercial': 3,
            'ev_charging': 4    # Lowest priority - reduce first
        }
    
    def is_overloaded(self, predicted_load: float) -> bool:
        """
        Check if predicted load exceeds capacity.
        
        Args:
            predicted_load: Predicted total load
        
        Returns:
            bool: True if load > capacity
        """
        return predicted_load > self.capacity
    
    def optimize(self, predicted_load: float, current_loads: Dict[str, float]) -> OptimizationResult:
        """
        Optimize load allocation if overloaded.
        
        Strategy:
        1. If not overloaded, return current loads unchanged
        2. If overloaded, reduce loads starting with lowest priority
        3. Hospital load (priority 1) is NEVER reduced
        4. Continue until total load ≤ capacity
        
        Args:
            predicted_load: Predicted total transformer load
            current_loads: Dict with zone loads {zone_name: load_value}
        
        Returns:
            OptimizationResult: Contains optimized loads and actions taken
        """
        actions = []
        
        # Store original loads
        original_loads = current_loads.copy()
        optimized_loads = current_loads.copy()
        
        # Check if overload condition
        if not self.is_overloaded(predicted_load):
            return OptimizationResult(
                is_overload=False,
                predicted_load=predicted_load,
                optimized_load=predicted_load,
                original_loads=original_loads,
                optimized_loads=optimized_loads,
                actions=["No overload detected. No action taken."]
            )
        
        # Overload detected - begin load shedding
        actions.append(f"OVERLOAD DETECTED: {predicted_load:.2f} > {self.capacity:.2f}")
        
        # Sort zones by priority (highest priority last - will be reduced last)
        zones_by_priority = sorted(
            self.zone_priorities.items(),
            key=lambda x: x[1],
            reverse=True  # Start with lowest priority first
        )
        
        current_total = sum(optimized_loads.values())
        deficit = current_total - self.capacity
        
        # Greedy load shedding
        for zone_name, priority in zones_by_priority:
            if deficit <= 0:
                break
            
            # Hospital (priority 1) is never reduced
            if zone_name == 'hospital':
                continue
            
            current_demand = optimized_loads[zone_name]
            
            # Try to shed as much as possible from this zone
            if current_demand > 0:
                # Shed minimum of (available demand, deficit)
                shed_amount = min(current_demand, deficit)
                
                optimized_loads[zone_name] -= shed_amount
                deficit -= shed_amount
                
                actions.append(
                    f"Reduced {zone_name}: {current_demand:.2f} → {optimized_loads[zone_name]:.2f} "
                    f"(shed {shed_amount:.2f})"
                )
        
        # If still overloaded after shedding all shedable loads
        if deficit > 0:
            actions.append(
                f"WARNING: Could not fully resolve overload. "
                f"Remaining deficit: {deficit:.2f}. "
                f"(Hospital load is protected and cannot be reduced)"
            )
        
        optimized_total = sum(optimized_loads.values())
        actions.append(f"Total load optimized: {current_total:.2f} → {optimized_total:.2f}")
        
        return OptimizationResult(
            is_overload=True,
            predicted_load=predicted_load,
            optimized_load=optimized_total,
            original_loads=original_loads,
            optimized_loads=optimized_loads,
            actions=actions
        )


def main():
    """Example usage of the LoadOptimizer."""
    optimizer = LoadOptimizer(transformer_capacity=150.0)
    
    print("=" * 70)
    print("Load Optimizer - Test Scenarios")
    print("=" * 70)
    
    # Scenario 1: No overload
    print("\nSCENARIO 1: Normal Load (No Overload)")
    print("-" * 70)
    loads_1 = {
        'hospital': 50,
        'residential': 30,
        'commercial': 40,
        'ev_charging': 15
    }
    predicted_1 = sum(loads_1.values())
    result_1 = optimizer.optimize(predicted_1, loads_1)
    
    print(f"Predicted Load: {result_1.predicted_load:.2f}")
    print(f"Capacity: {optimizer.capacity}")
    print(f"Status: {'OVERLOAD' if result_1.is_overload else 'NORMAL'}")
    print("\nActions:")
    for action in result_1.actions:
        print(f"  - {action}")
    print(f"\nOriginal Loads: {result_1.original_loads}")
    print(f"Optimized Loads: {result_1.optimized_loads}")
    
    # Scenario 2: Overload detected and resolved
    print("\n\nSCENARIO 2: Overload with Optimization")
    print("-" * 70)
    loads_2 = {
        'hospital': 50,
        'residential': 45,
        'commercial': 50,
        'ev_charging': 35
    }
    predicted_2 = sum(loads_2.values())
    result_2 = optimizer.optimize(predicted_2, loads_2)
    
    print(f"Predicted Load: {result_2.predicted_load:.2f}")
    print(f"Capacity: {optimizer.capacity}")
    print(f"Status: {'OVERLOAD' if result_2.is_overload else 'NORMAL'}")
    print("\nActions:")
    for action in result_2.actions:
        print(f"  - {action}")
    print(f"\nOriginal Loads: {result_2.original_loads}")
    print(f"Optimized Loads: {result_2.optimized_loads}")
    print(f"Load Reduced: {result_2.predicted_load - result_2.optimized_load:.2f} units")
    
    # Scenario 3: Severe overload
    print("\n\nSCENARIO 3: Severe Overload")
    print("-" * 70)
    loads_3 = {
        'hospital': 50,
        'residential': 60,
        'commercial': 60,
        'ev_charging': 40
    }
    predicted_3 = sum(loads_3.values())
    result_3 = optimizer.optimize(predicted_3, loads_3)
    
    print(f"Predicted Load: {result_3.predicted_load:.2f}")
    print(f"Capacity: {optimizer.capacity}")
    print(f"Status: {'OVERLOAD' if result_3.is_overload else 'NORMAL'}")
    print("\nActions:")
    for action in result_3.actions:
        print(f"  - {action}")
    print(f"\nOriginal Loads: {result_3.original_loads}")
    print(f"Optimized Loads: {result_3.optimized_loads}")
    print(f"Load Reduced: {result_3.predicted_load - result_3.optimized_load:.2f} units")
    
    return optimizer


if __name__ == "__main__":
    main()
