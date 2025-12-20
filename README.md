💸 Smart Expense Tracker

A professional, scalable, and AI-powered personal finance application built with Streamlit. It leverages Google Gemini 2.5 for intelligent receipt scanning and Google Firestore for secure, multi-user cloud storage. Designed with a mobile-first responsive UI.

🚀 Key Features

🤖 AI Receipt Scanning: Automatically extracts Date, Amount, Category, and Merchant from receipt images using Google's Gemini 2.5 Flash model.

📋 Smart Paste: Supports direct image pasting from the clipboard for quick data entry.

🔐 Secure Authentication: Multi-user support with SHA-256 password hashing and duplicate username prevention.

☁️ Cloud Database: Real-time, scalable data storage using Google Firebase Firestore.

📊 Interactive Dashboard: Visualizes spending trends, category splits, and lifetime expenses using dynamic charts.

🚨 Smart Budget Alerts: Sets monthly budget limits and triggers visual warnings when spending exceeds 90%.

📱 Responsive Design: Adaptive layout that functions like a native app on mobile and offers a split-screen view on desktop.

🛠️ Tech Stack

Frontend: Streamlit (Python-based Web Framework)

AI Engine: Google Generative AI (Gemini 2.5 Flash)

Database: Google Firebase Firestore (NoSQL)

Data Manipulation: Pandas

Image Processing: Pillow (PIL)

Security: Python Hashlib (SHA-256)

⚙️ Installation & Setup

1. Clone the Repository

git clone [https://github.com/your-username/smart-expense-tracker.git]
cd smart-expense-tracker


2. Install Dependencies

pip install -r requirements.txt


3. Configure Secrets

The app requires API keys to function. Create a folder named .streamlit in the root directory and add a file named secrets.toml.

Format for .streamlit/secrets.toml:

# Google Gemini API Key
GEMINI_API_KEY = "AIzaSyD..."

# Firebase Service Account Credentials
[firebase]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
client_email = "..."
client_id = "..."
auth_uri = "[https://accounts.google.com/o/oauth2/auth](https://accounts.google.com/o/oauth2/auth)"
token_uri = "[https://oauth2.googleapis.com/token](https://oauth2.googleapis.com/token)"
auth_provider_x509_cert_url = "[https://www.googleapis.com/oauth2/v1/certs](https://www.googleapis.com/oauth2/v1/certs)"
client_x509_cert_url = "..."
private_key = """
-----BEGIN PRIVATE KEY-----
MIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQC...
-----END PRIVATE KEY-----
"""


Note: You can obtain the Gemini API key from Google AI Studio and the Firebase credentials from the Firebase Console.

4. Run the App

streamlit run app.py


📱 Usage Guide

Sign Up/Login: Create a unique username and password to access your private wallet.

Add Expense:

Scan: Upload or paste a receipt image and click "✨ Extract Details with AI".

Manual: Enter or edit details in the form on the right.

Set Budget: Go to the "Budget" tab to define your monthly limit.

Track: Monitor the "Dashboard" for real-time spending insights and budget alerts.

🔮 Future Roadmap (Scalability)

[ ] Pagination: Optimize database queries to load expenses in chunks (e.g., last 50 records) for enterprise-level scalability.

[ ] Export Data: Add functionality to export monthly reports as CSV/PDF.

[ ] Email Verification: Integrate SMTP for password recovery.

Built with ❤️ by Debjit Roy
