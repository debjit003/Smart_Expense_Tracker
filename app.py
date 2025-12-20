import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
from datetime import datetime
import json
import os
import io

# ==========================================
# 1. SETUP & CONFIG
# ==========================================
st.set_page_config(page_title="Smart Wallet", page_icon="💳", layout="centered")

# --- CSS FOR MOBILE OPTIMIZATION ---
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            .stApp {margin-top: -50px;}
            div[data-testid="stMetricValue"] {font-size: 1.8rem;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# ==========================================
# 2. DATABASE HANDLER (Hybrid CSV/Firestore)
# ==========================================
class DataHandler:
    def __init__(self):
        self.csv_file = 'expenses.csv'
        self.use_cloud = False
        self.db = None
        
        # Check for Firebase secrets (Production Mode)
        if "firebase" in st.secrets:
            try:
                import firebase_admin
                from firebase_admin import credentials, firestore
                
                # Check if already initialized to avoid errors on reload
                if not firebase_admin._apps:
                    # UPDATED LOGIC: Handle both JSON string AND direct TOML format
                    secrets_conf = st.secrets["firebase"]
                    
                    if "text_key" in secrets_conf:
                        # Old JSON string format
                        key_dict = json.loads(secrets_conf["text_key"])
                    else:
                        # New Clean TOML format (converts Streamlit object to standard dict)
                        key_dict = dict(secrets_conf)
                        # Fix potential newline issues in private key
                        if "\\n" in key_dict["private_key"]:
                            key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
                    
                    cred = credentials.Certificate(key_dict)
                    firebase_admin.initialize_app(cred)
                
                self.db = firestore.client()
                self.use_cloud = True
            except Exception as e:
                st.warning(f"Cloud DB Error: {e}. Falling back to CSV.")
        
    def save_expense(self, date, category, amount, description):
        data = {
            "Date": date.strftime('%Y-%m-%d'),
            "Category": category,
            "Amount": float(amount),
            "Description": description,
            "Timestamp": datetime.now().isoformat()
        }
        
        if self.use_cloud:
            self.db.collection(u'expenses').add(data)
        else:
            df = pd.DataFrame([data])
            df.to_csv(self.csv_file, mode='a', header=not os.path.exists(self.csv_file), index=False)

    def load_expenses(self):
        if self.use_cloud:
            docs = self.db.collection(u'expenses').stream()
            data = [doc.to_dict() for doc in docs]
            if not data:
                return pd.DataFrame(columns=["Date", "Category", "Amount", "Description"])
            df = pd.DataFrame(data)
            df['Date'] = pd.to_datetime(df['Date'])
            return df.sort_values(by="Date", ascending=False)
        else:
            if os.path.exists(self.csv_file):
                df = pd.read_csv(self.csv_file)
                df['Date'] = pd.to_datetime(df['Date'])
                return df.sort_values(by="Date", ascending=False)
            return pd.DataFrame(columns=["Date", "Category", "Amount", "Description"])

    def delete_expense(self, row_identifier):
        if not self.use_cloud:
            df = self.load_expenses()
            df = df.drop(row_identifier)
            df.to_csv(self.csv_file, index=False)
        else:
            # Note: For Firestore, we ideally need the Document ID.
            # This simple version focuses on adding/viewing.
            # Implementing full delete requires fetching Doc IDs.
            pass

db = DataHandler()

# ==========================================
# 3. AI ENGINE (Google Gemini)
# ==========================================
def analyze_receipt_with_ai(image):
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        return None, 0.0, "Other", "API Key Missing!"

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')

    prompt = """
    Analyze this receipt image. Extract the following details in strictly JSON format:
    {
        "date": "YYYY-MM-DD",
        "total_amount": 0.00,
        "category": "Food/Transport/Shopping/Bills/Health/Entertainment/Other",
        "merchant": "Store Name"
    }
    If the date is missing, use today's date.
    Categorize strictly into one of the options provided based on the items.
    """
    
    try:
        response = model.generate_content([prompt, image])
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        return data.get("date"), data.get("total_amount"), data.get("category"), data.get("merchant")
    except Exception as e:
        return None, 0.0, "Other", f"AI Error: {str(e)}"

# ==========================================
# 4. MOBILE-FIRST UI LAYOUT
# ==========================================
def main():
    st.title("💰 Smart Wallet")
    
    tab1, tab2, tab3 = st.tabs(["➕ Add Expense", "📊 Insights", "📜 History"])

    # --- TAB 1: ADD EXPENSE ---
    with tab1:
        st.caption("Snap a receipt or enter manually")
        uploaded_file = st.file_uploader("Upload Receipt", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed")
        
        default_date = datetime.today()
        default_amount = 0.0
        default_cat = "Other"
        default_desc = ""

        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption="Processing...", width=150)
            
            if st.button("✨ Auto-Fill with AI", type="primary", use_container_width=True):
                with st.spinner("AI is reading your receipt..."):
                    ex_date, ex_amount, ex_cat, ex_desc = analyze_receipt_with_ai(image)
                    if ex_amount and ex_amount > 0:
                        st.toast("Receipt Scanned Successfully!", icon="✅")
                        try: default_date = datetime.strptime(ex_date, '%Y-%m-%d')
                        except: pass
                        default_amount = float(ex_amount)
                        default_cat = ex_cat
                        default_desc = ex_desc
                    else:
                        st.error(f"Failed: {ex_desc}")

        with st.form("expense_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1: date = st.date_input("Date", default_date)
            with col2: amount = st.number_input("Amount (₹)", value=default_amount, step=1.0)
            
            category = st.selectbox("Category", 
                ["Food", "Transport", "Shopping", "Bills", "Health", "Entertainment", "Other"], 
                index=["Food", "Transport", "Shopping", "Bills", "Health", "Entertainment", "Other"].index(default_cat) if default_cat in ["Food", "Transport", "Shopping", "Bills", "Health", "Entertainment", "Other"] else 6
            )
            desc = st.text_input("Note", value=default_desc)
            
            if st.form_submit_button("✅ Save Expense", use_container_width=True):
                if amount > 0:
                    db.save_expense(date, category, amount, desc)
                    st.toast(f"Saved ₹{amount}!", icon="🎉")
                    st.balloons()
                else:
                    st.warning("Amount must be greater than 0")

    # --- TAB 2: DASHBOARD ---
    with tab2:
        df = db.load_expenses()
        if not df.empty:
            total = df['Amount'].sum()
            avg = df['Amount'].mean()
            c1, c2 = st.columns(2)
            c1.metric("Total Spent", f"₹{total:,.0f}")
            c2.metric("Avg Txn", f"₹{avg:,.0f}")
            st.divider()
            st.subheader("By Category")
            st.bar_chart(df.groupby("Category")["Amount"].sum(), horizontal=True, color="#4CAF50")
            st.subheader("Daily Trend")
            st.line_chart(df.groupby("Date")["Amount"].sum(), color="#FF5722")
        else:
            st.info("No data yet.")

    # --- TAB 3: HISTORY ---
    with tab3:
        st.subheader("Recent Transactions")
        df = db.load_expenses()
        if not df.empty:
            display_df = df.copy()
            display_df['Date'] = display_df['Date'].dt.strftime('%d %b')
            st.dataframe(display_df[['Date', 'Category', 'Amount', 'Description']], use_container_width=True, hide_index=True)

if __name__ == '__main__':
    main()