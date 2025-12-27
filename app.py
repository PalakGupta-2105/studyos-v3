# -*- coding: utf-8 -*-
import streamlit as st
import time
import os
from datetime import datetime
from modules.ui import load_css
from modules.data_manager import (
    load_data, save_data, add_item_to_path, 
    save_temp_file, upload_and_delete, 
    save_generated_notes_to_drive, read_notes_from_drive,
    update_generated_notes, delete_drive_file, update_teacher_learning
)
from modules.ai_engine import generate_hybrid_notes, learn_from_edits

# ==========================================
# 1. SETUP & SESSION STATE
# ==========================================
if 'study_data' not in st.session_state:
    st.session_state.study_data = load_data()

defaults = {
    'theme': 'light',
    'path': [],
    'study_start': None,
    'total_hours': 142.0,
    'edit_mode': False,  # Track if we are editing notes
    'clipboard_formula': "" # For the formula editor
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

st.set_page_config(page_title="StudyOS Cloud", layout="wide")
load_css(st.session_state['theme'])

def get_current_data():
    data = st.session_state.study_data
    for step in st.session_state.path:
        data = data.get(step, {})
    return data

# ==========================================
# 2. HELPER UI FUNCTIONS
# ==========================================
def split_screen_formula_editor():
    
    """
    Renders the Input (Left) and Live Preview (Right) for LaTeX.
    """
    st.markdown("### ➗ Formula Editor")
    c_edit, c_view = st.columns(2)
    
    with c_edit:
        # The Raw Input
        formula_input = st.text_area(
            "Type LaTeX Code:", 
            value=r"\beta = \frac{I_c}{I_b}", 
            height=100,
            help="Type standard LaTeX. No need for $$ dollars."
        )
        
    with c_view:
        # The Live Preview
        st.markdown("**Live Preview:**")
        st.markdown(f"""
        <div class="latex-preview-box">
            $${formula_input}$$
        </div>
        """, unsafe_allow_html=True)
        
    # The Save Action
    if st.button("➕ Insert Formula into Notes"):
        # This copies it to a session variable (or you can manually copy-paste)
        st.session_state.clipboard_formula = f"$$ {formula_input} $$"
        st.success(f"Copied: $$ {formula_input} $$")
def block_style_inserter():
    """
    Helper to generate the HTML div wrappers for colorful blocks.
    """
    with st.expander("🎨 Insert Colored Block"):
        block_type = st.selectbox("Block Type", ["🚀 GATE Trap (Orange)", "🧠 Concept (Green)", "❓ Doubt (Pink)"])
        block_content = st.text_area("Content inside the box:", height=80)
        
        if st.button("Generate Block Code"):
            css_class = "block-trap" if "Trap" in block_type else "block-concept" if "Concept" in block_type else "block-doubt"
            
            # The HTML code to paste
            code_snippet = f'<div class="{css_class}">\n{block_content}\n</div>'
            st.code(code_snippet, language="html")
            st.caption("Copy the code above and paste it into your editor.")
# ==========================================
# 3. SIDEBAR (NAVIGATION)
# ==========================================
with st.sidebar:
    st.title("StudyOS v3 ☁️")
    if st.button("🏠 HOME", use_container_width=True):
        st.session_state.path = []
        st.rerun()
    
    if st.session_state.path:
        st.markdown("### 📍 Path")
        for i, step in enumerate(st.session_state.path):
            if st.button(f"📂 {step}", key=f"nav_{i}", use_container_width=True):
                st.session_state.path = st.session_state.path[:i+1]
                st.rerun()
    
    st.markdown("---")
    if st.button("🌗 THEME", use_container_width=True):
        st.session_state.theme = 'dark' if st.session_state.theme == 'light' else 'light'
        st.rerun()

# ==========================================
# 4. MAIN INTERFACE
# ==========================================
current_data = get_current_data()
current_name = st.session_state.path[-1] if st.session_state.path else "Dashboard"
is_lecture = isinstance(current_data, dict) and current_data.get("type") == "lecture"

if is_lecture:
    # --- AUTO-TIMER LOGIC ---
    if 'active_lecture' not in st.session_state or st.session_state.active_lecture != current_name:
        st.session_state.active_lecture = current_name
        st.session_state.lecture_start_time = time.time()
    
    elapsed_seconds = time.time() - st.session_state.lecture_start_time
    elapsed_mins = int(elapsed_seconds // 60)

    # --- HEADER ---
    c_head1, c_head2 = st.columns([3, 1])
    with c_head1:
        st.title(f"📄 {current_name}")
    with c_head2:
        st.markdown(f"""
        <div style="text-align:center; padding: 10px; background-color: #e6fffa; border: 1px solid #00b386; border-radius: 5px; color: #00664d;">
            ⏱️ <b>{elapsed_mins} min</b>
        </div>
        """, unsafe_allow_html=True)

    if 'drive_ids' not in current_data:
        current_data['drive_ids'] = {}

    # --- TABS ---
    tab1, tab2 = st.tabs(["📝 AI NOTES & EDIT", "📅 REVISION HISTORY"])

    # === TAB 1: HYBRID NOTES ENGINE ===
    with tab1:
        notes_id = current_data['drive_ids'].get('notes_id')
        
        # A. IF NOTES EXIST: SHOW / EDIT
        if notes_id:
            # Fetch text from RAM (Cloud)
            if 'cached_notes' not in st.session_state or st.session_state.get('cached_id') != notes_id:
                st.session_state.cached_notes = read_notes_from_drive(notes_id)
                st.session_state.cached_id = notes_id
            
            cloud_text = st.session_state.cached_notes

            if cloud_text:
                # HEADER CONTROLS
                c_ctrl1, c_ctrl2 = st.columns([4, 1])
                with c_ctrl1:
                    st.caption("✅ Live from Google Drive (Zero Local Storage)")
                with c_ctrl2:
                    # EDIT TOGGLE
                    if st.button("✏️ EDIT MODE" if not st.session_state.edit_mode else "👀 VIEW MODE"):
                        st.session_state.edit_mode = not st.session_state.edit_mode
                        st.rerun()

                # CONTENT AREA
                if st.session_state.edit_mode:
                    # --- EDIT MODE (WIKI STYLE) ---
                    st.info("✏️ You are editing. AI is watching to learn your preferences.")
                    
                    # 1. The Split-Screen Formula Helper
                    split_screen_formula_editor()
                    
                    st.markdown("---")
                    
                    # 2. The Main Editor
                    new_text = st.text_area("Markdown Editor", value=cloud_text, height=600)
                    
                    if st.button("💾 SAVE & TEACH AI", use_container_width=True):
                        with st.spinner("Syncing to Cloud & Analyzing your edits..."):
                            
                            # A. Update File in Drive
                            new_id = update_generated_notes(new_text, st.session_state.path)
                            current_data['drive_ids']['notes_id'] = new_id
                            
                            # B. THE LEARNING LOOP (Secret AI Agent)
                            # We compare what was there (cloud_text) vs what you wrote (new_text)
                            learned_vocab = learn_from_edits(cloud_text, new_text)
                            
                            if learned_vocab:
                                # Update the profile for "Default" teacher
                                for old_word, new_word in learned_vocab.items():
                                    update_teacher_learning("Default", old_word, new_word)
                                st.toast(f"🧠 AI Learned: {learned_vocab}", icon="🎓")
                            
                            # C. Update Session Cache
                            st.session_state.cached_notes = new_text
                            st.session_state.cached_id = new_id
                            save_data(st.session_state.study_data)
                            
                            st.session_state.edit_mode = False
                            st.success("Saved & Learned!")
                            time.sleep(1.5)
                            st.rerun()
                else:
                    # --- VIEW MODE (INTERACTIVE) ---
                    # Render with handwritten aesthetic if needed
                   # ... inside View Mode ...
                    c_flag1, c_flag2 = st.columns([4, 1])
                    with c_flag1:
                        st.markdown(f'<div class="handwritten-text">{cloud_text}</div>', unsafe_allow_html=True)
                    with c_flag2:
                        # Quick Flag Feature
                        with st.popover("🚩 Flag"):
                            flag_comment = st.text_area("Why is this hard?")
                            if st.button("Log Mistake"):
                                from modules.data_manager import log_mistake
                                log_mistake(st.session_state.path[-2], st.session_state.path[-1], flag_comment)
                                st.success("Flagged!")
                    st.markdown("---")
                    st.download_button("📥 Download Copy", cloud_text, "notes.md")
                    
                    if st.button("🗑️ DELETE & RESET"):
                        # Delete notes from Cloud too? Maybe just unlink.
                        current_data['drive_ids'] = {}
                        save_data(st.session_state.study_data)
                        st.rerun()

            else:
                st.error("Error fetching notes. File might be deleted from Drive.")
                if st.button("Reset Link"):
                    current_data['drive_ids'] = {}
                    save_data(st.session_state.study_data)
                    st.rerun()

        # B. IF NO NOTES: UPLOAD & GENERATE
        else:
            st.info("Upload materials to generate the 'Process-and-Flush' notes.")
            
            c_up1, c_up2 = st.columns(2)
            with c_up1:
                pdf_file = st.file_uploader("1. Slides (PDF)", type=['pdf'])
            with c_up2:
                audio_file = st.file_uploader("2. Lecture (Audio)", type=['mp3', 'wav', 'm4a'])
            
            if pdf_file and st.button("✨ GENERATE NOTES (AUTO-CLEANUP)", use_container_width=True):
                status = st.empty()
                progress = st.progress(0)
                
                # 1. STAGING
                status.info("⏳ Step 1/4: Staging files locally...")
                pdf_temp, _ = save_temp_file(pdf_file)
                audio_temp = None
                if audio_file:
                    audio_temp, _ = save_temp_file(audio_file)
                progress.progress(25)
                
                # 2. AI GENERATION
                status.info("🧠 Step 2/4: AI is analyzing (this takes ~30s)...")
                # Using Default teacher persona for now
                ai_text = generate_hybrid_notes(pdf_temp, audio_temp, teacher_name="Default")
                progress.progress(60)
                
                # 3. CLOUD SYNC
                status.info("☁️ Step 3/4: Uploading Notes to Google Drive...")
                notes_drive_id = save_generated_notes_to_drive(ai_text, st.session_state.path)
                current_data['drive_ids']['notes_id'] = notes_drive_id
                progress.progress(80)
                
                # 4. TOTAL WIPEOUT (Delete Input Files from Laptop AND Cloud)
                status.info("🗑️ Step 4/4: Performing Total Wipeout...")
                
                # Note: We are deleting the local temp folder. 
                # Since we didn't upload the raw PDF/Audio to Drive in this flow (only notes),
                # we just need to clean the local disk.
                import shutil
                shutil.rmtree("temp_staging") 
                
                current_data['notes_date'] = datetime.now().strftime("%Y-%m-%d")
                save_data(st.session_state.study_data)
                
                progress.progress(100)
                status.success("Done! Laptop & Cloud storage clean.")
                time.sleep(1)
                st.rerun()

    # === TAB 2: REVISION HISTORY ===
    with tab2:
        st.markdown("#### 📅 Session Log")
        history = current_data.get('revision_history', [])
        
        if history:
            st.table(history)
        else:
            st.info("No sessions logged yet.")
            
        st.markdown("---")
        
        # AUTO-LOGGING
        c_log1, c_log2 = st.columns([2, 1])
        with c_log1:
            rev_type = st.selectbox("I studied:", ["📄 Notes", "⚡ Flashcards"], key="rev_type")
        with c_log2:
            time_val = st.number_input("Mins:", value=max(1, elapsed_mins), min_value=1)
            
        if st.button("✅ Finish & Log Session", use_container_width=True):
            new_entry = {
                "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "material": rev_type,
                "time_taken": f"{time_val}m",
                "status": "Completed"
            }
            current_data['revision_history'].append(new_entry)
            st.session_state.total_hours += (time_val/60)
            
            # Reset timer
            st.session_state.lecture_start_time = time.time()
            save_data(st.session_state.study_data)
            
            st.success("Logged!")
            time.sleep(1)
            st.rerun()

else:
    # --- FOLDER BROWSER / DASHBOARD ---
    
    # A. IF HOME SCREEN (Path is empty) -> SHOW DASHBOARD WIDGETS
    if not st.session_state.path:
        st.title("🚀 Central Command")
        
        # Import and Render Widgets
        from modules.dashboard_widgets import render_dashboard
        render_dashboard(current_data)
        
        st.markdown("---")
        st.subheader("📚 Your Library")
    
    # B. IF INSIDE A FOLDER -> SHOW STANDARD TITLE
    else:
        st.title(f"📂 {current_name}")
        st.subheader("Contents")

    # --- CONTENTS GRID (Standard for both Home & Folders) ---
    cols = st.columns(3)
    keys = [k for k in current_data.keys() if k not in ["type", "drive_ids", "tasks", "revision_history", "notes_date"]]
    
    if not keys:
        st.info("Empty folder. Add something below!")
        
    for i, key in enumerate(keys):
        item = current_data[key]
        is_lec = item.get("type") == "lecture"
        icon = "📄" if is_lec else "📂"
        
        if cols[i % 3].button(f"{icon} {key}", use_container_width=True):
            st.session_state.path.append(key)
            st.rerun()
            
    st.markdown("---")
    
    # --- CREATE NEW ITEM FORM ---
    with st.form("new_item"):
        c1, c2 = st.columns([3, 1])
        name = c1.text_input("New Item Name")
        type_ = c2.selectbox("Type", ["folder", "lecture"])
        if st.form_submit_button("Create"):
            if name:
                st.session_state.study_data = add_item_to_path(
                    st.session_state.study_data, st.session_state.path, name, type_)
                st.rerun()