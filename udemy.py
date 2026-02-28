from curl_cffi import requests

class UdemyAPI:
    def __init__(self, access_token):
        self.access_token = access_token
        self.headers = {
            "Cookie": f"access_token={self.access_token}",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }
        self.base_url = "https://www.udemy.com/api-2.0"

    def get_subscribed_courses(self):
        """Fetches a list of enrolled courses."""
        courses = []
        page = 1
        url = f"{self.base_url}/users/me/subscribed-courses?page_size=100"
        
        while url:
            try:
                response = requests.get(url, headers=self.headers, impersonate="chrome")
                response.raise_for_status()
                data = response.json()
                
                for item in data.get('results', []):
                    courses.append({
                        "id": item.get('id'),
                        "title": item.get('title'),
                        "url": item.get('url')
                    })
                
                url = data.get('next')
                page += 1
            except requests.exceptions.RequestException as e:
                return {"error": "Failed to fetch courses. Token might be invalid or expired.", "details": str(e)}
                
        return {"courses": courses}

    def get_course_curriculum(self, course_id):
        """Fetches the curriculum for a specific course ID."""
        url = f"{self.base_url}/courses/{course_id}/subscriber-curriculum-items?page_size=100&fields[lecture]=title,object_index,is_published,sort_order,created,asset,supplementary_assets,is_free&fields[quiz]=title,object_index,is_published,sort_order,type&fields[practice]=title,object_index,is_published,sort_order,type&fields[chapter]=title,object_index,is_published,sort_order&fields[asset]=title,filename,asset_type,status,time_estimation,is_external"
        
        curriculum = []
        page = 1
        
        while url:
            try:
                response = requests.get(url, headers=self.headers, impersonate="chrome")
                response.raise_for_status()
                data = response.json()
                
                curriculum.extend(data.get('results', []))
                url = data.get('next')
                page += 1
            except requests.exceptions.RequestException as e:
                return {"error": "Failed to fetch curriculum.", "details": str(e)}
                
        return {"curriculum": curriculum}

    def get_lecture_asset(self, course_id, lecture_id):
        """Fetches the stream URLs for a lecture asset."""
        url = f"{self.base_url}/users/me/subscribed-courses/{course_id}/lectures/{lecture_id}/?fields[lecture]=asset,description,download_url&fields[asset]=asset_type,stream_urls,download_urls,length,media_license_token,course_is_drmed"
        
        try:
            response = requests.get(url, headers=self.headers, impersonate="chrome")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": "Failed to fetch lecture asset.", "details": str(e)}

    def get_supplementary_asset(self, course_id, lecture_id, asset_id):
        """Fetches download URL for a supplementary asset (like .zip)."""
        url = f"{self.base_url}/users/me/subscribed-courses/{course_id}/lectures/{lecture_id}/supplementary-assets/{asset_id}/?fields[asset]=download_urls"
        try:
            response = requests.get(url, headers=self.headers, impersonate="chrome")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": "Failed to fetch supplementary asset.", "details": str(e)}
