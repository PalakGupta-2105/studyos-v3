import streamlit as st
import datetime
from modules.tools import generate_formula_codex, render_mistake_notebook

def calculate_brain_battery(subject_data):
    """Calculates Retention Health (0-100%)."""
    health = 100
    last_rev_date = None
    
    def find_latest_date(data):
        nonlocal last_rev_date
        if isinstance(data, dict):
            if "revision_history" in data and data["revision_history"]:
                last = data["revision_history"][-1]["date"]
                try:
                    d_obj = datetime.datetime.strptime(last, "%Y-%m-%d %H:%M").date()
                except:
                    try: 
                        d_obj = datetime.datetime.strptime(last, "%Y-%m-%d").date()
                    except: 
                        d_obj = datetime.date.today()
                
                if last_rev_date is None or d_obj > last_rev_date:
                    last_rev_date = d_obj
            for key, val in data.items():
                if isinstance(val, dict): 
                    find_latest_date(val)

    find_latest_date(subject_data)
    if last_rev_date:
        days_gap = (datetime.date.today() - last_rev_date).days
        health = max(0, 100 - (days_gap * 10)) 
    else: 
        health = 0
    return health

def search_database(data, query, path_prefix=[]):
    """Recursive search."""
    results = []
    query = query.lower()
    for key, val in data.items():
        if key in ["type", "drive_ids", "tasks", "revision_history", "notes_date", "vocabulary"]: 
            continue
        
        current_path = path_prefix + [key]
        if query in key.lower():
            item_type = val.get("type", "folder") if isinstance(val, dict) else "folder"
            results.append((key, current_path, item_type))
        if isinstance(val, dict):
            results.extend(search_database(val, query, current_path))
    return results

def render_dashboard(full_data):
    """Displays the Central Command Dashboard."""
    
    # TABS FOR ORGANIZATION
    tab_overview, tab_tools, tab_syllabus = st.tabs(["🧠 OVERVIEW", "🛠️ POWER TOOLS", "📊 SYLLABUS"])

    # --- TAB 1: OVERVIEW (Battery & Search) ---
    with tab_overview:
        st.markdown("### 🧠 Brain Battery")
        cols = st.columns(3)
        idx = 0
        for subject in full_data.keys():
            if subject in ["type", "revision_history", "drive_ids", "notes_date"]: 
                continue
                
            health = calculate_brain_battery(full_data[subject])
            
            # Color Logic
            color = "green" if health > 75 else "orange" if health > 40 else "red"
            
            with cols[idx % 3]:
                st.markdown(f"**{subject}**")
                st.progress(health / 100)
                st.caption(f"Health: {health}%")
            idx += 1
            
        st.markdown("---")
        st.markdown("### 🔍 Global Search")
        search_query = st.text_input("Search Library...", placeholder="Topic, Lecture name...")
        if search_query:
            results = search_database(full_data, search_query)
            if results:
                for name, path, item_type in results:
                    c1, c2 = st.columns([4, 1])
                    c1.write(f"**{name}** ({' > '.join(path)})")
                    if c2.button("Go", key=f"jump_{name}"):
                        st.session_state.path = path
                        st.rerun()
            else: 
                st.warning("No matches.")

    # --- TAB 2: POWER TOOLS (Codex & Mistakes) ---
    with tab_tools:
        c_tool1, c_tool2 = st.columns(2)
        
        with c_tool1:
            st.markdown("### 📜 Formula Codex")
            st.caption("Compiles all LaTeX $$ formulas from a subject into one sheet.")
            
            # Dropdown to pick subject
            subjects = [k for k in full_data.keys() if k not in ["type", "revision_history", "drive_ids", "notes_date"]]
            target_sub = st.selectbox("Select Subject", subjects)
            
            if st.button(f"Generate {target_sub} Codex"):
                with st.spinner("Scanning all cloud notes... (This might take a moment)"):
                    report = generate_formula_codex(target_sub, full_data[target_sub])
                    if report:
                        st.success("Codex Generated!")
                        st.download_button("📥 Download PDF/MD", report, f"{target_sub}_Codex.md")
                    else:
                        st.warning("No formulas found in this subject yet.")

        with c_tool2:
            render_mistake_notebook()

    # --- TAB 3: SYLLABUS (Real Tracker) ---
    with tab_syllabus:
        st.markdown("### 🏆 Syllabus Completion")
        
        # 1. Calculate Progress Recursively
        def get_progress(data):
            total_tasks = 0
            completed_tasks = 0
            
            if isinstance(data, dict):
                # Check for tasks list in this item
                if "tasks" in data:
                    for t in data["tasks"]:
                        total_tasks += 1
                        # Assuming format "- [x] Task" for completed
                        if "- [x]" in t or "- [X]" in t:
                            completed_tasks += 1
                            
                # Recurse
                for k, v in data.items():
                    if isinstance(v, dict):
                        t, c = get_progress(v)
                        total_tasks += t
                        completed_tasks += c
            
            return total_tasks, completed_tasks

        # 2. Render Bars for Top-Level Subjects
        for subject in full_data.keys():
            # Skip metadata keys
            if subject in ["type", "revision_history", "drive_ids", "notes_date"]: 
                continue
            
            # Get the numbers
            tot, com = get_progress(full_data[subject])
            
            # Display
            if tot > 0:
                percent = com / tot
                st.write(f"**{subject}** ({com}/{tot} Tasks)")
                st.progress(percent)
            else:
                st.write(f"**{subject}** (No checklists found)")
                st.caption("Add checklists inside lectures to track this.")