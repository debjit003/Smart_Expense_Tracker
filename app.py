import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
from datetime import datetime
import json
import os
import time
from streamlit_paste_button import paste_image_button

# ==========================================
# 1. CONFIG & STYLING
# ==========================================
st.set_page_config(page_title="Smart Wallet", page_icon="💳", layout="centered")

# CSS to make it look like a mobile app
st.markdown("""
    <style>
    .stApp {margin-top: -30px;}
    div[data-testid="stMetricValue"] {font-size: 1.6rem;}
    button[kind="primary"] {width: 100%; border-radius: 10px;}
    button[kind="secondary"] {width: 100%; border-radius: 10px;}
    .warning-box {
        background-color: #ffcccc; 
        padding: 15px; 
        border-radius: 10px; 
        border-left: 5px solid #ff0000;
        color: #990000;
        font-weight: bold;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. DATABASE HANDLER (SCALABLE)
# ==========================================
class DataHandler:
    def __init__(self):
        self.use_cloud = False
        self.db = None
        
        # Initialize Firestore
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
                st.error(f"Database Connection Failed: {e}")

    # --- EXPENSES ---
    def save_expense(self, user_id, date, category, amount, description):
        if not self.use_cloud: return
        data = {
            "user_id": user_id, # Link data to specific user
            "Date": date.strftime('%Y-%m-%d'),
            "Category": category,
            "Amount": float(amount),
            "Description": description,
            "Timestamp": datetime.now().isoformat()
        }
        self.db.collection(u'expenses').add(data)

    def load_expenses(self, user_id):
        if not self.use_cloud: return pd.DataFrame()
        # SCALABLE QUERY: Only fetch data for this user
        docs = self.db.collection(u'expenses').where(u'user_id', u'==', user_id).stream()
        data = [doc.to_dict() | {'id': doc.id} for doc in docs] # Include ID for deletion
        
        if not data:
            return pd.DataFrame(columns=["Date", "Category", "Amount", "Description", "id"])
        
        df = pd.DataFrame(data)
        df['Date'] = pd.to_datetime(df['Date'])
        return df.sort_values(by="Date", ascending=False)

    def delete_expense(self, doc_id):
        if self.use_cloud:
            self.db.collection(u'expenses').document(doc_id).delete()

    # --- BUDGETS ---
    def set_budget(self, user_id, month_str, limit):
        if not self.use_cloud: return
        # Create a unique ID for the budget: "user_2025-10"
        doc_id = f"{user_id}_{month_str}"
        self.db.collection(u'budgets').document(doc_id).set({
            "user_id": user_id,
            "month": month_str,
            "limit": float(limit)
        })

    def get_budget(self, user_id, month_str):
        if not self.use_cloud: return 0.0
        doc_id = f"{user_id}_{month_str}"
        doc = self.db.collection(u'budgets').document(doc_id).get()
        if doc.exists:
            return doc.to_dict().get('limit', 0.0)
        return 0.0

db = DataHandler()

# ==========================================
# 3. AI ENGINE
# ==========================================
def analyze_receipt_with_ai(image):
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key: return None, 0.0, "Other", "API Key Missing!"

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-2.5-flash')
    prompt = """
    Analyze receipt. Return ONLY JSON:
    {"date": "YYYY-MM-DD", "total_amount": 0.0, "category": "Food/Transport/Shopping/Bills/Health/Entertainment/Other", "merchant": "Name"}
    """
    try:
        response = model.generate_content([prompt, image])
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        return data.get("date"), data.get("total_amount"), data.get("category"), data.get("merchant")
    except Exception as e:
        return None, 0.0, "Other", f"AI Error: {str(e)}"

# ==========================================
# 4. MAIN APP LOGIC
# ==========================================
def main():
    # --- AUTHENTICATION (Simple Scalable Login) ---
    if 'user_id' not in st.session_state:
        st.title("🔐 Login to Smart Wallet")
        st.caption("Enter a unique username to access your private data.")
        
        with st.form("login_form"):
            username = st.text_input("Username").strip().lower()
            if st.form_submit_button("Access My Wallet", type="primary"):
                if username:
                    st.session_state.user_id = username
                    st.rerun()
                else:
                    st.warning("Please enter a username")
        return # Stop execution if not logged in

    # --- LOGGED IN USER ---
    user_id = st.session_state.user_id
    
    # Header with Logout
    c1, c2 = st.columns([3, 1])
    with c1: st.title(f"👋 Hi, {user_id}")
    with c2: 
        if st.button("Log Out"):
            del st.session_state.user_id
            st.rerun()

    # Initialize Session State Variables
    if 'form_amount' not in st.session_state: st.session_state.form_amount = 0.0
    if 'form_date' not in st.session_state: st.session_state.form_date = datetime.today()
    if 'form_category' not in st.session_state: st.session_state.form_category = "Other"
    if 'form_desc' not in st.session_state: st.session_state.form_desc = ""

    # TABS
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Add", "📊 Dash", "🎯 Budget", "📜 List"])

    # --- TAB 1: ADD EXPENSE ---
    with tab1:
        st.write("### New Expense")
        col_up, col_paste = st.columns(2)
        with col_up: uploaded_file = st.file_uploader("Upload", type=['png', 'jpg'], label_visibility="collapsed")
        with col_paste: paste_result = paste_image_button(label="📋 Paste", background_color="#FF4B4B")

        image = None
        if uploaded_file: image = Image.open(uploaded_file)
        elif paste_result.image_data is not None: image = paste_result.image_data

        if image:
            st.image(image, width=150)
            if st.button("✨ Auto-Fill", type="primary"):
                with st.spinner("Scanning..."):
                    ex_date, ex_amount, ex_cat, ex_desc = analyze_receipt_with_ai(image)
                    if ex_amount and ex_amount > 0:
                        st.session_state.form_amount = float(ex_amount)
                        st.session_state.form_category = ex_cat
                        st.session_state.form_desc = ex_desc
                        try: st.session_state.form_date = datetime.strptime(ex_date, '%Y-%m-%d')
                        except: pass
                        st.rerun()

        with st.form("add_exp"):
            c1, c2 = st.columns(2)
            amt = c1.number_input("₹ Amount", value=st.session_state.form_amount)
            dt = c2.date_input("Date", value=st.session_state.form_date)
            cat = st.selectbox("Category", ["Food", "Transport", "Shopping", "Bills", "Health", "Entertainment", "Other"], index=6)
            desc = st.text_input("Note", value=st.session_state.form_desc)
            
            if st.form_submit_button("Save", type="primary"):
                if amt > 0:
                    db.save_expense(user_id, dt, cat, amt, desc)
                    st.success("Saved!")
                    st.session_state.form_amount = 0.0
                    st.session_state.form_desc = ""
                    time.sleep(1)
                    st.rerun()

    # --- TAB 2: DASHBOARD & ALERTS ---
    with tab2:
        df = db.load_expenses(user_id)
        if not df.empty:
            # 1. Budget Logic
            current_month_str = datetime.now().strftime("%Y-%m")
            budget_limit = db.get_budget(user_id, current_month_str)
            
            # Filter df for current month
            df['Month'] = df['Date'].dt.strftime('%Y-%m')
            monthly_expenses = df[df['Month'] == current_month_str]['Amount'].sum()
            
            # 2. ALERT SYSTEM (90% Logic)
            if budget_limit > 0:
                percent_used = (monthly_expenses / budget_limit) * 100
                st.write(f"**Monthly Budget ({current_month_str})**")
                st.progress(min(percent_used / 100, 1.0))
                
                col_b1, col_b2 = st.columns(2)
                col_b1.metric("Spent", f"₹{monthly_expenses:,.0f}")
                col_b2.metric("Limit", f"₹{budget_limit:,.0f}", delta=f"{budget_limit - monthly_expenses:,.0f} left")

                if percent_used >= 90:
                    st.markdown(f"""
                    <div class="warning-box">
                    ⚠️ ALERT: You have used {percent_used:.1f}% of your monthly budget!
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("💡 Set a budget in the 'Budget' tab to see alerts.")
                st.metric("Total Spent", f"₹{monthly_expenses:,.0f}")

            st.divider()
            st.bar_chart(df.groupby("Category")["Amount"].sum(), horizontal=True, color="#4CAF50")

    # --- TAB 3: SET BUDGET ---
    with tab3:
        st.subheader("🎯 Monthly Goals")
        curr_month = datetime.now().strftime("%Y-%m")
        st.caption(f"Setting budget for: {curr_month}")
        
        current_limit = db.get_budget(user_id, curr_month)
        new_limit = st.number_input("Monthly Limit (₹)", value=float(current_limit), step=500.0)
        
        if st.button("Update Budget", type="primary"):
            db.set_budget(user_id, curr_month, new_limit)
            st.success(f"Budget set to ₹{new_limit:,.0f}")
            time.sleep(1)
            st.rerun()

    # --- TAB 4: LIST VIEW (Month Wise) ---
    with tab4:
        st.subheader("📜 Expense List")
        df = db.load_expenses(user_id)
        if not df.empty:
            # Month Filter
            df['MonthStr'] = df['Date'].dt.strftime('%Y-%m')
            all_months = sorted(df['MonthStr'].unique().tolist(), reverse=True)
            selected_month = st.selectbox("Select Month", all_months)
            
            filtered_df = df[df['MonthStr'] == selected_month]
            
            # Display
            for index, row in filtered_df.iterrows():
                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    c1.markdown(f"**{row['Category']}**")
                    c1.caption(f"{row['Date'].strftime('%d %b')} - {row['Description']}")
                    c2.markdown(f"**₹{row['Amount']}**")
                    if c3.button("🗑️", key=f"del_{row['id']}"):
                        db.delete_expense(row['id'])
                        st.rerun()
        else:
            st.info("No records found.")

if __name__ == '__main__':
    main()