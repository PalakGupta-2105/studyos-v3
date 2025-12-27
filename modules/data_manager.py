import json
import os
import shutil
import io
from functools import lru_cache
from datetime import datetime  # <--- MAKE SURE YOU ADD THIS IMPORT

import streamlit as st
from google.api_core.exceptions import GoogleAPIError
from google.cloud import firestore
from modules.drive_sync import upload_to_drive, authenticate, delete_file_from_drive
from googleapiclient.http import MediaIoBaseDownload

TEMP_DIR = "temp_staging"

TEACHER_DB_FILE = "teacher_profiles.json"
USER_STATS_FILE = "user_stats.json"

class DataRepository:
    """Repository abstraction for user data stored in Firestore.

    Consumers call these methods without needing to know the storage backend.
    """

    def __init__(self, collection_name: str = "users") -> None:
        self._client = _cached_firestore_client()
        self._collection = self._client.collection(collection_name)

    def get_all(self) -> dict:
        """Return all user documents as a dict of {doc_id: data}.

        Fail-safe to an empty dict on errors.
        """
        try:
            docs = self._collection.stream()
        except GoogleAPIError as e:
            print(f"Could not load data from Firestore: {e}")
            return {}
        except Exception as e:
            print(f"Unexpected error loading Firestore data: {e}")
            return {}

        data: dict = {}
        for doc in docs:
            data[doc.id] = doc.to_dict() or {}
        return data

    def get_student_data(self, student_id: str) -> dict:
        """Return a single student's document by id, or {} if missing."""
        try:
            snap = self._collection.document(str(student_id)).get()
            return snap.to_dict() or {}
        except GoogleAPIError as e:
            print(f"Could not read student '{student_id}' from Firestore: {e}")
            return {}
        except Exception as e:
            print(f"Unexpected error reading student '{student_id}': {e}")
            return {}

    def save_student_data(self, student_id: str, payload: dict) -> None:
        """Upsert a single student's document."""
        if not isinstance(payload, dict):
            raise ValueError("save_student_data expects a dictionary payload.")
        try:
            self._collection.document(str(student_id)).set(payload or {})
        except GoogleAPIError as e:
            print(f"Could not save student '{student_id}' to Firestore: {e}")
        except Exception as e:
            print(f"Unexpected error saving student '{student_id}': {e}")

    def save_all(self, data: dict) -> None:
        """Batch-write all docs from a dict and remove stale ones.

        Input shape: {doc_id: payload_dict}
        """
        if not isinstance(data, dict):
            raise ValueError("save_all expects a dictionary payload.")

        try:
            existing_ids = {doc.id for doc in self._collection.stream()}
        except GoogleAPIError as e:
            print(f"Could not retrieve existing Firestore documents: {e}")
            existing_ids = set()
        except Exception as e:
            print(f"Unexpected error while reading Firestore documents: {e}")
            existing_ids = set()

        incoming_ids = {str(key) for key in data.keys()}
        batch = self._client.batch()

        # Upserts
        for doc_id, payload in data.items():
            doc_ref = self._collection.document(str(doc_id))
            batch.set(doc_ref, payload or {})

        # Deletes for stale docs
        for stale_id in existing_ids - incoming_ids:
            batch.delete(self._collection.document(stale_id))

        try:
            batch.commit()
        except GoogleAPIError as e:
            print(f"Could not save data to Firestore: {e}")
        except Exception as e:
            print(f"Unexpected error committing Firestore batch: {e}")

def _get_firestore_client():
    """Returns a cached Firestore client configured via Streamlit secrets."""
    credentials = st.secrets.get("gcp_service_account")
    if credentials:
        return firestore.Client.from_service_account_info(dict(credentials))

    project_id = st.secrets.get("gcp_project_id")
    if project_id:
        return firestore.Client(project=project_id)

    return firestore.Client()


@lru_cache(maxsize=1)
def _cached_firestore_client():
    return _get_firestore_client()


def load_data():
    """Backward-compatible loader: delegates to DataRepository.get_all()."""
    return DataRepository().get_all()


def save_data(data):
    """Backward-compatible saver: delegates to DataRepository.save_all()."""
    return DataRepository().save_all(data)

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