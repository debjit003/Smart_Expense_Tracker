import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
from datetime import datetime
import json
import os
from streamlit_paste_button import paste_image_button

# ==========================================
# 1. SETUP & CONFIG
# ==========================================
st.set_page_config(page_title="Smart Wallet", page_icon="💳", layout="centered")

# --- CSS FOR MOBILE OPTIMIZATION ---
st.markdown("""
    <style>
    .stApp {margin-top: -30px;}
    div[data-testid="stMetricValue"] {font-size: 1.6rem;}
    button[kind="primary"] {width: 100%;}
    button[kind="secondary"] {width: 100%;}
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. DATABASE HANDLER
# ==========================================
class DataHandler:
    def __init__(self):
        self.csv_file = 'expenses.csv'
        self.use_cloud = False
        self.db = None
        
        if "firebase" in st.secrets:
            try:
                import firebase_admin
                from firebase_admin import credentials, firestore
                
                if not firebase_admin._apps:
                    secrets_conf = st.secrets["firebase"]
                    if "text_key" in secrets_conf:
                        key_dict = json.loads(secrets_conf["text_key"])
                    else:
                        key_dict = dict(secrets_conf)
                        if "\\n" in key_dict["private_key"]:
                            key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
                    
                    cred = credentials.Certificate(key_dict)
                    firebase_admin.initialize_app(cred)
                
                self.db = firestore.client()
                self.use_cloud = True
            except Exception as e:
                st.warning(f"Cloud DB Warning: {e}. Using CSV.")
        
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
            pass

db = DataHandler()

# ==========================================
# 3. AI ENGINE
# ==========================================
def analyze_receipt_with_ai(image):
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        return None, 0.0, "Other", "API Key Missing!"

    genai.configure(api_key=api_key)
    # Using the standard Flash model
    model = genai.GenerativeModel('gemini-2.5-flash')

    prompt = """
    Analyze this receipt image. Extract:
    {
        "date": "YYYY-MM-DD",
        "total_amount": 0.00,
        "category": "Food/Transport/Shopping/Bills/Health/Entertainment/Other",
        "merchant": "Store Name"
    }
    Use today's date if missing.
    """
    
    try:
        response = model.generate_content([prompt, image])
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        return data.get("date"), data.get("total_amount"), data.get("category"), data.get("merchant")
    except Exception as e:
        return None, 0.0, "Other", f"AI Error: {str(e)}"

# ==========================================
# 4. MOBILE-FRIENDLY UI
# ==========================================
def main():
    st.title("💰 Smart Wallet")
    
    # --- SESSION STATE INITIALIZATION (The Fix) ---
    if 'form_amount' not in st.session_state: st.session_state.form_amount = 0.0
    if 'form_date' not in st.session_state: st.session_state.form_date = datetime.today()
    if 'form_category' not in st.session_state: st.session_state.form_category = "Other"
    if 'form_desc' not in st.session_state: st.session_state.form_desc = ""
    
    tab1, tab2, tab3 = st.tabs(["➕ Add", "📊 Insights", "📜 History"])

    # --- TAB 1: ADD EXPENSE ---
    with tab1:
        st.write("### 1. Upload Receipt")
        
        col_up, col_paste = st.columns(2)
        with col_up:
            uploaded_file = st.file_uploader("Upload", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed")
        with col_paste:
            paste_result = paste_image_button(
                label="📋 Paste Image",
                background_color="#FF4B4B",
                hover_background_color="#FF0000",
            )

        image = None
        if uploaded_file:
            image = Image.open(uploaded_file)
        elif paste_result.image_data is not None:
            image = paste_result.image_data

        if image:
            st.image(image, caption="Receipt Preview", width=200)
            
            with st.container():
                if st.button("✨ Auto-Fill Details", type="primary"):
                    with st.spinner("AI is reading details..."):
                        ex_date, ex_amount, ex_cat, ex_desc = analyze_receipt_with_ai(image)
                        
                        if ex_amount and ex_amount > 0:
                            # SAVE TO SESSION STATE
                            st.session_state.form_amount = float(ex_amount)
                            st.session_state.form_category = ex_cat
                            st.session_state.form_desc = ex_desc
                            try:
                                st.session_state.form_date = datetime.strptime(ex_date, '%Y-%m-%d')
                            except:
                                st.session_state.form_date = datetime.today()
                                
                            st.toast("Success! Details updated.", icon="✅")
                            st.rerun() # Force refresh so form picks up new values
                        else:
                            st.error(f"Could not read receipt: {ex_desc}")

        st.write("### 2. Verify Details")
        with st.container(border=True):
            with st.form("expense_form", clear_on_submit=True):
                c1, c2 = st.columns([1, 1])
                with c1: 
                    # READ FROM SESSION STATE
                    amount = st.number_input("Amount (₹)", value=st.session_state.form_amount, step=1.0)
                with c2: 
                    date = st.date_input("Date", value=st.session_state.form_date)
                
                # Safe Category Index
                cat_options = ["Food", "Transport", "Shopping", "Bills", "Health", "Entertainment", "Other"]
                curr_cat = st.session_state.form_category
                cat_idx = cat_options.index(curr_cat) if curr_cat in cat_options else 6
                
                category = st.selectbox("Category", cat_options, index=cat_idx)
                desc = st.text_input("Description", value=st.session_state.form_desc)
                
                st.write("")
                if st.form_submit_button("✅ Save Expense", type="primary", use_container_width=True):
                    if amount > 0:
                        db.save_expense(date, category, amount, desc)
                        st.toast(f"Saved ₹{amount}!", icon="🎉")
                        
                        # RESET SESSION STATE AFTER SAVE
                        st.session_state.form_amount = 0.0
                        st.session_state.form_desc = ""
                        st.session_state.form_category = "Other"
                        st.rerun()
                    else:
                        st.warning("Enter an amount greater than 0")

    # --- TAB 2: DASHBOARD ---
    with tab2:
        df = db.load_expenses()
        if not df.empty:
            total = df['Amount'].sum()
            avg = df['Amount'].mean()
            m1, m2 = st.columns(2)
            m1.metric("Total Spent", f"₹{total:,.0f}")
            m2.metric("Avg Transaction", f"₹{avg:,.0f}")
            st.divider()
            st.subheader("Where is money going?")
            st.bar_chart(df.groupby("Category")["Amount"].sum().sort_values(ascending=True), horizontal=True, color="#4CAF50")
            st.subheader("Daily Trend")
            st.line_chart(df.groupby("Date")["Amount"].sum(), color="#FF5722")
        else:
            st.info("No data yet.")

    # --- TAB 3: HISTORY ---
    with tab3:
        st.subheader("History")
        df = db.load_expenses()
        if not df.empty:
            display_df = df.copy()
            display_df['Date'] = display_df['Date'].dt.strftime('%d %b')
            st.dataframe(display_df[['Date', 'Category', 'Amount', 'Description']], use_container_width=True, hide_index=True)
            
            with st.expander("🛠 Manage Records"):
                options = df.apply(lambda x: f"{x['Date'].strftime('%Y-%m-%d')} - ₹{x['Amount']} ({x['Category']})", axis=1)
                selected = st.selectbox("Select transaction", options.index, format_func=lambda x: options[x])
                if st.button("Delete Selected"):
                    db.delete_expense(selected)
                    st.success("Deleted! Refreshing...")
                    st.rerun()

if __name__ == '__main__':
    main()