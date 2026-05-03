# 💰 Smart Expense Tracker

> An intelligent financial companion powered by Google Gemini AI and Firebase.

---

## 📖 About The Project

**Smart Expense Tracker** is not just a digital ledger — it's an intelligent financial companion. Whether you are snapping a photo of a dinner receipt or pasting a digital invoice, the AI parses the data instantly. Coupled with **Firebase Firestore**, your data is secure, synced, and scalable across devices.

---

## 🌟 Key Features

| Feature | Description |
|---|---|
| 🤖 **AI Receipt Parsing** | Extracts Date, Merchant, Category, and Amount from images with high precision using Gemini 2.5. |
| 🔐 **Secure Auth** | Custom-built authentication system using SHA-256 hashing to ensure user privacy and data separation. |
| ☁️ **Cloud Sync** | Real-time CRUD operations using Google Firestore. Your data is safe even if you close the browser. |
| 🚨 **Smart Alerts** | Visual warning system that triggers when you cross 90% of your defined monthly budget. |
| 📱 **Native Feel** | Optimized CSS removes standard web elements for an immersive, app-like experience on mobile. |
| 📋 **Clipboard Magic** | Custom Paste button allows direct image input from your clipboard — perfect for desktop users. |

---

## 🛠️ Tech Stack

This project is built using a modern, scalable architecture:

| Layer | Technology |
|---|---|
| **Frontend** | Streamlit (Rapid UI Development) |
| **Intelligence** | Google Gemini API (Multimodal Processing) |
| **Backend** | Firebase Firestore (NoSQL Database) |
| **Data Processing** | Pandas & Pillow |

---

## 🚀 Getting Started

Follow these steps to set up the project locally.

### ✅ Prerequisites

- Python 3.9+
- A Google Cloud Project (for Firebase)
- A Google AI Studio API Key

### 🔧 Installation

**1️⃣ Clone the repository**

```bash
git clone https://github.com/debjit003/smart-expense-tracker.git
cd smart-expense-tracker
```

**2️⃣ Install dependencies**

```bash
pip install -r requirements.txt
```

### 🔑 Setup Secrets

Create a file named `.streamlit/secrets.toml` and add your credentials:

```toml
GEMINI_API_KEY = "Your-Gemini-Key-Here"

[firebase]
type = "service_account"
project_id = "your-project-id"
private_key_id = "..."
client_email = "..."
# ... Add full Firebase JSON credentials here
```

### ▶️ Run the App

```bash
streamlit run app.py
```

---

## 📱 Usage

### 1️⃣ Dashboard

Upon logging in, you are greeted with a **split-view dashboard**:

- **Left panel** — Expense input form
- **Right panel** — AI-assisted receipt verification

### 2️⃣ Adding Expenses

- **Mobile:** Tap **Upload** to take a picture of your receipt.
- **Desktop:** Take a screenshot and click **Paste Image**.

The AI automatically fills the form — you just click **Save** ✅

### 3️⃣ Setting Budgets

Navigate to the **Budget** tab and set a monthly limit (e.g., ₹5000).

> 🚨 If your total expenses exceed ₹4500 (90% of budget), a **red alert** appears on your dashboard.

---

## 🔮 Future Roadmap

- [ ] 📊 **Data Export** — Download monthly reports as PDF / Excel
- [ ] 💱 **Multi-Currency Support** — USD / EUR conversion
- [ ] 🧠 **Category Learning** — AI learns your personal expense categorization
- [ ] 👤 **User Profile** — Password reset & profile picture updates

---

## 🤝 Contributing

Contributions make the open-source community an amazing place to learn and grow. Any contribution is **greatly appreciated**!

1. Fork the Project
2. Create your Feature Branch
   ```bash
   git checkout -b feature/AmazingFeature
   ```
3. Commit your Changes
   ```bash
   git commit -m "Add some AmazingFeature"
   ```
4. Push to the Branch
   ```bash
   git push origin feature/AmazingFeature
   ```
5. Open a Pull Request 🚀

---

## 📝 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.

---

## 📧 Contact

**Your Name**
- 📩 Email: [roydebjit2003@gmail.com](mailto:roydebjit2003@gmail.com)

🔗 **Project Link:** [https://github.com/debjit003/smart-expense-tracker](https://github.com/debjit003/smart-expense-tracker)
