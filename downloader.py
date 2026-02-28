import os
import requests
import subprocess
from urllib.parse import urlparse

class Downloader:
    def __init__(self, base_dir="Downloads"):
        self.base_dir = base_dir
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)

    def sanitize_filename(self, filename):
        """Removes invalid characters from filenames."""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        return filename.strip()

    def create_course_dir(self, course_name):
        safe_name = self.sanitize_filename(course_name)
        course_path = os.path.join(self.base_dir, safe_name)
        if not os.path.exists(course_path):
            os.makedirs(course_path)
        return course_path
        
    def create_chapter_dir(self, course_path, chapter_index, chapter_title):
        safe_title = self.sanitize_filename(chapter_title)
        chapter_name = f"{chapter_index:02d} - {safe_title}"
        chapter_path = os.path.join(course_path, chapter_name)
        if not os.path.exists(chapter_path):
            os.makedirs(chapter_path)
        return chapter_path

    def download_file(self, url, destination_path):
        """Downloads a regular file with a progress bar."""
        if os.path.exists(destination_path):
            print(f"    File already exists: {os.path.basename(destination_path)}. Skipping.")
            return

        print(f"    Downloading to: {os.path.basename(destination_path)}")
        try:
            with requests.get(url, stream=True) as r:
                r.raise_for_status()
                total_length = r.headers.get('content-length')
                
                with open(destination_path, 'wb') as f:
                    if total_length is None: # no content length header
                        f.write(r.content)
                    else:
                        dl = 0
                        total_length = int(total_length)
                        for data in r.iter_content(chunk_size=4096):
                            dl += len(data)
                            f.write(data)
                            done = int(50 * dl / total_length)
                            print(f"\r[{'=' * done}{' ' * (50-done)}] {dl/(1024*1024):.2f}/{total_length/(1024*1024):.2f} MB", end='', flush=True)
            print() # Print newline after progress bar
        except Exception as e:
            print(f"\nError downloading {url}: {e}")

    def download_video_ytdlp(self, url, destination_path, title):
        """Uses yt-dlp to download m3u8 or mp4 videos."""
        if not destination_path.endswith('.mp4'):
            destination_path += '.mp4'
            
        if os.path.exists(destination_path):
            print(f"    Video already exists: {os.path.basename(destination_path)}. Skipping.")
            return
            
        print(f"    Downloading video: {title}")
        command = [
            'yt-dlp',
            '-o', destination_path,
            url
        ]
        
        try:
            subprocess.run(command, check=True)
        except subprocess.CalledProcessError as e:
            print(f"Error downloading video with yt-dlp: {e}")
            print("Note: Udemy DRM videos cannot be downloaded with this script.")
        except FileNotFoundError:
            print("yt-dlp is not installed or not in PATH. Please install it to download videos.")
