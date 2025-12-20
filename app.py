import streamlit as st
import pandas as pd
import google.generativeai as genai
from PIL import Image
from datetime import datetime
import json
import os
import time
import hashlib
from streamlit_paste_button import paste_image_button

# ==========================================
# 1. CONFIG & STYLING 
# ==========================================
st.set_page_config(page_title="Smart Expense Tracker", page_icon="💸", layout="wide")

# CSS: 
st.markdown("""
    <style>
    /* ---------------------------------------
       1. HIDE STREAMLIT DEFAULT UI
       --------------------------------------- */
    /* Completely hide the top header bar (Run, Settings, Github icon, etc.) */
    header[data-testid="stHeader"] {
        display: none;
    }
    
    /* Hide the hamburger menu (top right) and footer */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}

    /* ---------------------------------------
       2. LAYOUT ADJUSTMENTS
       --------------------------------------- */
    /* Reduce top padding since the header is gone */
    .block-container {
        padding-top: 1rem; 
        padding-bottom: 2rem;
    }
    
    /* ---------------------------------------
       3. COMPONENT STYLING
       --------------------------------------- */
    /* Metrics styling */
    div[data-testid="stMetricValue"] {font-size: 1.4rem; color: #333;}
    
    /* Professional Button Styling */
    button[kind="primary"] {border-radius: 8px; font-weight: 600; height: 3em;}
    button[kind="secondary"] {border-radius: 8px; height: 3em;}
    
    /* Warning Box for Budget */
    .warning-box {
        background-color: #ffebee; 
        padding: 15px; 
        border-radius: 8px; 
        border-left: 5px solid #d32f2f;
        color: #c62828;
        font-weight: bold;
        margin-bottom: 10px;
    }
    
    /* Paste Button Area Styling */
    .paste-container {
        border: 2px dashed #e0e0e0;
        background-color: #f9f9f9;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        margin-bottom: 15px;
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
    }
    .paste-text {
        font-size: 1rem;
        font-weight: 500;
        color: #555;
        margin-bottom: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. DATABASE HANDLER (Secure & Scalable)
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
                    # Handle both formats (JSON string vs Dict)
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

    # --- AUTHENTICATION ---
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def create_user(self, username, password):
        if not self.use_cloud: return False, "Cloud DB not connected"
        
        user_ref = self.db.collection(u'users').document(username)
        if user_ref.get().exists:
            return False, "Username already exists. Try another."
        
        user_ref.set({
            "username": username,
            "password": self.hash_password(password),
            "created_at": datetime.now().isoformat()
        })
        return True, "Account created! You can now log in."

    def verify_user(self, username, password):
        if not self.use_cloud: return False
        
        doc = self.db.collection(u'users').document(username).get()
        if doc.exists:
            user_data = doc.to_dict()
            if user_data['password'] == self.hash_password(password):
                return True
        return False

    # --- EXPENSES ---
    def save_expense(self, user_id, date, category, amount, description):
        if not self.use_cloud: return
        data = {
            "user_id": user_id,
            "Date": date.strftime('%Y-%m-%d'),
            "Category": category,
            "Amount": float(amount),
            "Description": description,
            "Timestamp": datetime.now().isoformat()
        }
        self.db.collection(u'expenses').add(data)

    def load_expenses(self, user_id):
        if not self.use_cloud: return pd.DataFrame()
        # Scalability: Order by date descending
        docs = self.db.collection(u'expenses')\
            .where(u'user_id', u'==', user_id)\
            .stream()
            
        data = [doc.to_dict() | {'id': doc.id} for doc in docs]
        
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
    # --- AUTHENTICATION FLOW ---
    if 'user_id' not in st.session_state:
        # Centered Layout for Login
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True) 
            st.title("💸 Smart Expense Tracker")
            st.markdown("### Secure Login")
            
            auth_tab1, auth_tab2 = st.tabs(["🔐 Log In", "📝 Sign Up"])
            
            # LOGIN TAB
            with auth_tab1:
                with st.form("login_form"):
                    username = st.text_input("Username").strip().lower()
                    password = st.text_input("Password", type="password")
                    if st.form_submit_button("Access Wallet", type="primary", use_container_width=True):
                        if db.verify_user(username, password):
                            st.session_state.user_id = username
                            st.rerun()
                        else:
                            st.error("Invalid Username or Password")
            
            # SIGN UP TAB
            with auth_tab2:
                with st.form("signup_form"):
                    new_user = st.text_input("Choose Username").strip().lower()
                    new_pass = st.text_input("Choose Password", type="password")
                    if st.form_submit_button("Create Account", type="secondary", use_container_width=True):
                        if new_user and new_pass:
                            success, msg = db.create_user(new_user, new_pass)
                            if success:
                                st.success(msg)
                            else:
                                st.error(msg)
                        else:
                            st.warning("Please fill all fields")
        return 

    # --- LOGGED IN DASHBOARD ---
    user_id = st.session_state.user_id
    
    # Header Section
    with st.container():
        c1, c2 = st.columns([6, 1])
        with c1: 
            st.title("💸 Smart Expense Tracker")
            st.caption(f"Welcome back, **{user_id}**! Let's manage your finances.")
        with c2: 
            # Logout Button aligned to top right
            if st.button("Log Out", type="secondary"):
                del st.session_state.user_id
                st.rerun()

    st.divider()

    # Init Session State for Form
    if 'form_amount' not in st.session_state: st.session_state.form_amount = 0.0
    if 'form_date' not in st.session_state: st.session_state.form_date = datetime.today()
    if 'form_category' not in st.session_state: st.session_state.form_category = "Other"
    if 'form_desc' not in st.session_state: st.session_state.form_desc = ""

    # MAIN NAVIGATION
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Add Expense", "📊 Dashboard", "🎯 Budget", "📜 History"])

    # --- TAB 1: ADD EXPENSE (Desktop Split View) ---
    with tab1:
        # Use columns to split layout on desktop
        col_input, col_form = st.columns([1, 1.5], gap="large")
        
        # LEFT: UPLOAD SECTION
        with col_input:
            st.subheader("1. Scan Receipt")
            st.info("Upload or Paste a receipt image to auto-fill.")
            
            up_tab1, up_tab2 = st.tabs(["📁 Upload", "📋 Paste"])
            
            image = None
            with up_tab1:
                uploaded_file = st.file_uploader("Choose file", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed")
                if uploaded_file: image = Image.open(uploaded_file)
            
            with up_tab2:
                # Better Paste UI
                st.markdown("""
                <div class="paste-container">
                    <div class="paste-text">📷 Taken a screenshot?</div>
                    <div style="font-size: 0.8rem; color: #888;">Click below to paste from clipboard</div>
                </div>
                """, unsafe_allow_html=True)
                paste_result = paste_image_button(label="📋 Paste Image", background_color="#FF4B4B")
                if paste_result.image_data is not None: image = paste_result.image_data

            if image:
                st.image(image, caption="Preview", width=250)
                if st.button("✨ Extract Details with AI", type="primary"):
                    with st.spinner("Analyzing receipt..."):
                        ex_date, ex_amount, ex_cat, ex_desc = analyze_receipt_with_ai(image)
                        if ex_amount and ex_amount > 0:
                            st.session_state.form_amount = float(ex_amount)
                            st.session_state.form_category = ex_cat
                            st.session_state.form_desc = ex_desc
                            try: st.session_state.form_date = datetime.strptime(ex_date, '%Y-%m-%d')
                            except: pass
                            
                            st.toast("Receipt scanned successfully!", icon="✅")
                            time.sleep(1.2) # Allow toast to be visible
                            st.rerun()

        # RIGHT: FORM SECTION
        with col_form:
            st.subheader("2. Add Expense Details (Manually)")
            with st.container(border=True):
                with st.form("add_exp"):
                    f_c1, f_c2 = st.columns(2)
                    amt = f_c1.number_input("Amount (₹)", value=st.session_state.form_amount, step=10.0)
                    dt = f_c2.date_input("Date", value=st.session_state.form_date)
                    
                    cat_options = ["Food", "Transport", "Shopping", "Bills", "Health", "Entertainment", "Other"]
                    curr_cat = st.session_state.form_category
                    cat_idx = cat_options.index(curr_cat) if curr_cat in cat_options else 6
                    
                    cat = st.selectbox("Category", cat_options, index=cat_idx)
                    desc = st.text_input("Description/Note", value=st.session_state.form_desc)
                    
                    st.write("")
                    if st.form_submit_button("✅ Save Expense", type="primary", use_container_width=True):
                        if amt > 0:
                            db.save_expense(user_id, dt, cat, amt, desc)
                            
                            # RESET & FEEDBACK
                            st.session_state.form_amount = 0.0
                            st.session_state.form_desc = ""
                            
                            st.toast(f"Added expense ₹{amt} successfully!", icon="🎉")
                            time.sleep(1.5) # Wait for toast
                            st.rerun()
                        else:
                            st.warning("Amount cannot be zero.")

    # --- TAB 2: DASHBOARD ---
    with tab2:
        df = db.load_expenses(user_id)
        if not df.empty:
            curr_month_str = datetime.now().strftime("%Y-%m")
            budget_limit = db.get_budget(user_id, curr_month_str)
            
            df['Month'] = df['Date'].dt.strftime('%Y-%m')
            curr_expenses = df[df['Month'] == curr_month_str]['Amount'].sum()
            total_lifetime = df['Amount'].sum()
            
            # Metrics
            m1, m2, m3 = st.columns(3)
            m1.metric("This Month Spent", f"₹{curr_expenses:,.0f}")
            if budget_limit > 0:
                delta = budget_limit - curr_expenses
                m2.metric("Monthly Budget", f"₹{budget_limit:,.0f}", delta=f"{delta:,.0f} Remaining", delta_color="normal")
            else:
                m2.metric("Monthly Budget", "Not Set", delta="Set in Budget tab", delta_color="off")
            m3.metric("Lifetime Spent", f"₹{total_lifetime:,.0f}")
            
            # Alert Logic
            if budget_limit > 0:
                percent = (curr_expenses / budget_limit) * 100
                st.progress(min(percent/100, 1.0))
                if percent >= 90:
                    st.markdown(f'''
                    <div class="warning-box">
                    ⚠️ ALERT: You have used {percent:.1f}% of your monthly budget!
                    </div>
                    ''', unsafe_allow_html=True)
            
            st.divider()
            
            # Charts
            c_chart1, c_chart2 = st.columns(2)
            with c_chart1:
                st.subheader("Category Split")
                st.bar_chart(df.groupby("Category")["Amount"].sum(), color="#4CAF50")
            
            with c_chart2:
                st.subheader("Daily Trend")
                st.line_chart(df.groupby("Date")["Amount"].sum(), color="#FF5722")

        else:
            st.info("No data available yet. Add your first expense!")

    # --- TAB 3: BUDGET ---
    with tab3:
        col_b_main, col_b_dummy = st.columns([1, 1])
        with col_b_main:
            st.subheader("🎯 Set Monthly Limits")
            curr_month = datetime.now().strftime("%Y-%m")
            st.caption(f"Managing budget for: **{curr_month}**")
            
            current_limit = db.get_budget(user_id, curr_month)
            new_limit = st.number_input("Monthly Limit (₹)", value=float(current_limit), step=500.0)
            
            if st.button("Update Budget Limit", type="primary"):
                db.set_budget(user_id, curr_month, new_limit)
                st.toast(f"Budget updated to ₹{new_limit:,.0f}", icon="🎯")
                time.sleep(1)
                st.rerun()

    # --- TAB 4: HISTORY ---
    with tab4:
        st.subheader("📜 Transaction History")
        df = db.load_expenses(user_id)
        if not df.empty:
            df['MonthStr'] = df['Date'].dt.strftime('%Y-%m')
            months = sorted(df['MonthStr'].unique().tolist(), reverse=True)
            
            col_filter, col_rest = st.columns([1, 3])
            with col_filter:
                sel_month = st.selectbox("Filter by Month", months)
            
            filtered = df[df['MonthStr'] == sel_month]
            
            # Table View
            for idx, row in filtered.iterrows():
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([2, 4, 2, 1])
                    c1.write(f"**{row['Date'].strftime('%d %b')}**")
                    c2.write(f"{row['Category']} - {row['Description']}")
                    c3.write(f"**₹{row['Amount']}**")
                    if c4.button("🗑️", key=f"del_{row['id']}"):
                        db.delete_expense(row['id'])
                        st.toast("Expense deleted!", icon="🗑️")
                        time.sleep(1)
                        st.rerun()
        else:
            st.info("No records found.")

if __name__ == '__main__':
    main()