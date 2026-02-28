"""
Load Prediction Layer
Uses LinearRegression to predict next-hour transformer load.
Simple and fast - designed for real-time predictions.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression


class LoadPredictionModel:
    """Predicts next-hour total load using LinearRegression."""
    
    def __init__(self):
        """Initialize the prediction model."""
        self.model = LinearRegression()
        self.is_trained = False
        self.lookback_hours = 3  # Use past 3 hours for prediction
    
    def train(self, df):
        """
        Train the model on historical demand data.
        
        Args:
            df: DataFrame with columns including 'hour', 'hospital', 'residential',
                'commercial', 'ev_charging', 'total_load'
        
        Returns:
            self: For method chaining
        """
        # Create features: hour and zone loads
        features = df[['hour', 'hospital', 'residential', 'commercial', 'ev_charging']].values
        targets = df['total_load'].values
        
        # Train the model
        self.model.fit(features, targets)
        self.is_trained = True
        
        return self
    
    def predict_next_hour(self, current_hour, current_loads):
        """
        Predict the total load for the next hour.
        
        Args:
            current_hour: Current hour (0-23)
            current_loads: Dict with keys 'hospital', 'residential', 'commercial', 'ev_charging'
        
        Returns:
            float: Predicted total load for next hour
        """
        if not self.is_trained:
            raise RuntimeError("Model must be trained before making predictions")
        
        next_hour = (current_hour + 1) % 24
        
        # Create feature vector for next hour
        features = np.array([[
            next_hour,
            current_loads.get('hospital', 0),
            current_loads.get('residential', 0),
            current_loads.get('commercial', 0),
            current_loads.get('ev_charging', 0)
        ]])
        
        # Get prediction
        predicted_load = self.model.predict(features)[0]
        
        # Ensure non-negative
        return max(predicted_load, 0)
    
    def predict_batch(self, df):
        """
        Predict loads for multiple hours.
        
        Args:
            df: DataFrame with required columns
        
        Returns:
            np.array: Predicted loads for each row
        """
        if not self.is_trained:
            raise RuntimeError("Model must be trained before making predictions")
        
        features = df[['hour', 'hospital', 'residential', 'commercial', 'ev_charging']].values
        predictions = self.model.predict(features)
        
        return np.maximum(predictions, 0)  # Ensure non-negative


def main():
    """Example usage of the LoadPredictionModel."""
    # import from the backend package
    from .simulator import DemandSimulator
    
    # Generate training data
    simulator = DemandSimulator()
    df = simulator.generate_24h_profile()
    
    # Train model
    model = LoadPredictionModel()
    model.train(df)
    
    print("=" * 60)
    print("Load Prediction Model - Validation Results")
    print("=" * 60)
    
    # Batch predictions
    predictions = model.predict_batch(df)
    
    # Show sample predictions vs actual
    comparison = pd.DataFrame({
        'hour': df['hour'],
        'actual_load': df['total_load'],
        'predicted_load': predictions,
        'error': np.abs(df['total_load'] - predictions)
    })
    
    print(comparison.to_string(index=False))
    print("\n")
    print(f"Mean Absolute Error: {comparison['error'].mean():.2f} units")
    print(f"Max Error: {comparison['error'].max():.2f} units")
    print(f"Model Weight (coefficient): {model.model.coef_}")
    print(f"Intercept: {model.model.intercept_:.2f}")
    
    return model, df


if __name__ == "__main__":
    main()
