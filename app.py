"""
Streamlit Dashboard
Real-time visualization of the AI-Driven Transformer Load Optimization System.
Displays load profiles, predictions, optimization actions, and system status.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from controller import SystemController


def initialize_controller():
    """Initialize the system controller (cached for performance)."""
    if 'controller' not in st.session_state:
        st.session_state.controller = SystemController(
            transformer_capacity=150.0,
            verbose=False
        )
    return st.session_state.controller


def plot_load_profile(df):
    """Plot total load vs capacity over 24 hours."""
    fig = go.Figure()
    
    # Add capacity line
    fig.add_trace(go.Scatter(
        x=df['hour'],
        y=df['capacity'],
        mode='lines',
        name='Transformer Capacity',
        line=dict(color='red', width=3, dash='dash'),
        hovertemplate='<b>Capacity</b>: %{y:.1f}<extra></extra>'
    ))
    
    # Add actual load
    fig.add_trace(go.Scatter(
        x=df['hour'],
        y=df['total_load'],
        mode='lines+markers',
        name='Actual Load (After Optimization)',
        line=dict(color='green', width=2),
        marker=dict(size=6),
        fill='tozeroy',
        hovertemplate='<b>Hour %{x}:00</b><br>Load: %{y:.1f} units<extra></extra>'
    ))
    
    # Add predicted load
    fig.add_trace(go.Scatter(
        x=df['hour'],
        y=df['predicted_load'],
        mode='lines+markers',
        name='Predicted Load',
        line=dict(color='orange', width=2, dash='dot'),
        marker=dict(size=5),
        hovertemplate='<b>Hour %{x}:00</b><br>Predicted: %{y:.1f} units<extra></extra>'
    ))
    
    # Highlight overload periods
    overload_hours = df[df['is_overloaded']]['hour'].values
    if len(overload_hours) > 0:
        for hour in overload_hours:
            fig.add_vrect(
                x0=hour - 0.4, x1=hour + 0.4,
                fillcolor="red", opacity=0.1,
                line_width=0,
            )
    
    fig.update_layout(
        title='<b>24-Hour Load Profile with Optimization</b>',
        xaxis_title='Hour of Day',
        yaxis_title='Load (units)',
        hovermode='x unified',
        template='plotly_white',
        height=400,
        margin=dict(l=50, r=50, t=50, b=50),
    )
    
    return fig


def plot_zone_allocation(df):
    """Plot stacked area chart of zone-wise load allocation."""
    fig = go.Figure()
    
    # Add zones in order
    zones = ['hospital', 'residential', 'commercial', 'ev_charging']
    colors = {
        'hospital': '#FF6B6B',
        'residential': '#4ECDC4',
        'commercial': '#45B7D1',
        'ev_charging': '#FFA07A'
    }
    
    for zone in reversed(zones):  # Reversed for correct stacking order
        fig.add_trace(go.Scatter(
            x=df['hour'],
            y=df[zone],
            mode='lines',
            name=zone.replace('_', ' ').title(),
            line=dict(width=0.5, color=colors[zone]),
            fillcolor=colors[zone],
            fill='tonexty' if zone != zones[0] else 'tozeroy',
            hovertemplate=f'<b>{zone.replace("_", " ").title()}</b>: %{{y:.1f}} units<extra></extra>'
        ))
    
    fig.update_layout(
        title='<b>Zone-wise Load Allocation (Stacked)</b>',
        xaxis_title='Hour of Day',
        yaxis_title='Load (units)',
        hovermode='x unified',
        template='plotly_white',
        height=400,
        margin=dict(l=50, r=50, t=50, b=50),
    )
    
    return fig


def plot_overload_events(df):
    """Create a timeline of overload events and shedding actions."""
    overload_df = df[df['is_overloaded']].copy()
    
    if len(overload_df) == 0:
        fig = go.Figure()
        fig.add_annotation(
            text="No overload events detected in 24-hour period",
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16, color="green")
        )
        fig.update_layout(
            title='<b>Overload Events & Shedding Actions</b>',
            height=300,
            margin=dict(l=50, r=50, t=50, b=50),
        )
        return fig
    
    fig = go.Figure()
    
    # Add overload events as bars
    fig.add_trace(go.Bar(
        x=overload_df['hour'],
        y=overload_df['predicted_load'] - overload_df['capacity'],
        name='Load Shed (units)',
        marker_color='#FF6B6B',
        hovertemplate='<b>Hour %{x}:00</b><br>Shed: %{y:.1f} units<extra></extra>'
    ))
    
    fig.update_layout(
        title='<b>Overload Events & Load Shed</b>',
        xaxis_title='Hour of Day',
        yaxis_title='Load Shed (units)',
        template='plotly_white',
        height=300,
        margin=dict(l=50, r=50, t=50, b=50),
    )
    
    return fig


def main():
    """Main Streamlit app."""
    st.set_page_config(
        page_title="Load Optimizer Dashboard",
        page_icon="⚡",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Title
    st.markdown("# ⚡ AI-Driven Transformer Load Optimization System")
    st.markdown("### Smart Energy Management & Automated Load Control")
    
    # Initialize controller
    controller = initialize_controller()
    
    # Execute 24-hour simulation
    if st.button("🔄 Run 24-Hour Simulation", key="run_sim", use_container_width=True):
        with st.spinner("Running 24-hour simulation..."):
            controller.execute_24h()
            st.session_state.simulation_complete = True
            st.success("✓ Simulation complete!")
    
    if 'simulation_complete' not in st.session_state:
        st.info("👉 Click 'Run 24-Hour Simulation' to start the analysis")
        return
    
    # Get state history
    df = controller.get_state_history_dataframe()
    
    # Sidebar: System Configuration & Statistics
    with st.sidebar:
        st.markdown("### ⚙️ System Configuration")
        st.metric("Transformer Capacity", f"{controller.capacity:.0f} units")
        
        st.markdown("---")
        st.markdown("### 📊 24-Hour Statistics")
        
        overload_hours = len(df[df['is_overloaded']])
        optimized_hours = len(df[df['total_load'] < df['predicted_load']])
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Overload Hours", overload_hours)
            st.metric("Peak Load", f"{df['total_load'].max():.1f} units")
        with col2:
            st.metric("Optimized Hours", optimized_hours)
            st.metric("Avg Load", f"{df['total_load'].mean():.1f} units")
        
        if optimized_hours > 0:
            total_shed = (df['predicted_load'] - df['total_load']).sum()
            st.metric("Total Load Shed", f"{total_shed:.1f} units")
        
        st.markdown("---")
        st.markdown("### 🎯 System Status")
        if overload_hours == 0:
            st.success("✓ No overload events")
        else:
            st.warning(f"⚠️ {overload_hours} overload hours detected")
    
    # Main content area
    st.markdown("---")
    
    # Row 1: Load Profile
    st.markdown("### 📈 24-Hour Load Profile")
    fig_profile = plot_load_profile(df)
    st.plotly_chart(fig_profile, use_container_width=True)
    
    # Row 2: Zone allocation and Overload events (side by side)
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 🏢 Zone-wise Allocation")
        fig_zones = plot_zone_allocation(df)
        st.plotly_chart(fig_zones, use_container_width=True)
    
    with col2:
        st.markdown("### 🚨 Overload Events & Shedding")
        fig_overload = plot_overload_events(df)
        st.plotly_chart(fig_overload, use_container_width=True)
    
    # Row 3: Detailed data table
    st.markdown("---")
    st.markdown("### 📋 Detailed Hourly Data")
    
    # Format for display
    display_df = df.copy()
    display_df['timestamp'] = display_df['timestamp'].dt.strftime('%H:%M')
    display_df = display_df.rename(columns={
        'hour': 'Hour',
        'timestamp': 'Time',
        'total_load': 'Total Load',
        'predicted_load': 'Predicted Load',
        'hospital': 'Hospital',
        'residential': 'Residential',
        'commercial': 'Commercial',
        'ev_charging': 'EV Charging',
        'is_overloaded': 'Overloaded'
    })
    
    # Format numeric columns
    numeric_cols = ['Total Load', 'Predicted Load', 'Hospital', 'Residential', 'Commercial', 'EV Charging']
    for col in numeric_cols:
        display_df[col] = display_df[col].round(1)
    
    # Convert boolean to emoji
    display_df['Overloaded'] = display_df['Overloaded'].apply(
        lambda x: '⚠️ YES' if x else '✓ NO'
    )
    
    # Display table
    st.dataframe(
        display_df[['Hour', 'Time', 'Total Load', 'Predicted Load', 'Hospital', 
                    'Residential', 'Commercial', 'EV Charging', 'Overloaded']],
        use_container_width=True,
        height=400
    )
    
    # Row 4: Overload events log
    if len(controller.state_history) > 0:
        st.markdown("---")
        st.markdown("### 📝 Load Shedding Actions Log")
        
        actions_log = []
        for state in controller.state_history:
            if state.optimization_result and state.is_overloaded:
                for action in state.optimization_result.actions:
                    actions_log.append(f"**[Hour {state.hour:02d}:00]** {action}")
        
        if actions_log:
            st.markdown("\n".join(actions_log))
        else:
            st.info("✓ No load shedding actions required")
    
    # Footer
    st.markdown("---")
    st.markdown(
        """
        **System Features:**
        - 🔮 Load Prediction: Machine Learning (LinearRegression)
        - 🎯 Optimization: Proportional Fair Share Load Shedding
        - 🏥 Critical Protection: Hospital loads never reduced
        - 📊 Real-time Monitoring: Zone-wise tracking & alerts
        - 🚨 Automated Response: Load shedding when overload detected
        """
    )


if __name__ == "__main__":
    main()
