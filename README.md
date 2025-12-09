# 🧾 Smart Expense Tracker with AI (OCR)

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://your-app-url-here.streamlit.app)
![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)

A robust full-stack data application that automates expense tracking. It uses **Computer Vision (OpenCV)** and **OCR (Tesseract)** to extract data from receipts, categorizes expenses using keyword logic, and visualizes spending habits via an interactive dashboard.

### App Screenshot:
<img width="969" height="2112" alt="image" src="https://github.com/user-attachments/assets/d469df61-a208-4d40-86e2-c4e85c3c0fe3" />

## 🚀 Key Features

* **AI-Powered Extraction:** Automatically detects **Date**, **Total Amount**, and **Category** from receipt images.
* **Dual-Mode OCR:** * *Photo Mode:* Uses thresholding & dilation for paper receipts.
    * *Digital Mode:* Uses Gaussian blurring to handle sharp digital screenshots.
* **Smart Categorization:** Auto-tags expenses (e.g., "Starbucks" → "Food", "Uber" → "Transport") using a keyword mapping engine.
* **Interactive Dashboard:** Visualizes spending trends and category breakdowns.
* **Data Management:** Edit, delete, and export data to **Excel (.xlsx)**.
* **Clipboard Support:** Paste images directly (`Ctrl+V`) for a seamless workflow.

## 🛠️ Tech Stack

* **Frontend:** [Streamlit](https://streamlit.io/) (Web UI)
* **OCR Engine:** [Tesseract 4.0](https://github.com/tesseract-ocr/tesseract)
* **Image Processing:** OpenCV (`cv2`), PIL
* **Data Manipulation:** Pandas, NumPy, Regex
* **Deployment:** Streamlit Community Cloud (Linux)

## ⚙️ Installation & Setup

### 1. Prerequisites
You must have **Tesseract OCR** installed on your system.
* **Windows:** [Download Installer here](https://github.com/UB-Mannheim/tesseract/wiki). Note the path (e.g., `C:\Program Files\Tesseract-OCR`).
* **Linux (Ubuntu):** `sudo apt install tesseract-ocr`
* **Mac:** `brew install tesseract`

### 2. Clone the Repository
```bash
git clone https://github.com/debjit003/Smart_Expense_Tracker.git
cd expense-tracker-ocr
```
### 3. Install Python Dependencies
```bash

pip install -r requirements.txt
```
### 4. Run the Application
```bash

streamlit run app.py
```
### 🧠 How It Works (The Logic)
Preprocessing: The raw image is converted to grayscale and upscaled (3x). Depending on the mode selected (Photo vs. Digital), OpenCV applies either Thresholding (to remove paper noise) or Gaussian Blur (to soften pixelated digital text).

Text Extraction: Tesseract OCR reads the processed image. Custom config flags (--psm 6) are used to optimize for block text.

Regex Parsing: * Amounts: A robust regex [\d.,]+ extracts numbers. A custom parser handles OCR errors like converting 17.999.00 (European style) to 17999.00 and fixing symbol misreads (e.g., ₹ read as 2).

Dates: Supports formats like DD-MM-YYYY, YYYY-MM-DD, and text-based dates like Feb 03, 2013.

Categorization: The extracted text is scanned against a dictionary of keywords to assign a category (Food, Transport, etc.).
