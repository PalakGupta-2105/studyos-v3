import google.generativeai as genai
import PyPDF2
import os
import time
import json
from dotenv import load_dotenv
from modules.data_manager import load_teacher_profiles

# Load API Key
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    print("⚠️ API Key missing! AI generation will fail.")
else:
    genai.configure(api_key=api_key)

def extract_text_from_pdf(pdf_path):
    """Reads text from the temporary PDF file."""
    try:
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
        return text
    except Exception as e:
        print(f"PDF Error: {e}")
        return ""

def upload_audio_to_gemini(audio_path):
    """Uploads audio to Gemini's temporary server."""
    print(f"🎧 Uploading audio to AI Brain: {os.path.basename(audio_path)}...")
    try:
        audio_file = genai.upload_file(path=audio_path)
        while audio_file.state.name == "PROCESSING":
            time.sleep(1)
            audio_file = genai.get_file(audio_file.name)
        if audio_file.state.name == "FAILED":
            raise ValueError("Audio processing failed.")
        return audio_file
    except Exception as e:
        print(f"Audio Upload Error: {e}")
        return None

def generate_hybrid_notes(pdf_path, audio_path=None, teacher_name="Default"):
    """
    Generates notes using the specific Teacher Persona.
    """
    inputs = []
    
    # 0. LOAD TEACHER PERSONA
    teacher_profile_text = ""
    profiles = load_teacher_profiles()
    
    if teacher_name in profiles:
        p_data = profiles[teacher_name]
        vocab_list = "\n".join([f"- Replace '{k}' with '{v}'" for k,v in p_data.get('vocabulary', {}).items()])
        
        teacher_profile_text = f"""
        **🎭 TEACHER PERSONA ACTIVE: {teacher_name}**
        **Vocabulary Preferences (STRICT):**
        {vocab_list}
        """
        print(f"🎭 Applied Persona: {teacher_name}")

    # 1. Add PDF Text
    if pdf_path:
        text = extract_text_from_pdf(pdf_path)
        inputs.append(f"LECTURE SLIDES CONTENT:\n{text[:30000]}")

    # 2. Add Audio
    if audio_path:
        audio_file = upload_audio_to_gemini(audio_path)
        if audio_file:
            inputs.append(audio_file)
            inputs.append("AUDIO RECORDING OF LECTURE (Hinglish).")

    # 3. The Prompt
    prompt = f"""
    You are an expert Professor for Competitive Exams (GATE/UPSC).
    Generate **Interactive Lecture Notes**.
    
    {teacher_profile_text}
    
    **CRITICAL RULE:** Output strict Markdown blocks.
    
    **STRUCTURE:**
    # [Lecture Title]
    
    ## 🧠 Concept Block: Core Intuition
    * **The 'Why':** Explain simply.
    * **Teacher's Hint:** Capture any 'Desi' mnemonics from audio.
    
    ---
    
    ## 📝 Derivation Block: Formulas & Math
    * Use LaTeX for math ($V_x$).
    
    ---
    
    ## 🔥 Exam Block: Critical Points
    * **High Yield:** Mark "Important" points with 🔥.
    * **Traps:** Mark mistakes with ⚠️.
    
    ---
    
    ## ⚡ Short Notes Block (Summary)
    (5-line cheat sheet).
    """
    
    inputs.append(prompt)

    print("🧠 AI Thinking...")
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(inputs)
        return response.text
    except Exception as e:
        return f"AI Error: {str(e)}"

def learn_from_edits(original_text, edited_text):
    """
    Compares the Original vs. Edited text to find vocabulary patterns.
    Returns a Dictionary of learned changes: {'Triangle Wave': 'Triangular Pulse'}
    """
    if original_text == edited_text:
        return {}
        
    prompt = f"""
    Compare these two texts. The User edited the Original.
    Did the user consistently replace a specific technical term with another?
    
    Return ONLY a JSON dictionary of the replacements. 
    Example: {{"Voltage": "Potential Difference"}}
    If no systematic pattern is found, return {{}}.
    
    Original:
    {original_text[:10000]}
    
    Edited:
    {edited_text[:10000]}
    """
    
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(prompt)
        # Clean up the response to ensure it's valid JSON
        json_str = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(json_str)
    except:
        return {}