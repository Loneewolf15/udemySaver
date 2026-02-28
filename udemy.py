from curl_cffi import requests

class UdemyAPI:
    def __init__(self, access_token=None):
        self.access_token = access_token
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
        }
        if self.access_token:
            self.headers["Cookie"] = f"access_token={self.access_token}"
            self.headers["Authorization"] = f"Bearer {self.access_token}"
            
        self.base_url = "https://www.udemy.com/api-2.0"

    @staticmethod
    def login_with_credentials(email, password):
        """
        Attempts to authenticate using an email and password.
        Returns the access_token if successful, or an error dictionary.
        """
        session = requests.Session(impersonate="chrome")
        try:
            # 1. Fetch CSRF token from the login page
            init_res = session.get("https://www.udemy.com/join/login-popup/")
            init_res.raise_for_status()
            csrf_token = session.cookies.get("csrftoken")
            
            if not csrf_token:
                return {"error": "Failed to initialize login session (No CSRF token)."}
                
            # 2. POST the credentials
            login_data = {
                "email": email,
                "password": password,
                "csrfmiddlewaretoken": csrf_token,
                "locale": "en_US"
            }
            headers = {
                "Referer": "https://www.udemy.com/join/login-popup/",
                "Origin": "https://www.udemy.com",
                "X-CSRFToken": csrf_token,
                "Accept": "application/json, text/plain, */*"
            }
            
            post_res = session.post("https://www.udemy.com/join/login-popup/", data=login_data, headers=headers)
            
            # Check if Udemy blocked us with a Captcha or returned incorrect credentials
            if post_res.status_code != 200:
                 if "captcha" in post_res.text.lower() or post_res.status_code == 403:
                     return {"error": "Udemy blocked the login request with a Captcha. Please use the access_token method."}
                 return {"error": f"Login failed: Incorrect email or password (Status {post_res.status_code})."}
                 
            # 3. Extract the access_token cookie
            access_token = session.cookies.get("access_token")
            if not access_token:
                # If 200 OK but no token, Udemy usually requires a 6-digit OTP or a browser security check.
                return {"error": "Login succeeded, but Udemy requires a 6-digit OTP or Captcha verification. Please use your browser to extract the access_token manually."}
                
            return {"access_token": access_token}
            
        except requests.exceptions.RequestException as e:
            return {"error": "Network error during login attempt.", "details": str(e)}

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
