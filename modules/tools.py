import re
import streamlit as st
from modules.data_manager import read_notes_from_drive, load_user_stats

def extract_formulas_from_text(text):
    """
    Finds all LaTeX equations in a markdown string.
    Returns a list of formulas.
    """
    # Regex for $$ ... $$ (Display Math)
    display_math = re.findall(r'\$\$(.*?)\$\$', text, re.DOTALL)
    # Regex for $ ... $ (Inline Math) - Optional, can be noisy
    # inline_math = re.findall(r'\$(.*?)\$', text)
    
    return display_math

def generate_formula_codex(subject_name, subject_data):
    """
    Scans an entire subject folder (e.g., "Signals") for formulas.
    """
    compiled_formulas = []
    total_notes = 0
    
    def traverse(data, current_path):
        nonlocal total_notes
        if isinstance(data, dict):
            # Check if this is a lecture with notes
            if "drive_ids" in data and "notes_id" in data["drive_ids"]:
                notes_id = data["drive_ids"]["notes_id"]
                if notes_id:
                    # Download content from Cloud RAM
                    content = read_notes_from_drive(notes_id)
                    if content:
                        formulas = extract_formulas_from_text(content)
                        if formulas:
                            compiled_formulas.append({
                                "source": " > ".join(current_path),
                                "formulas": formulas
                            })
                            total_notes += 1
            
            # Recurse
            for key, val in data.items():
                if key not in ["drive_ids", "type"]:
                    traverse(val, current_path + [key])

    # Start scanning
    traverse(subject_data, [subject_name])
    
    # Generate Markdown Report
    report = f"# 📜 Formula Codex: {subject_name}\n"
    report += f"*Compiled from {total_notes} Lecture Notes*\n\n---\n"
    
    for item in compiled_formulas:
        report += f"### 📂 {item['source']}\n"
        for form in item['formulas']:
            report += f"$$ {form} $$\n\n"
        report += "---\n"
        
    return report

def render_mistake_notebook():
    """
    Displays the user's flagged mistakes and generates a PDF/Markdown report.
    """
    stats = load_user_stats()
    mistakes = stats.get("mistakes_log", [])
    
    if not mistakes:
        st.info("🎉 No active mistakes! Flag doubts in your notes to see them here.")
        return

    st.markdown(f"### 📕 Mistake Notebook ({len(mistakes)} Active)")
    
    # Filter by Subject
    subjects = list(set([m['subject'] for m in mistakes]))
    selected_sub = st.selectbox("Filter by Subject", ["All"] + subjects)
    
    filtered = [m for m in mistakes if selected_sub == "All" or m['subject'] == selected_sub]
    
    for m in filtered:
        with st.expander(f"🚩 {m['topic']} ({m['date']})", expanded=True):
            st.write(f"**My Doubt/Error:** {m['comment']}")
            st.caption(f"Subject: {m['subject']}")
            
            if st.button("✅ I Fixed This", key=f"fix_{m['topic']}"):
                # Logic to remove from list could be added here
                st.toast("Marked as resolved! (Logic to update JSON needed)")

    # Download Button
    report = "# 📕 My Mistake Notebook\n\n"
    for m in mistakes:
        report += f"## 🚩 {m['topic']}\n"
        report += f"*Date: {m['date']} | Subject: {m['subject']}*\n\n"
        report += f"> {m['comment']}\n\n---\n"
        
    st.download_button("📥 Download Mistake Report", report, "mistakes.md")