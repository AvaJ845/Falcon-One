#data_settings.py
import streamlit as st

def initialize_data_settings():
    """
    Initialize the app's data settings if they don't exist.
    """
    if 'use_mock_data' not in st.session_state:
        st.session_state.use_mock_data = False

def get_data_mode():
    """
    Get the current data mode - real or mock.
    
    Returns:
    bool: True if using mock data, False if using real data
    """
    return st.session_state.use_mock_data

def toggle_data_mode():
    """
    Toggle between real and mock data
    """
    st.session_state.use_mock_data = not st.session_state.use_mock_data
    
def add_data_settings_ui():
    """
    Add UI elements for data settings to the sidebar
    """
    st.sidebar.markdown("---")
    st.sidebar.subheader("Data Settings")
    
    data_mode = "Mock Data" if st.session_state.use_mock_data else "Real Data"
    toggle_label = f"Using {data_mode} - Click to Switch"
    
    if st.sidebar.button(toggle_label):
        toggle_data_mode()
        st.experimental_rerun()
    
    if st.session_state.use_mock_data:
        st.sidebar.info("Using simulated mock data. All visualizations show demo data.")
    else:
        st.sidebar.info("Using real-time market data from Yahoo Finance.")