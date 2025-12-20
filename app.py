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
# This hides the default Streamlit hamburger menu and footer for a cleaner "App" look
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
                    # Load credentials from Streamlit secrets
                    key_dict = json.loads(st.secrets["firebase"]["text_key"])
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
            # Save to Firestore
            self.db.collection(u'expenses').add(data)
        else:
            # Save to CSV (Fallback)
            df = pd.DataFrame([data])
            df.to_csv(self.csv_file, mode='a', header=not os.path.exists(self.csv_file), index=False)

    def load_expenses(self):
        if self.use_cloud:
            # Load from Firestore
            docs = self.db.collection(u'expenses').stream()
            data = [doc.to_dict() for doc in docs]
            if not data:
                return pd.DataFrame(columns=["Date", "Category", "Amount", "Description"])
            df = pd.DataFrame(data)
            df['Date'] = pd.to_datetime(df['Date'])
            return df.sort_values(by="Date", ascending=False)
        else:
            # Load from CSV
            if os.path.exists(self.csv_file):
                df = pd.read_csv(self.csv_file)
                df['Date'] = pd.to_datetime(df['Date'])
                return df.sort_values(by="Date", ascending=False)
            return pd.DataFrame(columns=["Date", "Category", "Amount", "Description"])

    def delete_expense(self, row_identifier):
        # Note: Deleting from CSV by index is tricky in multi-user, 
        # Firestore uses Document IDs. This is a simplified local version.
        if not self.use_cloud:
            df = self.load_expenses()
            # We assume row_identifier is the index for CSV
            df = df.drop(row_identifier)
            df.to_csv(self.csv_file, index=False)

db = DataHandler()

# ==========================================
# 3. AI ENGINE (Google Gemini)
# ==========================================
def analyze_receipt_with_ai(image):
    # Check for API Key
    api_key = st.secrets.get("GEMINI_API_KEY")
    if not api_key:
        return None, 0.0, "Other", "API Key Missing! Set GEMINI_API_KEY in secrets."

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
        # Clean the response to ensure it's pure JSON
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
    
    # TABS for Mobile Navigation
    tab1, tab2, tab3 = st.tabs(["➕ Add Expense", "📊 Insights", "📜 History"])

    # --- TAB 1: ADD EXPENSE ---
    with tab1:
        st.caption("Snap a receipt or enter manually")
        
        # 1. Image Input
        uploaded_file = st.file_uploader("Upload Receipt", type=['png', 'jpg', 'jpeg'], label_visibility="collapsed")
        
        # Defaults
        default_date = datetime.today()
        default_amount = 0.0
        default_cat = "Other"
        default_desc = ""

        # 2. AI Processing
        if uploaded_file:
            image = Image.open(uploaded_file)
            st.image(image, caption="Processing...", width=150)
            
            if st.button("✨ Auto-Fill with AI", type="primary", use_container_width=True):
                with st.spinner("AI is reading your receipt..."):
                    ex_date, ex_amount, ex_cat, ex_desc = analyze_receipt_with_ai(image)
                    if ex_amount > 0:
                        st.toast("Receipt Scanned Successfully!", icon="✅")
                        try:
                            default_date = datetime.strptime(ex_date, '%Y-%m-%d')
                        except:
                            pass
                        default_amount = float(ex_amount)
                        default_cat = ex_cat
                        default_desc = ex_desc
                    else:
                        st.error(f"Failed: {ex_desc}")

        # 3. Final Form
        with st.form("expense_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                date = st.date_input("Date", default_date)
            with col2:
                amount = st.number_input("Amount (₹)", value=default_amount, step=1.0)
            
            category = st.selectbox("Category", 
                ["Food", "Transport", "Shopping", "Bills", "Health", "Entertainment", "Other"], 
                index=["Food", "Transport", "Shopping", "Bills", "Health", "Entertainment", "Other"].index(default_cat) if default_cat in ["Food", "Transport", "Shopping", "Bills", "Health", "Entertainment", "Other"] else 6
            )
            desc = st.text_input("Note", value=default_desc, placeholder="e.g. Dinner at McD")
            
            if st.form_submit_button("✅ Save Expense", use_container_width=True):
                if amount > 0:
                    db.save_expense(date, category, amount, desc)
                    st.toast(f"Saved ₹{amount} for {category}!", icon="🎉")
                else:
                    st.warning("Amount must be greater than 0")

    # --- TAB 2: DASHBOARD ---
    with tab2:
        df = db.load_expenses()
        if not df.empty:
            # KPI Cards
            total = df['Amount'].sum()
            avg = df['Amount'].mean()
            
            c1, c2 = st.columns(2)
            c1.metric("Total Spent", f"₹{total:,.0f}")
            c2.metric("Avg Txn", f"₹{avg:,.0f}")
            
            st.divider()
            
            # Charts
            st.subheader("Spending by Category")
            # Simple bar chart is best for mobile
            cat_data = df.groupby("Category")["Amount"].sum().sort_values(ascending=True)
            st.bar_chart(cat_data, horizontal=True, color="#4CAF50")
            
            st.subheader("Daily Trend")
            daily_data = df.groupby("Date")["Amount"].sum()
            st.line_chart(daily_data, color="#FF5722")
        else:
            st.info("No data yet. Go to 'Add Expense' to start!")

    # --- TAB 3: HISTORY ---
    with tab3:
        st.subheader("Recent Transactions")
        df = db.load_expenses()
        if not df.empty:
            # Display simple table
            # Format Date for display
            display_df = df.copy()
            display_df['Date'] = display_df['Date'].dt.strftime('%d %b')
            
            st.dataframe(
                display_df[['Date', 'Category', 'Amount', 'Description']], 
                use_container_width=True,
                hide_index=True
            )
            
            # Delete Utility (Hidden in Expander to stay clean)
            with st.expander("⚙️ Manage Records"):
                options = df.apply(lambda x: f"{x['Date'].strftime('%Y-%m-%d')} - ₹{x['Amount']} ({x['Category']})", axis=1)
                selected = st.selectbox("Select transaction to delete", options.index, format_func=lambda x: options[x])
                
                if st.button("🗑️ Delete Selected Record", type="secondary", use_container_width=True):
                    db.delete_expense(selected)
                    st.success("Deleted! Refreshing...")
                    st.rerun()

if __name__ == '__main__':
    main()


# import streamlit as st
# import pytesseract
# from PIL import Image
# import pandas as pd
# import re
# import os
# from datetime import datetime
# from streamlit_paste_button import paste_image_button
# import cv2
# import numpy as np
# import io

# # ==========================================
# # 1. CONFIGURATION
# # ==========================================
# CSV_FILE = 'expenses.csv'

# if os.name == 'nt':
#     pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# # ==========================================
# # 2. IMAGE PREPROCESSING
# # ==========================================
# def preprocess_image(pil_image):
#     img_array = np.array(pil_image)
#     if img_array.shape[-1] == 4:
#         img_array = cv2.cvtColor(img_array, cv2.COLOR_RGBA2RGB)
    
#     if len(img_array.shape) == 3:
#         gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
#     else:
#         gray = img_array

#     # 1. Upscale (3x)
#     scaled = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    
#     # 2. Blur (Fixes symbol noise)
#     blurred = cv2.GaussianBlur(scaled, (5, 5), 0)

#     # 3. Threshold
#     _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
#     return thresh

# # ==========================================
# # 3. ROBUST CLEANING
# # ==========================================
# def parse_flexible_float(price_str):
#     clean_str = price_str.lower()
#     clean_str = re.sub(r'(rs\.|rs|inr|₹|r8|fls\.|total|grand|amount|net|paid|target)', '', clean_str)
#     clean_str = re.sub(r'[^\d.,]', '', clean_str).strip()
    
#     if not clean_str or len(clean_str) > 15: return 0.0

#     if ',' in clean_str:
#         if re.search(r',\d{3}(?:$|[^\d])', clean_str):
#             clean_str = clean_str.replace(',', '') 
#         else:
#             clean_str = clean_str.replace(',', '.')

#     try:
#         val = float(clean_str)
#         if val > 5000000: return 0.0
#         return val
#     except:
#         return 0.0

# # ==========================================
# # 4. SMART EXTRACTION
# # ==========================================
# def smart_categorize(text):
#     text = text.lower()
#     if any(x in text for x in ["flipkart", "amazon", "myntra", "retail", "shipping"]):
#         return "Shopping"

#     keywords = {
#         "Food": ["restaurant", "cafe", "coffee", "burger", "pizza", "dining", "meal", "zomato", "swiggy"],
#         "Transport": ["uber", "ola", "fuel", "petrol", "parking", "cab", "flight"],
#         "Bills": ["electricity", "water", "gas", "airtel", "jio", "wifi", "bill"],
#         "Health": ["pharmacy", "doctor", "hospital", "med", "health", "lab"],
#         "Entertainment": ["movie", "cinema", "netflix", "prime", "show"],
#         "Shopping": ["mart", "mall", "clothing", "store", "shop", "book", "fashion"]
#     }
#     for cat, words in keywords.items():
#         for word in words:
#             if word in text: return cat
#     return "Other"

# def extract_info(image):
#     processed_img = preprocess_image(image)
#     try:
#         custom_config = r'--oem 3 --psm 6'
#         raw_text = pytesseract.image_to_string(processed_img, config=custom_config)
#     except Exception as e:
#         return None, 0.0, "Other", f"Error: {e}"

#     # Date
#     extracted_date_str = datetime.today().strftime('%Y-%m-%d')
#     date_patterns = [
#         r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,.-]*\d{1,2}[\s,.-]*\d{4}',
#         r'\d{1,2}\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,.-]*\d{4}',
#         r'\d{4}[/-]\d{2}[/-]\d{2}',
#         r'\d{2}[/-]\d{2}[/-]\d{2,4}'
#     ]
#     for pattern in date_patterns:
#         dates_found = re.findall(pattern, raw_text, re.IGNORECASE)
#         if dates_found:
#             extracted_date_str = dates_found[0]
#             if "20" in extracted_date_str: break

#     # Amount (Grand Total Logic)
#     lines = raw_text.split('\n')
#     potential_totals = []
    
#     # Priority 1: "Grand Total"
#     for line in lines:
#         if "grand total" in line.lower():
#             clean = re.sub(r'[^\d., ]', '', line.lower().replace("grand total", ""))
#             for part in clean.split():
#                 val = parse_flexible_float(part)
#                 if val > 0: potential_totals.append(val)
    
#     amount = 0.0
#     if potential_totals:
#         amount = max(potential_totals)
#     else:
#         # Priority 2: Any "Total" line
#         fallback_totals = []
#         for line in lines:
#             if any(k in line.lower() for k in ["total", "payable", "amount"]):
#                 clean = re.sub(r'[^\d., ]', '', line.lower())
#                 for part in clean.split():
#                     val = parse_flexible_float(part)
#                     if val > 0: fallback_totals.append(val)
        
#         if fallback_totals:
#             amount = max(fallback_totals)
#         else:
#             # Priority 3: Scan all
#             all_nums = re.findall(r'[\d.,]+', raw_text)
#             valid = []
#             for p in all_nums:
#                 v = parse_flexible_float(p)
#                 if v > 10 and v < 5000000 and v not in [2012, 2013, 2023, 2024, 2025]:
#                     valid.append(v)
#             if valid: amount = max(valid)

#     category = smart_categorize(raw_text)
#     return extracted_date_str, amount, category, raw_text

# def to_excel(df):
#     output = io.BytesIO()
#     with pd.ExcelWriter(output, engine='openpyxl') as writer:
#         df.to_excel(writer, index=False, sheet_name='Expenses')
#     return output.getvalue()

# # ==========================================
# # 5. FRONTEND UI
# # ==========================================
# def main():
#     st.set_page_config(page_title="Expense AI", page_icon="🧾", layout="wide")
#     st.markdown("<h1 style='text-align: center;'>🧾 Smart Expense Tracker</h1>", unsafe_allow_html=True)

#     # --- INPUT SECTION (2 Columns) ---
#     col_input, col_form = st.columns([1, 1])
    
#     # Initialize Defaults
#     default_date = datetime.today()
#     default_amount = 0.0
#     default_category = "Other"
#     default_desc = ""
#     categories_list = ["Food", "Transport", "Shopping", "Bills", "Health", "Entertainment", "Other"]
    
#     image = None

#     # --- LEFT COLUMN: IMAGE HANDLING ---
#     with col_input:
#         st.subheader("1. Receipt (Optional)")
#         uploaded_file = st.file_uploader("Upload Image", type=['png', 'jpg', 'jpeg'])
#         paste_result = paste_image_button(label="📋 Paste Image (Ctrl+V)", background_color="#FF4B4B", hover_background_color="#FF0000")
        
#         if uploaded_file:
#             image = Image.open(uploaded_file)
#         elif paste_result.image_data:
#             image = paste_result.image_data

#         if image:
#             st.image(image, caption='Receipt Preview', use_column_width=True)
#             with st.spinner('AI Analyzing...'):
#                 extracted_date_str, extracted_amount, extracted_cat, _ = extract_info(image)
                
#                 # UPDATE DEFAULTS WITH AI DATA
#                 if extracted_amount > 0:
#                     st.success("AI Data Extracted!")
#                     default_amount = extracted_amount
#                     default_category = extracted_cat
                    
#                     # Date Parsing
#                     clean_date = re.sub(r'[.,]', ' ', extracted_date_str).strip()
#                     for fmt in ['%b %d %Y', '%B %d %Y', '%Y-%m-%d', '%d-%m-%Y', '%d %b %Y']:
#                         try:
#                             default_date = datetime.strptime(clean_date, fmt)
#                             break
#                         except: pass
#         else:
#             st.info("No image? No problem. Enter details manually ➡️")

#     # --- RIGHT COLUMN: THE FORM (ALWAYS VISIBLE) ---
#     with col_form:
#         st.subheader("2. Expense Details")
        
#         with st.form(key='expense_form'):
#             date = st.date_input("Date", default_date)
            
#             # Category Select
#             try: cat_index = categories_list.index(default_category)
#             except: cat_index = 6
#             category = st.selectbox("Category", categories_list, index=cat_index)
            
#             amount = st.number_input("Amount (₹)", value=default_amount, step=0.1)
#             desc = st.text_input("Description (Optional)", value=default_desc)
            
#             submit_button = st.form_submit_button(label='💾 Save Expense', use_container_width=True)

#         if submit_button:
#             if amount > 0:
#                 new_data = pd.DataFrame({"Date": [date], "Category": [category], "Amount": [amount], "Description": [desc]})
#                 new_data.to_csv(CSV_FILE, mode='a', header=not os.path.exists(CSV_FILE), index=False)
#                 st.success(f"Saved: ₹{amount}")
#                 st.rerun()
#             else:
#                 st.error("Amount must be greater than 0.")

#     st.divider()

#     # --- DATA DASHBOARD ---
#     if os.path.exists(CSV_FILE):
#         df = pd.read_csv(CSV_FILE)
#         if not df.empty:
#             df['Date'] = pd.to_datetime(df['Date'])
#             df = df.sort_values(by="Date", ascending=False)
            
#             # Metrics
#             m1, m2, m3 = st.columns(3)
#             m1.metric("Total Spending", f"₹ {df['Amount'].sum():,.2f}")
#             m2.metric("Transactions", len(df))
#             m3.metric("Average", f"₹ {df['Amount'].mean():,.2f}")
            
#             st.divider()

#             # Graphs & Manage
#             c1, c2 = st.columns([2, 1])
#             with c1:
#                 st.subheader("Spending Overview")
#                 st.bar_chart(df.groupby("Category")["Amount"].sum())
            
#             with c2:
#                 st.subheader("Manage Data")
                
#                 # Excel Download
#                 excel_data = to_excel(df)
#                 st.download_button("📥 Download Excel", data=excel_data, file_name='expenses.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', use_container_width=True)
                
#                 # Delete Section
#                 with st.expander("🗑️ Delete Expenses"):
#                     df['display_str'] = df.index.astype(str) + " | " + df['Date'].dt.strftime('%Y-%m-%d') + " | ₹" + df['Amount'].astype(str)
#                     rows_to_delete = st.multiselect("Select rows:", df['display_str'])
#                     if st.button("Delete Selected"):
#                         indices = [int(r.split(' | ')[0]) for r in rows_to_delete]
#                         df = df.drop(indices).drop(columns=['display_str'])
#                         df.to_csv(CSV_FILE, index=False)
#                         st.success("Deleted!")
#                         st.rerun()
            
#             # Recent Table
#             st.subheader("Recent Transactions")
#             st.dataframe(df[['Date', 'Category', 'Amount', 'Description']], use_container_width=True)

# if __name__ == '__main__':
#     main()