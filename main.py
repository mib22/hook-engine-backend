from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from google import genai
import shutil
import os
import json
import traceback
import time # <--- NEW IMPORT FOR THE WAITING ROOM

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Paste your API key here again!
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise ValueError("CRITICAL: GEMINI_API_KEY environment variable is missing!")
client = genai.Client(api_key=GEMINI_API_KEY)

@app.post("/analyze")
async def analyze_video(file: UploadFile = File(...)):
    print("\n" + "="*50)
    print(f"📥 NEW REQUEST INCOMING: {file.filename}")
    print("="*50)
    
    temp_file_path = f"temp_{file.filename}"
    video_file = None
    
    try:
        # Step 1: Save the file
        print("⏳ Step 1: Saving video to local computer...")
        with open(temp_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        print("✅ Step 1 Complete!")
            
        # Step 2: Upload to Gemini
        print("⏳ Step 2: Uploading video to Google Gemini servers...")
        video_file = client.files.upload(file=temp_file_path)
        print(f"✅ Step 2 Complete! Uploaded as: {video_file.name}")
        
        # ==========================================
        # NEW STEP 2.5: THE WAITING ROOM
        # ==========================================
        print("⏳ Step 2.5: Waiting for Google to digest the video...")
        while True:
            # Check the current status of the file on Google's servers
            file_info = client.files.get(name=video_file.name)
            # Handle the enum/string state safely
            state = file_info.state.name if hasattr(file_info.state, 'name') else str(file_info.state)
            
            if "ACTIVE" in state:
                print("✅ Step 2.5 Complete! Video is fully processed and ready.")
                break
            elif "FAILED" in state:
                raise Exception("Google servers failed to process this video file.")
            
            print("   Still processing... checking again in 3 seconds.")
            time.sleep(3)
        # ==========================================
        
        # Step 3: Analyze
        print("⏳ Step 3: Requesting AI Analysis (This takes 10-60 seconds)...")
        prompt = """
        Analyze this video and output ONLY a JSON object with this exact structure:
        {
          "recommended_clip": {"start_timestamp_seconds": 0.0, "end_timestamp_seconds": 0.0, "duration_explanation": "String"},
          "metadata": {"viral_title": "String", "hook_text": "String"},
          "typography_settings": {"primary_language": "String", "requires_rtl_formatting": false, "calligraphy_styling_notes": "String"}
        }
        """
        
        response = client.models.generate_content(
            model='gemini-2.5-pro',
            contents=[video_file, prompt]
        )
        print("✅ Step 3 Complete! AI Response received.")
        
        # Step 4: Parse JSON
        print("⏳ Step 4: Formatting data for mobile app...")
        raw_text = response.text.replace("```json\n", "").replace("```", "").strip()
        parsed_json = json.loads(raw_text)
        print("✅ Step 4 Complete! Sending successful response to phone.")
        
        return parsed_json
        
    except Exception as e:
        print("\n" + "❌"*25)
        print("CRITICAL ERROR DURING UPLOAD OR ANALYSIS!")
        traceback.print_exc() 
        print("="*50 + "\n")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        print("🧹 Cleaning up temporary files...")
        if video_file:
            try:
                client.files.delete(name=video_file.name)
                print("☁️ Deleted file from Gemini cloud.")
            except Exception as cleanup_error:
                print(f"⚠️ Failed to delete cloud file: {cleanup_error}")
                
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            print("🗑️ Deleted file from local computer.")
        print("🏁 Request cycle finished.\n")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)