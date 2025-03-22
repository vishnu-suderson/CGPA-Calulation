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
    chrome_options.add_argument("--headless")  # Remove for visual debugging if needed
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--page-load-strategy=eager")
    chrome_options.add_argument("--window-size=1280,720")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-logging")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-animations")
    
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
        print("Opening login page...")
        driver.get("https://arms.sse.saveetha.com/")
        print("Page loaded. Current URL:", driver.current_url)

        wait = WebDriverWait(driver, 10)
        username_field = wait.until(EC.presence_of_element_located((By.ID, "txtusername")))
        password_field = driver.find_element(By.ID, "txtpassword")
        login_button = driver.find_element(By.ID, "btnlogin")

        print("Entering credentials...")
        username_field.send_keys(username)
        password_field.send_keys(password)
        login_button.click()

        print("Login button clicked. Waiting for redirection...")
        time.sleep(2)
        print("Current URL after login:", driver.current_url)

        if "Landing.aspx" not in driver.current_url:
            print("Login failed. Expected 'Landing.aspx' in URL but got:", driver.current_url)
            driver.quit()
            return None

        with logged_in_lock:
            logged_in_drivers[username] = driver
        print("Login successful and driver stored for user:", username)
        return driver
    except Exception as e:
        print("Login exception:", e)
        traceback.print_exc()
        try:
            driver.quit()
        except:
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

    # Get or create a logged-in driver
    with logged_in_lock:
        driver = logged_in_drivers.get(username)

    if not driver:
        print("No persistent session found. Logging in...")
        driver = login_and_store_driver(username, password)
        if not driver:
            return jsonify({"success": False, "message": "Login failed, please check credentials"})

    try:
        start_time = time.time()

        # Step 1: Navigate to Student Profile page
        print("Navigating to Student Profile page...")
        driver.get("https://arms.sse.saveetha.com/StudentPortal/DataProfile.aspx")
        print("Navigated to profile page. Current URL:", driver.current_url)

        # Retry mechanism to wait for non-empty 'dvname' text
        retries = 3
        profile_loaded = False
        for attempt in range(retries):
            try:
                wait_table = WebDriverWait(driver, 15)
                # Wait until the 'dvname' element is present and its text is non-empty.
                wait_table.until(lambda d: d.find_element(By.ID, "dvname").text.strip() != "")
                element = driver.find_element(By.ID, "dvname")
                print(f"Attempt {attempt+1}: 'dvname' element loaded with text: '{element.text.strip()}'")
                profile_loaded = True
                break
            except Exception as e:
                print(f"Attempt {attempt+1} failed: {e}")
                time.sleep(2)
        
        if not profile_loaded:
            print("Failed to load profile page after retries.")
            print("Current URL:", driver.current_url)
            print("Page Source snippet:", driver.page_source[:1000])
            return jsonify({"success": False, "message": "Failed to load profile page. Possibly logged out."})

        # Step 2: Extract student profile data
        print("Extracting student data...")
        student_data = driver.execute_script("""
            return {
                name: document.getElementById('dvname').textContent.trim(),
                regno: document.getElementById('dvregno').textContent.trim(),
                program: document.getElementById('dvprogram').textContent.trim(),
                imgUrl: document.getElementById('imgprofile').src
            };
        """)
        print("Student data extracted:", student_data)

        # Step 3: Navigate to Grades page
        print("Navigating to Grades page...")
        driver.get("https://arms.sse.saveetha.com/StudentPortal/MyCourse.aspx")
        print("Grades page loaded. Current URL:", driver.current_url)
        WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "tblGridViewComplete")))
        time.sleep(3)

        # Step 4: Extract grades data
        print("Extracting grades data...")
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
        print("Grades data extracted:", results)

        # Calculate CGPA
        if results:
            total_points = sum(course['points'] for course in results)
            cgpa = total_points / len(results)
        else:
            cgpa = 0

        elapsed = time.time() - start_time
        print(f"Total execution time: {elapsed:.2f}s")

        return jsonify({
            "success": True,
            "student_data": student_data,
            "courses": results,
            "cgpa": round(cgpa, 2),
            "execution_time": elapsed
        })
    except Exception as e:
        print("Fetch grades exception:", e)
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
        print("Navigating to Attendance Report page...")
        driver.get("https://arms.sse.saveetha.com/StudentPortal/AttendanceReport.aspx")
        print("Attendance page loaded. Current URL:", driver.current_url)
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.ID, "tblStudent")))
        print("Attendance table located.")

        # Log a snippet of the attendance table HTML for debugging
        table_html = driver.find_element(By.ID, "tblStudent").get_attribute("innerHTML")
        print("Attendance Table HTML snippet:", table_html[:500])

        attendance_data = driver.execute_script("""
            var table = document.getElementById('tblStudent');
            var rows = table.getElementsByTagName('tr');
            var attendance_info = [];
            console.log("Total rows found:", rows.length);
            for (var i = 1; i < rows.length; i++) {  // Assuming row 0 is header
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
        print("Attendance data extracted:", attendance_data)

        results = []
        for record in attendance_data:
            attended = record['attended']
            total = record['total']
            current_percentage = record['current_percentage']

            safe_leave = 0
            while (attended / (total + safe_leave + 1)) * 100 >= 80:
                safe_leave += 1

            need_to_attend = 0
            if current_percentage < 80:
                while ((attended + need_to_attend + 1) / (total + need_to_attend + 1)) * 100 < 80:
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
        print("Attendance exception:", e)
        traceback.print_exc()
        return jsonify({"success": False, "message": str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
