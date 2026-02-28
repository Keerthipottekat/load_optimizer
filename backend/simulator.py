"""
Demand Simulation Layer
Generates synthetic time-series load data for 24 hours across multiple zones.
Each zone has realistic load patterns and priorities.
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta


class DemandSimulator:
    """Simulates realistic load patterns for different consumer zones."""
    
    def __init__(self, seed=42):
        """
        Initialize the simulator.
        
        Args:
            seed: Random seed for reproducibility
        """
        np.random.seed(seed)
        # Zone priorities: lower value = higher priority (cannot be shed)
        self.zones = {
            'hospital': {'priority': 1, 'base_load': 50},      # Highest priority, constant
            'residential': {'priority': 2, 'base_load': 30},   # Medium priority, peaks morning/evening
            'commercial': {'priority': 3, 'base_load': 40},    # Lower priority, daytime peak
            'ev_charging': {'priority': 4, 'base_load': 0}     # Lowest priority, evening spike
        }
    
    def _hospital_load(self, hourly_data):
        """Hospital load: constant throughout the day."""
        return np.full(24, self.zones['hospital']['base_load'])
    
    def _residential_load(self, hourly_data):
        """Residential load: peaks in morning (6-8 AM) and evening (6-10 PM)."""
        load = np.zeros(24)
        base = self.zones['residential']['base_load']
        
        # Morning peak (6-8 AM)
        load[6:9] = base + 15
        
        # Evening peak (6-10 PM)
        load[18:23] = base + 20
        
        # Off-peak hours
        load[0:6] = max(base - 10, 5)
        load[9:18] = base
        load[23] = max(base - 10, 5)
        
        return load
    
    def _commercial_load(self, hourly_data):
        """Commercial load: peaks during business hours (9 AM - 5 PM)."""
        load = np.zeros(24)
        base = self.zones['commercial']['base_load']
        
        # Business hours peak
        load[9:18] = base + 25
        
        # Reduced hours
        load[6:9] = base + 5
        load[18:22] = base + 5
        
        # Night/off-hours
        load[0:6] = max(base - 20, 5)
        load[22:24] = max(base - 20, 5)
        
        return load
    
    def _ev_charging_load(self, hourly_data):
        """EV charging load: evening spike (7-10 PM)."""
        load = np.zeros(24)
        
        # Evening surge for EV charging
        load[19:23] = 35
        
        # Minimal during day
        load[8:19] = 2
        load[0:8] = 0
        load[23] = 0
        
        return load
    
    def generate_24h_profile(self):
        """
        Generate 24-hour demand profile for all zones.
        
        Returns:
            pd.DataFrame: With columns for each zone + total load
        """
        hourly_data = np.arange(24)
        
        data = {
            'hour': hourly_data,
            'hospital': self._hospital_load(hourly_data),
            'residential': self._residential_load(hourly_data),
            'commercial': self._commercial_load(hourly_data),
            'ev_charging': self._ev_charging_load(hourly_data)
        }
        
        df = pd.DataFrame(data)
        
        # Add small random variation (noise)
        noise_cols = ['hospital', 'residential', 'commercial', 'ev_charging']
        for col in noise_cols:
            noise = np.random.normal(0, 0.5, len(df))
            df[col] = df[col] + noise
            df[col] = df[col].clip(lower=0)  # Ensure non-negative
        
        # Calculate total load
        df['total_load'] = df[noise_cols].sum(axis=1)
        
        # Add timestamp
        base_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        df['timestamp'] = [base_date + timedelta(hours=int(h)) for h in df['hour']]
        
        return df[['timestamp', 'hour', 'hospital', 'residential', 'commercial', 'ev_charging', 'total_load']]


def main():
    """Example usage of the DemandSimulator."""
    simulator = DemandSimulator()
    df = simulator.generate_24h_profile()
    
    print("=" * 60)
    print("24-Hour Demand Profile")
    print("=" * 60)
    print(df.to_string(index=False))
    print("\n")
    print(f"Peak Load: {df['total_load'].max():.2f} units")
    print(f"Min Load: {df['total_load'].min():.2f} units")
    print(f"Avg Load: {df['total_load'].mean():.2f} units")
    
    return df


if __name__ == "__main__":
    main()
