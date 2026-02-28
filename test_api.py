import json
from udemy import UdemyAPI

token = "YK2ZFi/ZWUKP4t/sYc/baY3QgJdSH9TuOjiw/VhGdM8:FbyDH+Yd1+SIVJugA4DHiUZwOUSFOlAbl7alnGXj6KQ"
api = UdemyAPI(token)
courses = api.get_subscribed_courses()

course_id = None
for c in courses:
    if "Ionic" in c['title']:
        course_id = c['id']
        break

if course_id:
    print(f"Fetching curriculum for {course_id}...")
    curr = api.get_course_curriculum(course_id)
    for idx, item in enumerate(curr):
        if item.get('_class') == 'chapter' and 'Modals' in item.get('title', ''):
            print(f"Found Chapter: {item['title']}")
            # inspect a few lectures after this
            for i in range(1, 5):
                lec = curr[idx + i]
                print(f"Lecture: {lec.get('title')}")
                asset = api.get_lecture_asset(course_id, lec['id'])
                print(json.dumps(asset, indent=2))
            break
