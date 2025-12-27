from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os

# CONSTANTS
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'service_account.json'
PARENT_FOLDER_NAME = "StudyOS_Data"

def authenticate():
    """Logs into the Google Service Account."""
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        return None
        
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES)
        return build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"Authentication Error: {e}")
        return None

def find_or_create_folder(service, folder_name, parent_id=None):
    """Finds a folder ID by name, or creates it if missing."""
    if not service: return None
    
    query = f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        query += f" and '{parent_id}' in parents"
        
    results = service.files().list(q=query, fields="files(id, name)").execute()
    items = results.get('files', [])
    
    if not items:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder'
        }
        if parent_id:
            file_metadata['parents'] = [parent_id]
        
        folder = service.files().create(body=file_metadata, fields='id').execute()
        return folder.get('id')
    else:
        return items[0]['id']

def upload_to_drive(local_path, path_list):
    """Uploads file to Google Drive under the correct hierarchy."""
    service = authenticate()
    if not service: return None

    try:
        current_parent_id = find_or_create_folder(service, PARENT_FOLDER_NAME)
        for folder in path_list:
            current_parent_id = find_or_create_folder(service, folder, current_parent_id)
            
        file_name = os.path.basename(local_path)
        
        # Deduplication check
        query = f"name='{file_name}' and '{current_parent_id}' in parents and trashed=false"
        results = service.files().list(q=query).execute()
        if results.get('files', []):
            return results.get('files', [])[0]['id']

        # Upload
        file_metadata = {'name': file_name, 'parents': [current_parent_id]}
        media = MediaFileUpload(local_path, resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        return file.get('id')
        
    except Exception as e:
        print(f"⚠️ Upload Failed: {e}")
        return None

def delete_file_from_drive(file_id):
    """
    PERMANENTLY deletes a file from Google Drive.
    Used for the 'Total Wipeout' feature.
    """
    service = authenticate()
    if not service or not file_id: return False

    try:
        service.files().delete(fileId=file_id).execute()
        print(f"🗑️ Deleted from Cloud: {file_id}")
        return True
    except Exception as e:
        print(f"⚠️ Cloud Deletion Failed: {e}")
        return False