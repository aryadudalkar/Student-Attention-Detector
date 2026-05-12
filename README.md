# SmartClass AI — Student Attention Detector

SmartClass AI is an intelligent classroom monitoring system that uses Computer Vision and Deep Learning to automatically track student attendance, monitor attention levels, and generate actionable feedback for teachers.

## 🚀 Key Features

- **Real-Time Attention Tracking:** Uses computer vision to analyze student posture, gaze, and activities to determine if they are attentive, distracted, or using their phones.
- **Facial Recognition Attendance:** Automatically identifies and tracks students across sessions using ArcFace embeddings.
- **Interactive Teacher Dashboard:** A beautiful, responsive React dashboard with dynamic charts (Recharts) visualizing the classroom's overall attention timeline.
- **AI-Generated Feedback Reports:** Analyzes session data to generate an automated feedback report highlighting peak distraction periods and offering recommendations for teachers.
- **PDF Generation & Email Delivery:** Generates structured PDF reports of session analytics that can be downloaded or emailed directly to teachers from the dashboard.
- **Student Management:** View individual student profiles, track their weekly engagement grades, and edit student details seamlessly.

---

## 🛠️ Technology Stack

### **Frontend**
- **React.js & Vite:** Fast, modern UI development.
- **Tailwind-inspired Custom CSS:** Glassmorphism UI, sleek dark mode aesthetics.
- **Recharts:** Interactive data visualization for attention timelines.
- **Lucide React:** Modern iconography.

### **Backend**
- **Python & Django REST Framework:** Robust API handling and database management.
- **SQLite:** Lightweight, built-in relational database.
- **ReportLab:** Dynamic PDF generation for session reports.
- **Django Core Mail:** Automated SMTP email dispatch system.

### **Computer Vision Pipeline**
- **OpenCV:** Real-time video processing and frame extraction.
- **YOLO (Ultralytics):** High-speed object detection (people, phones, books).
- **InsightFace / ArcFace:** State-of-the-art face recognition for student identification.

---

## 🧠 System Architecture

The system operates in three main interconnected layers:

1. **Detection Pipeline (`scripts/`):** Processes live webcam feeds or recorded videos frame-by-frame. It identifies faces, tracks objects (like phones), calculates an "attention score" based on posture/gaze, and streams this data to the backend via HTTP POST requests.
2. **Backend API (`backend/`):** Receives the continuous stream of attention logs. Once a session ends, it runs an aggregation algorithm to assign grades, find peak distraction periods, and auto-generate the Teacher Feedback summary.
3. **Frontend Dashboard (`frontend/`):** Pulls the aggregated data from the API and visualizes it. It provides controls to manage students, view historical sessions, download PDF reports, and trigger email deliveries.

---

## ⚙️ Setup & Installation

### 1. Prerequisites
- Python 3.10+
- Node.js 18+

### 2. Backend Setup
```bash
cd smart-classroom-attention-detection/backend

# Install Python dependencies
pip install -r requirements.txt
pip install reportlab

# Run database migrations
python manage.py migrate

# (Optional) Set environment variables for real email delivery
$env:SMTP_EMAIL="your-gmail@gmail.com"
$env:SMTP_PASSWORD="your-app-password"

# Start the Django server (or run .\start_backend.ps1 on Windows)
python manage.py runserver
```

### 3. Frontend Setup
```bash
cd smart-classroom-attention-detection/frontend

# Install Node dependencies
npm install

# Start the Vite development server
npm run dev
```

### 4. Running the Vision Pipeline
To simulate a classroom session and generate data for the dashboard:
```bash
cd smart-classroom-attention-detection/scripts

# Run on a sample video file
python video_test.py path/to/sample.mp4

# OR Run using your live webcam
python webcam_test.py
```

---

## 📊 Evaluation Metrics & Grading

The system assigns a grade based on the average attention score across the session:
- **A** (85-100%): Excellent engagement.
- **B** (70-84%): Good attention.
- **C** (55-69%): Moderate attention (mixed engagement).
- **D** (40-54%): Low attention.
- **F** (< 40%): Highly distracted.

*Note: The presence of a mobile phone drastically reduces the frame's instantaneous attention score.*
