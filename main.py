import sys
import os
from udemy import UdemyAPI
from downloader import Downloader

def main():
    print("=== Udemy Terminal Downloader ===")
    access_token = input("Enter your Udemy access_token: ").strip()
    
    if not access_token:
        print("Please provide a valid access_token.")
        sys.exit(1)
        
    api = UdemyAPI(access_token)
    
    courses = api.get_subscribed_courses()
    
    if not courses:
        print("No courses found or failed to authenticate.")
        sys.exit(1)

    print("\n--- Subscribed Courses ---")
    for idx, course in enumerate(courses, 1):
        print(f"{idx}. {course['title']}")
        
    print("--------------------------")
    
    try:
        choice = int(input("Select a course to download (number): "))
        if choice < 1 or choice > len(courses):
            print("Invalid choice.")
            sys.exit(1)
    except ValueError:
        print("Invalid input.")
        sys.exit(1)
        
    selected_course = courses[choice - 1]
    
    print(f"\nFetching curriculum for: {selected_course['title']} ...")
    curriculum = api.get_course_curriculum(selected_course['id'])
    
    if not curriculum:
        print("Failed to fetch curriculum.")
        sys.exit(1)
        
    dl = Downloader()
    course_path = dl.create_course_dir(selected_course['title'])
    
    current_chapter_title = "Uncategorized"
    current_chapter_index = 0
    current_chapter_path = course_path
    
    for item in curriculum:
        item_type = item.get('_class')
        
        if item_type == 'chapter':
            current_chapter_index += 1
            current_chapter_title = item.get('title')
            current_chapter_path = dl.create_chapter_dir(course_path, current_chapter_index, current_chapter_title)
            print(f"\n-> Chapter: {current_chapter_title}")
            
        elif item_type == 'lecture':
            lecture_title = item.get('title')
            lecture_id = item.get('id')
            object_index = item.get('object_index')
            
            safe_title = dl.sanitize_filename(f"{object_index:03d} - {lecture_title}")
            print(f"  * Lecture: {lecture_title}")
            
            # Fetch stream URLs
            asset_info = api.get_lecture_asset(selected_course['id'], lecture_id)
            if not asset_info:
                continue
                
            asset = asset_info.get('asset', {})
            stream_urls = asset.get('stream_urls', {})
            download_urls = asset.get('download_urls', {})
            
            # Prefer 1080p, else 720p, else 480p, else 360p
            video_url = None
            if stream_urls:
                videos = stream_urls.get('Video', [])
                if videos:
                    # sort by resolution descending or simply take the first if it's highest to lowest.
                    # Usually it's a list. We will just use yt-dlp on the first URL or the best download URL.
                    video_url = videos[0].get('file')

            # Alternative: direct download_url from 'download_urls'
            if not video_url and download_urls:
                 videos = download_urls.get('Video', [])
                 if videos:
                     video_url = videos[0].get('file')

            # Download video (if any)
            if video_url:
                dest_path = os.path.join(current_chapter_path, safe_title)
                print(f"    Downloading Video...")
                dl.download_video_ytdlp(video_url, dest_path, lecture_title)
            else:
                 print("    No video stream available (might be an article, DRM locked, or quiz).")
                 print("    [DEBUG] Asset Info:", asset)

            # Download supplementary assets (attachments)
            supplementary = item.get('supplementary_assets', [])
            for supp in supplementary:
                 supp_title = supp.get('title') or supp.get('filename') or "attachment"
                 supp_id = supp.get('id')
                 
                 print(f"    Attachment found: {supp_title}")
                 
                 if not supp_id:
                     print("      -> No asset ID found to download.")
                     continue
                     
                 # Fetch the actual download URL for the asset
                 supp_info = api.get_supplementary_asset(selected_course['id'], lecture_id, supp_id)
                 if supp_info and 'download_urls' in supp_info:
                     # Usually under File -> list of dicts with 'file' key
                     # Or sometimes directly under a different key depending on asset_type
                     download_urls = supp_info.get('download_urls', {})
                     file_url = None
                     
                     if 'File' in download_urls and len(download_urls['File']) > 0:
                         file_url = download_urls['File'][0].get('file')
                         
                     if file_url:
                         # Attempt to get extension from the URL or filename
                         ext = ""
                         if supp_title.find('.') == -1: # No extension in title
                             parsed_url = urlparse(file_url)
                             base_name = os.path.basename(parsed_url.path)
                             if '.' in base_name:
                                 ext = f".{base_name.split('.')[-1]}"
                         
                         safe_supp_title = dl.sanitize_filename(supp_title + ext)
                         
                         dest_path = os.path.join(current_chapter_path, safe_supp_title)
                         dl.download_file(file_url, dest_path)
                     else:
                         print("      -> Could not extract a valid download link from the asset info.")
                 else:
                     # If it's an external link, Udemy doesn't provide a direct file URL.
                     if supp.get('is_external'):
                         print("      -> This is an external link, not a downloadable file.")
                     else:
                         print("      -> Failed to fetch download info for this asset.")
                 
    print("\nDownload process completed.")

if __name__ == "__main__":
    main()
