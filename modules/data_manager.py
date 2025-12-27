import json
import os
import shutil
import io
from datetime import datetime  # <--- MAKE SURE YOU ADD THIS IMPORT
from modules.drive_sync import upload_to_drive, authenticate, delete_file_from_drive
from googleapiclient.http import MediaIoBaseDownload

DB_FILE = "study_database.json"
TEMP_DIR = "temp_staging"

TEACHER_DB_FILE = "teacher_profiles.json"
USER_STATS_FILE = "user_stats.json"

def load_data():
    """Loads the database structure."""
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_data(data):
    """Saves the JSON database."""
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def clean_temp_folder():
    """Wipes the temp folder to ensure 0 storage usage on D:"""
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)

def save_temp_file(file_obj):
    """Saves a file TEMPORARILY to D: for uploading."""
    clean_temp_folder()
    
    file_path = os.path.join(TEMP_DIR, file_obj.name)
    with open(file_path, "wb") as f:
        f.write(file_obj.getbuffer())
        
    return file_path, file_obj.name

def upload_and_delete(local_path, path_list):
    """
    1. Uploads to Drive.
    2. Deletes local file.
    3. Returns Drive ID.
    """
    try:
        drive_id = upload_to_drive(local_path, path_list)
        if os.path.exists(local_path):
            os.remove(local_path)
        return drive_id
    except Exception as e:
        print(f"Error in process-and-flush: {e}")
        return None

def delete_drive_file(file_id):
    """Wrapper to delete a file from Cloud permanently."""
    return delete_file_from_drive(file_id)

def save_generated_notes_to_drive(content_string, path_list):
    """Saves Markdown text directly to Drive (via temp file)."""
    clean_temp_folder()
    
    # 1. Write temp file
    temp_path = os.path.join(TEMP_DIR, "generated_notes.md")
    with open(temp_path, "w", encoding="utf-8") as f:
        f.write(content_string)
        
    # 2. Upload to Drive
    drive_id = upload_to_drive(temp_path, path_list)
    
    # 3. Delete Temp
    os.remove(temp_path)
    
    return drive_id

def update_generated_notes(content_string, path_list):
    """
    Updates the existing notes by Overwriting them in the Cloud.
    Used when you click 'Save Edits'.
    """
    return save_generated_notes_to_drive(content_string, path_list)

def read_notes_from_drive(file_id):
    """Downloads notes from Drive DIRECTLY into RAM."""
    service = authenticate()
    if not service or not file_id: return None
    
    try:
        request = service.files().get_media(fileId=file_id)
        file_stream = io.BytesIO()
        downloader = MediaIoBaseDownload(file_stream, request)
        
        done = False
        while done is False:
            status, done = downloader.next_chunk()
            
        return file_stream.getvalue().decode('utf-8')
    except Exception as e:
        print(f"Could not read from Drive: {e}")
        return None

def add_item_to_path(full_data, path_list, new_name, item_type="folder"):
    """Creates folder structure in JSON database."""
    current = full_data
    for step in path_list:
        current = current.get(step, {})
        
    if item_type == "lecture":
        current[new_name] = {
            "type": "lecture",
            "drive_ids": {}, 
            "tasks": [],
            "revision_history": []
        }
    else:
        current[new_name] = {"type": "folder"}
        
    save_data(full_data)
    return full_data


def load_teacher_profiles():
    """Loads the AI's memory of teacher habits."""
    if not os.path.exists(TEACHER_DB_FILE):
        return {}
    with open(TEACHER_DB_FILE, 'r') as f:
        return json.load(f)

def save_teacher_profile(teacher_name, preferences):
    """Updates the 'Style DNA' for a specific teacher."""
    data = load_teacher_profiles()
    data[teacher_name] = preferences
    with open(TEACHER_DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def update_teacher_learning(teacher_name, original_term, corrected_term):
    """
    The 'Unsupervised Learning' Feedback Loop.
    If you correct 'Triangle Wave' -> 'Triangular Pulse', AI remembers.
    """
    profiles = load_teacher_profiles()
    if teacher_name not in profiles:
        profiles[teacher_name] = {"vocabulary": {}, "formatting": {}}
    
    # Save the preference
    profiles[teacher_name]["vocabulary"][original_term] = corrected_term
    
    with open(TEACHER_DB_FILE, 'w') as f:
        json.dump(profiles, f, indent=4)

def load_user_stats():
    """Loads your 'Brain Battery' data."""
    if not os.path.exists(USER_STATS_FILE):
        # Default starting stats
        return {
            "Signals & Systems": {"progress": 0, "retention": 100},
            "Analog Circuits": {"progress": 0, "retention": 100},
            "mistakes_log": []
        }
    with open(USER_STATS_FILE, 'r') as f:
        return json.load(f)

def log_mistake(subject, topic, flagged_comment):
    """Adds an entry to the 'Mistake Notebook'."""
    stats = load_user_stats()
    
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "subject": subject,
        "topic": topic,
        "comment": flagged_comment,
        "status": "active" # active = still getting it wrong
    }
    stats["mistakes_log"].append(entry)
    
    with open(USER_STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=4)