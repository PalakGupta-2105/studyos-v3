import streamlit as st

def load_css(theme):
    # Determine colors based on theme (Keep your existing color logic here)
    if theme == 'dark':
        text_color = "#E0E0E0"
        bg_color = "#1E1E1E"
        handwritten_color = "#D6D6D6" # Off-white for dark mode
    else:
        text_color = "#1E1E1E"
        bg_color = "#FFFFFF"
        handwritten_color = "#2D2D2D" # Dark pencil gray

    st.markdown(f"""
    <style>
        /* Import the 'Kalam' handwritten font from Google */
        @import url('https://fonts.googleapis.com/css2?family=Kalam:wght@300;400;700&family=Patrick+Hand&display=swap');

        /* Apply to the 'Interactive Notes' container */
        .handwritten-text {{
            font-family: 'Kalam', cursive;
            font-size: 1.2rem;
            line-height: 1.6;
            color: {handwritten_color};
            background-color: {bg_color}; /* Paper-like background can be added here */
            padding: 20px;
            border-radius: 5px;
            white-space: pre-wrap; /* Preserves spacing */
        }}

        /* Custom Block Styles */
        .block-concept {{
            border-left: 5px solid #28a745;
            background-color: rgba(40, 167, 69, 0.1);
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 4px;
        }}
        
        .block-trap {{
            border-left: 5px solid #dc3545;
            background-color: rgba(220, 53, 69, 0.1);
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 4px;
        }}

        .block-doubt {{
            border-left: 5px solid #e83e8c; /* Pink */
            background-color: rgba(232, 62, 140, 0.1);
            padding: 10px;
            margin-bottom: 10px;
            border-radius: 4px;
        }}
        
        /* The Split-Screen Editor Style */
        .latex-preview-box {{
            border: 1px solid #ccc;
            padding: 20px;
            border-radius: 5px;
            min-height: 100px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.5rem;
        }}
    </style>
    """, unsafe_allow_html=True)

def render_handwritten_notes(content):
    """Helper to wrap text in the handwritten class."""
    st.markdown(f'<div class="handwritten-text">{content}</div>', unsafe_allow_html=True)