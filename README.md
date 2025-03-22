
# 🎓 Student Grade Fetcher 📊  

This is a **Flask web application** that allows students to log in to the **Saveetha ARMS** portal and fetch their grades  and Attendance using **Selenium** automation.  
The grades are then displayed in a clean, interactive **HTML table** with filtering and sorting options.

---

## 🚀 Features  

✅ **Secure Login** – Users enter their ARMS credentials to fetch grades.  
✅ **Automated Web Scraping** – Uses Selenium to log in and extract grades.  
✅ **CGPA Calculation** – Automatically calculates the CGPA based on grades.  
✅ **Interactive UI** – Search and sort courses dynamically.  
✅ **Fast API Response** – Flask handles data fetching and returns JSON.  
✅ **Mobile Responsive** – Works well on both desktop and mobile browsers.  

---

## 🛠 Technologies Used  

- **Backend:** Flask, Selenium  
- **Frontend:** HTML, CSS, JavaScript, jQuery, Axios  
- **Automation:** WebDriver Manager (for ChromeDriver)  
- **UI Styling:** Modern CSS for a clean look  

---

## 📌 Installation Guide  

### **1️⃣ Clone the Repository**  
```sh
git clone https://github.com/your-username/student-grade-fetcher.git
cd student-grade-fetcher
```

### **2️⃣ Set Up a Virtual Environment (Optional but Recommended)**  
```sh
python -m venv venv  
source venv/bin/activate  # On macOS/Linux
venv\Scripts\activate     # On Windows
```

### **3️⃣ Install Dependencies**  
Ensure you have **Python 3** installed, then install the required libraries:  
```sh
pip install -r requirements.txt
```

### **4️⃣ Run the Flask Server**  
```sh
python app.py
```

The server will start at:  
📌 **http://127.0.0.1:5000/**

---

## 📌 How to Use  

1️⃣ **Open the Web App:**  
   - Go to `http://127.0.0.1:5000/` in your browser.  

2️⃣ **Enter Credentials:**  
   - Provide your **ARMS Username** and **Password**.  

3️⃣ **Fetch Grades & Fetch Calculation:**  
   - Click **Fetch Grade**, and the server will log in and extract grades.  
   - Click **Fetch Calucaltion**, and the server will log in and extract grades.  

4️⃣ **View & Sort Data:**  
   - The extracted grades will be displayed in a **responsive table**.  
   - You can **search** for courses or **sort** columns.  

---

## 📌 Project Structure  

```
/student-grade-fetcher
│── /templates
│   ├── index.html        # Frontend UI with form and table
│── app.py                # Flask Backend & Selenium Automation
│── requirements.txt      # List of dependencies
|__ DockerFile
│── README.md             # Project Documentation
```

---

## 📌 API Details  

### **📌 `/fetch_grades` (POST Request)**
- **Request Body:**  
  ```json
  {
    "username": "your_username",
    "password": "your_password"
  }
  ```
- **Response Example (Success):**  
  ```json
  {
    "success": true,
    "cgpa": 8.5,
    "courses": [
      {
        "code": "CS101",
        "name": "Computer Science Basics",
        "grade": "A"
      },
      {
        "code": "MA102",
        "name": "Mathematics",
        "grade": "B"
      }
    ]
  }
  ```
- **Response Example (Error):**  
  ```json
  {
    "success": false,
    "message": "Invalid Credentials"
  }
  ```

---

## 📌 Troubleshooting  

### **1️⃣ ChromeDriver Issues?**  
- Ensure **Google Chrome** is installed.  
- Install WebDriver Manager:  
  ```sh
  pip install webdriver-manager
  ```
- If issues persist, update your ChromeDriver manually.

### **2️⃣ Server Not Running?**  
- Check if Flask is installed:  
  ```sh
  pip install flask
  ```
- Restart the server with:  
  ```sh
  python app.py
  ```

### **3️⃣ Grades Not Fetching?**  
- The website structure may have changed.  
- Increase the `WebDriverWait` timeout in `app.py`.  
- Make sure your **credentials are correct**.  

---

## 📌 Dependencies  

### **Install Manually (If Needed)**  
```sh
pip install flask selenium webdriver-manager requests
```

---


## 📞 Contact  

🔹 **Developer:** M.VISHNU SUDERSON  
🔹 **Email:** m.vishnusuderson@gmail.com  
🔹 **GitHub:** [Vishnu-suderson](https://github.com/vishnu-suderson/)  

---
