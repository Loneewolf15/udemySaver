from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import uvicorn
import os

# Import our customized Udemy API wrapper
from udemy import UdemyAPI

app = FastAPI(title="Udemy Downloader API")

# Mount the static frontend files
# We will serve the index.html on the root path later.
app.mount("/app", StaticFiles(directory="public"), name="public")

class TokenReq(BaseModel):
    access_token: str

class LoginReq(BaseModel):
    email: str
    password: str

@app.post("/api/login")
async def login(req: LoginReq):
    """
    Attempts to login via email and password instead of access_token.
    """
    res = UdemyAPI.login_with_credentials(req.email, req.password)
    
    if "error" in res:
        raise HTTPException(status_code=401, detail=res["error"])
        
    return {"status": "success", "access_token": res["access_token"]}

@app.post("/api/auth")
async def auth(req: TokenReq):
    """
    Validates the token by attempting to fetch the first page of courses.
    """
    api = UdemyAPI(req.access_token)
    res = api.get_subscribed_courses()
    
    if "error" in res:
        raise HTTPException(status_code=401, detail=res["error"])
        
    # If successful, we just return an OK status to the frontend
    return {"status": "success", "message": "Token is valid"}

@app.get("/api/courses")
async def get_courses(authorization: str = Header(None)):
    """
    Returns the list of enrolled courses.
    The frontend should send the token in the Authorization header.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization Header")
        
    api = UdemyAPI(authorization)
    res = api.get_subscribed_courses()
    
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
        
    return res

@app.get("/api/curriculum/{course_id}")
async def get_curriculum(course_id: int, authorization: str = Header(None)):
    """
    Returns the curriculum for a given course.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization Header")
        
    api = UdemyAPI(authorization)
    res = api.get_course_curriculum(course_id)
    
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])
        
    return res

@app.get("/api/resolve-download/{course_id}/{lecture_id}")
async def resolve_download(course_id: int, lecture_id: int, quality: str = None, authorization: str = Header(None)):
    """
    Resolves the direct .mp4 streaming URL for a lecture.
    If 'quality' is provided (e.g., '1080', '720'), it attempts to find that specific resolution.
    Otherwise, it defaults to the highest available.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization Header")
        
    api = UdemyAPI(authorization)
    asset_info = api.get_lecture_asset(course_id, lecture_id)
    
    if not asset_info:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    if "error" in asset_info:
        raise HTTPException(status_code=400, detail=asset_info["error"])
        
    asset = asset_info.get("asset", {})
    
    # Check for DRM
    if asset.get("course_is_drmed") or asset.get("media_license_token"):
         return {"status": "drm_locked", "message": "This video is DRM protected and cannot be downloaded."}
         
    # Try to extract stream URLs
    stream_urls = asset.get("stream_urls")
    if stream_urls:
         video_streams = stream_urls.get("Video", [])
         if video_streams:
             
             # If a specific quality is requested, try to find it
             if quality:
                 for stream in video_streams:
                     if str(stream.get("label")) == quality:
                         return {"status": "success", "url": stream.get("file"), "type": "video", "quality": quality}
             
             # Fallback to highest quality if specific one isn't found or requested
             try:
                 video_streams.sort(key=lambda x: int(x.get("label", "0")), reverse=True)
             except ValueError:
                 pass
             
             best_stream = video_streams[0]
             return {"status": "success", "url": best_stream.get("file"), "type": "video", "quality": best_stream.get("label")}
                 
    # Fallback to download_urls if stream_urls fails
    download_urls = asset.get("download_urls")
    if download_urls:
         video_downloads = download_urls.get("Video", [])
         if video_downloads:
             return {"status": "success", "url": video_downloads[0].get("file"), "type": "video"}
             
    raise HTTPException(status_code=404, detail="No suitable download link found for this non-DRM video.")

@app.get("/api/lecture-qualities/{course_id}/{lecture_id}")
async def lecture_qualities(course_id: int, lecture_id: int, authorization: str = Header(None)):
    """
    Returns the available video resolutions for a specific lecture.
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization Header")
        
    api = UdemyAPI(authorization)
    asset_info = api.get_lecture_asset(course_id, lecture_id)
    
    if not asset_info or "error" in asset_info:
        raise HTTPException(status_code=400, detail="Failed to fetch asset info")
        
    asset = asset_info.get("asset", {})
    
    if asset.get("course_is_drmed") or asset.get("media_license_token"):
         return {"is_drm": True, "qualities": []}
         
    qualities = []
    stream_urls = asset.get("stream_urls")
    if stream_urls and "Video" in stream_urls:
        for stream in stream_urls.get("Video", []):
            if stream.get("label"):
                qualities.append(str(stream.get("label")))
                
    # Sort qualities descending (e.g. 1080, 720, 480)
    try:
        qualities.sort(key=lambda x: int(x), reverse=True)
    except ValueError:
        pass
        
    return {"is_drm": False, "qualities": list(set(qualities))}

@app.get("/api/resolve-attachment/{course_id}/{lecture_id}/{asset_id}")
async def resolve_attachment(course_id: int, lecture_id: int, asset_id: int, authorization: str = Header(None)):
    """
    Resolves the direct downloading URL for a supplementary asset (like .zip or .txt).
    """
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization Header")
        
    api = UdemyAPI(authorization)
    supp_info = api.get_supplementary_asset(course_id, lecture_id, asset_id)
    
    if not supp_info:
        raise HTTPException(status_code=404, detail="Attachment not found")
        
    if "error" in supp_info:
        raise HTTPException(status_code=400, detail=supp_info["error"])
        
    download_urls = supp_info.get("download_urls", {})
    
    # It's usually under 'File'
    if "File" in download_urls and len(download_urls["File"]) > 0:
        file_url = download_urls["File"][0].get("file")
        if file_url:
             return {"status": "success", "url": file_url, "type": "attachment"}
             
    raise HTTPException(status_code=404, detail="Could not extract download link for attachment.")

@app.get("/")
async def root():
    # Redirect root to /app/index.html
    return RedirectResponse(url="/app/index.html", status_code=302)

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
