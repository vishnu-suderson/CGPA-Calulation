from flask import Flask, render_template, request, jsonify
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
import threading
import traceback

app = Flask(__name__)

# Global dictionary to store persistent logged-in drivers keyed by username
logged_in_drivers = {}
logged_in_lock = threading.Lock()

def create_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # Use new headless mode for compatibility
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--page-load-strategy=eager")
    chrome_options.add_argument("--window-size=1280,720")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-animations")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    
    # Disable images, CSS, etc.
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2,
        "profile.managed_default_content_settings.stylesheets": 2,
        "profile.managed_default_content_settings.javascript": 1,
        "profile.default_content_setting_values.cookies": 1,
        "profile.managed_default_content_settings.plugins": 2,
        "profile.managed_default_content_settings.popups": 2,
        "profile.managed_default_content_settings.geolocation": 2,
        "profile.managed_default_content_settings.media_stream": 2,
    }
    chrome_options.add_experimental_option("prefs", prefs)
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.set_page_load_timeout(20)
    return driver

def login_and_store_driver(username, password):
    driver = create_driver()
    try:
        app.logger.info("Opening login page...")
        driver.get("https://arms.sse.saveetha.com/")
        app.logger.info("Page loaded. Current URL: %s", driver.current_url)

        wait = WebDriverWait(driver, 10)
        username_field = wait.until(EC.presence_of_element_located((By.ID, "txtusername")))
        password_field = driver.find_element(By.ID, "txtpassword")
        login_button = driver.find_element(By.ID, "btnlogin")

        app.logger.info("Entering credentials for user: %s", username)
        username_field.send_keys(username)
        password_field.send_keys(password)
        login_button.click()

        app.logger.info("Login button clicked. Waiting for redirection...")
        wait.until(EC.url_contains("Landing.aspx"))
        app.logger.info("Login successful. Current URL: %s", driver.current_url)

        with logged_in_lock:
            logged_in_drivers[username] = driver
        app.logger.info("Driver stored for user: %s", username)
        return driver
    except Exception as e:
        app.logger.error("Login exception: %s", e)
        traceback.print_exc()
        try:
            driver.quit()
        except Exception:
            pass
        return None

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/fetch_grades', methods=['POST'])
def fetch_grades():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return jsonify({"success": False, "message": "Missing credentials"})

    with logged_in_lock:
        driver = logged_in_drivers.get(username)

    if not driver:
        app.logger.info("No persistent session found. Logging in user: %s", username)
        driver = login_and_store_driver(username, password)
        if not driver:
            return jsonify({"success": False, "message": "Login failed, please check credentials"})

    try:
        start_time = time.time()
        app.logger.info("Navigating to Student Profile page for user: %s", username)
        driver.get("https://arms.sse.saveetha.com/StudentPortal/DataProfile.aspx")
        app.logger.info("Profile page loaded. Current URL: %s", driver.current_url)

        # Retry mechanism for non-empty 'dvname'
        retries = 3
        profile_loaded = False
        for attempt in range(retries):
            try:
                wait_profile = WebDriverWait(driver, 15)
                wait_profile.until(lambda d: d.find_element(By.ID, "dvname").text.strip() != "")
                element = driver.find_element(By.ID, "dvname")
                app.logger.info("Attempt %d: 'dvname' loaded with text: '%s'", attempt+1, element.text.strip())
                profile_loaded = True
                break
            except Exception as e:
                app.logger.warning("Attempt %d failed: %s", attempt+1, e)
                time.sleep(2)
        
        if not profile_loaded:
            app.logger.error("Failed to load profile page after %d attempts.", retries)
            app.logger.debug("Current URL: %s", driver.current_url)
            app.logger.debug("Page Source snippet: %s", driver.page_source[:1000])
            return jsonify({"success": False, "message": "Failed to load profile page. Possibly logged out."})

        app.logger.info("Extracting student profile data...")
        student_data = driver.execute_script("""
            return {
                name: document.getElementById('dvname').textContent.trim(),
                regno: document.getElementById('dvregno').textContent.trim(),
                program: document.getElementById('dvprogram').textContent.trim(),
                imgUrl: document.getElementById('imgprofile').src
            };
        """)
        app.logger.info("Student data extracted: %s", student_data)

        app.logger.info("Navigating to Grades page...")
        driver.get("https://arms.sse.saveetha.com/StudentPortal/MyCourse.aspx")
        app.logger.info("Grades page loaded. Current URL: %s", driver.current_url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "tblGridViewComplete")))
        time.sleep(2)  # Extra time for the table to fully render

        app.logger.info("Extracting grades data...")
        results = driver.execute_script("""
            var table = document.getElementById('tblGridViewComplete');
            var rows = table.getElementsByTagName('tr');
            var results = [];
            var gradePointMapping = {"S": 10, "A": 9, "B": 8, "C": 7, "D": 6, "E": 5};
            for (var i = 1; i < rows.length; i++) {
                var cells = rows[i].getElementsByTagName('td');
                if (cells.length < 6) continue;
                try {
                    var statusElement = cells[4].getElementsByTagName('span')[0];
                    var status = statusElement ? statusElement.textContent.trim() : '';
                    var grade = cells[3].textContent.trim();
                    if (status.toUpperCase() === "PASS" && grade in gradePointMapping) {
                        results.push({
                            code: cells[1].textContent.trim(),
                            name: cells[2].textContent.trim(),
                            grade: grade,
                            points: gradePointMapping[grade],
                            completed: cells[5].textContent.trim()
                        });
                    }
                } catch(e) {
                    console.log('Error processing row ' + i + ': ' + e.message);
                }
            }
            return results;
        """)
        app.logger.info("Grades data extracted: %s", results)

        cgpa = (sum(course['points'] for course in results) / len(results)) if results else 0
        elapsed = time.time() - start_time
        app.logger.info("Total execution time: %.2fs", elapsed)

        return jsonify({
            "success": True,
            "student_data": student_data,
            "courses": results,
            "cgpa": round(cgpa, 2),
            "execution_time": elapsed
        })
    except Exception as e:
        app.logger.error("Fetch grades exception: %s", e)
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)})

@app.route('/attendance', methods=['POST'])
def attendance():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")  # Optional if already logged in

    if not username:
        return jsonify({"success": False, "message": "Username is required to fetch attendance."})

    with logged_in_lock:
        driver = logged_in_drivers.get(username)

    if not driver:
        if not password:
            return jsonify({"success": False, "message": "Missing credentials for login."})
        driver = login_and_store_driver(username, password)
        if not driver:
            return jsonify({"success": False, "message": "Login failed, please check credentials"})

    try:
        app.logger.info("Navigating to Attendance Report page...")
        driver.get("https://arms.sse.saveetha.com/StudentPortal/AttendanceReport.aspx")
        app.logger.info("Attendance page loaded. Current URL: %s", driver.current_url)
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.ID, "tblStudent")))
        app.logger.info("Attendance table located.")

        table_html = driver.find_element(By.ID, "tblStudent").get_attribute("innerHTML")
        app.logger.debug("Attendance Table HTML snippet: %s", table_html[:500])

        attendance_data = driver.execute_script("""
            var table = document.getElementById('tblStudent');
            var rows = table.getElementsByTagName('tr');
            var attendance_info = [];
            for (var i = 1; i < rows.length; i++) {
                var cells = rows[i].getElementsByTagName('td');
                if (cells.length >= 7) {
                    var course = cells[2].textContent.trim();
                    var attended = parseInt(cells[3].textContent.trim());
                    var total = parseInt(cells[5].textContent.trim());
                    var percentage = parseFloat(cells[7].textContent.trim().replace('%', ''));
                    attendance_info.push({
                        course: course,
                        attended: attended,
                        total: total,
                        current_percentage: percentage
                    });
                }
            }
            return attendance_info;
        """)
        app.logger.info("Attendance data extracted: %s", attendance_data)

        results = []
        for record in attendance_data:
            attended = record['attended']
            total = record['total']
            current_percentage = record['current_percentage']

            safe_leave = 0
            while ((attended / (total + safe_leave + 1)) * 100) >= 80:
                safe_leave += 1

            need_to_attend = 0
            if current_percentage < 80:
                while (((attended + need_to_attend + 1) / (total + need_to_attend + 1)) * 100) < 80:
                    need_to_attend += 1

            results.append({
                "course": record['course'],
                "attended": attended,
                "total": total,
                "current_percentage": round(current_percentage, 2),
                "safe_leave_days": safe_leave,
                "classes_needed_for_80": need_to_attend
            })

        return jsonify({"success": True, "attendance": results})
    except Exception as e:
        app.logger.error("Attendance exception: %s", e)
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)})

@app.route("/robots.txt")
def robots():
    return Response(
        "User-agent: *\nAllow: /\nSitemap: https://cgpa-calulation.onrender.com/sitemap.xml",
        mimetype='text/plain'
    )

@app.route("/sitemap.xml")
def sitemap():
    sitemap_xml = '''<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://cgpa-calulation.onrender.com/</loc>
            <changefreq>monthly</changefreq>
            <priority>1.0</priority>
        </url>
    </urlset>'''
    return Response(sitemap_xml, mimetype='application/xml')

if __name__ == '__main__':
    # For production with Gunicorn, consider increasing the worker timeout:
    # gunicorn --bind 0.0.0.0:5000 --timeout 120 app:app
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
