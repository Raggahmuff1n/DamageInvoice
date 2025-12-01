import streamlit as st
import pandas as pd
from datetime import datetime
import os
from pathlib import Path
import urllib.parse
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import tempfile
import json

# --- Google Drive Setup ---
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def authenticate_google_drive():
    """Authenticate and return Google Drive service instance"""
    creds = None
    
    # Token file stores the user's access and refresh tokens
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    
    # If there are no (valid) credentials available, let the user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # You'll need to create credentials.json from Google Cloud Console
            if os.path.exists('credentials. json'):
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            else:
                st.error("credentials.json not found. Please set up Google Drive API credentials.")
                return None
        
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    
    return build('drive', 'v3', credentials=creds)

def extract_folder_id_from_url(url):
    """Extract folder ID from Google Drive URL"""
    if "drive.google.com" in url:
        # Handle different Google Drive URL formats
        if "/folders/" in url:
            folder_id = url.split("/folders/")[1].split("?")[0]
            return folder_id
        elif "id=" in url:
            folder_id = url.split("id=")[1].split("&")[0]
            return folder_id
    return url  # Return as-is if not a recognized Google Drive URL

def upload_to_google_drive(service, file_content, filename, folder_id, mime_type='application/octet-stream'):
    """Upload a file to Google Drive and return the shareable link"""
    try:
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(filename).suffix) as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name
        
        file_metadata = {
            'name': filename,
            'parents': [folder_id] if folder_id else []
        }
        
        media = MediaFileUpload(tmp_file_path, mimetype=mime_type, resumable=True)
        
        # Upload file
        file = service. files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink'
        ).execute()
        
        # Clean up temp file
        os.unlink(tmp_file_path)
        
        # Get the shareable link
        file_id = file.get('id')
        
        # Make the file publicly viewable (optional - comment out if not needed)
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'}
        ).execute()
        
        # Return the direct link
        return f"https://drive.google.com/file/d/{file_id}/view"
    
    except Exception as e:
        st.error(f"Error uploading to Google Drive: {e}")
        return None

# --- Config ---
CATEGORY_LIST = [
    "Property Damage",
    "Economic/Financial Loss", 
    "Medical & Health-Related",
    "Emotional & Psychological Damages",
    "Loss of Companionship or Consortium",
    "Punitive Damages",
    "Special Circumstances",
    "Legal & Administrative Costs",
    "Future Damages",
    "Miscellaneous",
    "Other"
]

# Subcategories for each main category
SUBCATEGORIES = {
    "Property Damage": [
        "Vehicle repair/replacement",
        "Rental vehicle costs",
        "Damage to home or real estate",
        "Damage to personal belongings",
        "Other"
    ],
    "Economic/Financial Loss": [
        "Lost wages or income",
        "Loss of earning capacity",
        "Business interruption",
        "Out-of-pocket expenses",
        "Replacement costs",
        "Other"
    ],
    "Medical & Health-Related": [
        "Medical bills",
        "Medication costs",
        "Rehabilitation or physical therapy",
        "Mental health therapy",
        "Other"
    ],
    "Emotional & Psychological Damages": [
        "Pain and suffering",
        "Emotional distress",
        "Loss of enjoyment of life",
        "Grief and bereavement",
        "Other"
    ],
    "Special Circumstances": [
        "Pet loss and related costs",
        "Temporary housing costs",
        "Childcare expenses",
        "Travel expenses",
        "Other"
    ],
    "Legal & Administrative Costs": [
        "Attorney fees",
        "Court filing fees",
        "Expert witness fees",
        "Other"
    ],
    "Future Damages": [
        "Projected medical care",
        "Future therapy",
        "Long-term disability costs",
        "Other"
    ]
}

DEFAULT_UPLOADS = "uploads"
os.makedirs(DEFAULT_UPLOADS, exist_ok=True)

# --- Session defaults for data storage ---
if "damages" not in st.session_state:
    st.session_state["damages"] = []

if "gdrive_service" not in st.session_state:
    st.session_state["gdrive_service"] = None

if "gdrive_folder_id" not in st.session_state:
    st.session_state["gdrive_folder_id"] = None

# --- Properly initialize form keys with correct types BEFORE creating widgets ---
if "title_input" not in st.session_state:
    st.session_state["title_input"] = ""
if "description_input" not in st.session_state:
    st.session_state["description_input"] = ""
if "date_input" not in st.session_state:
    st.session_state["date_input"] = datetime.today()
if "category_input" not in st.session_state:
    st.session_state["category_input"] = CATEGORY_LIST[0]
if "subcategory_input" not in st.session_state:
    st.session_state["subcategory_input"] = ""
if "custom_category_input" not in st.session_state:
    st.session_state["custom_category_input"] = ""
if "cost_input" not in st. session_state:
    st. session_state["cost_input"] = 0.0
if "image_input" not in st. session_state:
    st. session_state["image_input"] = None

# Save location config stored per session
if "save_config" not in st.session_state:
    st.session_state["save_config"] = None
if "save_config_set" not in st.session_state:
    st.session_state["save_config_set"] = False

st.set_page_config(page_title="Damage Invoice Tracker", layout="wide")
st.title("⚖️ Damage Invoice Tracker for Legal Proceedings")

# --- Google Drive Configuration (asked once per session) ---
with st.expander("🔧 Configure Google Drive for Receipt Storage", expanded=not st.session_state["save_config_set"]):
    st.write("Set up where your receipts and invoices will be stored.")
    
    storage_type = st.radio(
        "Storage Type",
        ["Google Drive (Recommended)", "Local Storage"]
    )
    
    if storage_type == "Google Drive (Recommended)":
        st.info("📁 Files will be uploaded to your Google Drive folder and links will be included in the spreadsheet.")
        
        # Check for credentials file
        if not os.path.exists('credentials.json'):
            st.warning("⚠️ Google Drive API credentials not found. Please follow these steps:")
            st.markdown("""
            1. Go to [Google Cloud Console](https://console. cloud.google.com/)
            2. Create a new project or select existing
            3. Enable Google Drive API
            4. Create OAuth 2. 0 credentials
            5. Download the credentials as `credentials.json`
            6. Place it in the same directory as this script
            """)
            
            # Alternative: Allow manual folder ID input
            st.subheader("Alternative: Manual Configuration")
            manual_folder_url = st.text_input(
                "Paste your Google Drive folder URL:",
                value="https://drive.google.com/drive/folders/1HIu5XR7pFg8s49AG8Yiu_7aCK9HMeT8N",
                help="Example: https://drive.google.com/drive/folders/..."
            )
            
            use_manual = st.checkbox("Use manual configuration (files will be saved locally with Google Drive links)")
            
            if st.button("Set Google Drive Folder"):
                if use_manual and manual_folder_url:
                    folder_id = extract_folder_id_from_url(manual_folder_url)
                    st.session_state["gdrive_folder_id"] = folder_id
                    st.session_state["save_config"] = {
                        "type": "gdrive_manual",
                        "folder_id": folder_id,
                        "folder_url": manual_folder_url
                    }
                    st.session_state["save_config_set"] = True
                    st.success(f"✅ Google Drive folder configured!  Folder ID: {folder_id}")
        else:
            folder_url = st.text_input(
                "Google Drive Folder URL:",
                value="https://drive. google.com/drive/folders/1HIu5XR7pFg8s49AG8Yiu_7aCK9HMeT8N",
                help="Paste the URL of your Google Drive folder"
            )
            
            if st. button("Connect to Google Drive"):
                service = authenticate_google_drive()
                if service:
                    folder_id = extract_folder_id_from_url(folder_url)
                    st.session_state["gdrive_service"] = service
                    st.session_state["gdrive_folder_id"] = folder_id
                    st.session_state["save_config"] = {
                        "type": "gdrive",
                        "folder_id": folder_id,
                        "folder_url": folder_url
                    }
                    st.session_state["save_config_set"] = True
                    st.success(f"✅ Connected to Google Drive! Folder ID: {folder_id}")
                else:
                    st.error("Failed to authenticate with Google Drive")
    
    else:  # Local Storage
        local_path = st.text_input("Local folder path:", value=DEFAULT_UPLOADS)
        if st.button("Set Local Storage"):
            os.makedirs(local_path, exist_ok=True)
            st.session_state["save_config"] = {
                "type": "local",
                "path": local_path
            }
            st.session_state["save_config_set"] = True
            st.success(f"✅ Local storage set to: {local_path}")

if st.session_state["save_config_set"]:
    cfg = st.session_state["save_config"]
    if cfg["type"] == "gdrive":
        st.success(f"✅ Connected to Google Drive folder")
    elif cfg["type"] == "gdrive_manual":
        st. info(f"📁 Manual Google Drive configuration - Folder URL: {cfg['folder_url']}")
    else:
        st.info(f"📁 Using local storage: {cfg. get('path', DEFAULT_UPLOADS)}")

# --- Form: all widgets reference session-state keys ---
with st.form("damage_form", clear_on_submit=False):
    st.subheader("📝 Enter a New Damage")
    
    col1, col2 = st.columns(2)
    
    with col1:
        title = st.text_input("Title*", key="title_input", help="Brief title for this damage")
        category = st.selectbox("Category*", CATEGORY_LIST, key="category_input")
        
        # Show subcategories if available
        if category in SUBCATEGORIES:
            subcategory = st.selectbox(
                f"Subcategory for {category}",
                ["Select... "] + SUBCATEGORIES[category],
                key="subcategory_input"
            )
        
        # Show custom input for "Other" category or subcategory
        if category == "Other" or (category in SUBCATEGORIES and st.session_state. get("subcategory_input") == "Other"):
            custom_category = st.text_input("Please specify:", key="custom_category_input")
        
        cost = st.number_input(
            "Cost (USD)*", 
            min_value=0.0, 
            step=0.01, 
            format="%.2f", 
            key="cost_input",
            help="Enter the amount in USD"
        )
    
    with col2:
        date = st.date_input("Date*", key="date_input", help="Date of the expense/damage")
        description = st. text_area(
            "Description (optional)", 
            key="description_input",
            height=100,
            help="Additional details about this damage"
        )
        image_file = st.file_uploader(
            "Upload Receipt/Invoice (optional)", 
            type=["png", "jpg", "jpeg", "pdf"], 
            key="image_input",
            help="Upload supporting documentation"
        )
    
    submitted = st.form_submit_button("➕ Add Damage", use_container_width=True, type="primary")

# --- Handle submit ---
if submitted:
    if not st.session_state["save_config_set"]:
        st.warning("⚠️ Please configure storage location first (see configuration section above)")
    elif not st.session_state["title_input"] or st.session_state["cost_input"] <= 0:
        st.error("❌ Please provide a title and cost amount")
    else:
        save_cfg = st.session_state["save_config"]
        filename = ""
        image_url = ""
        
        # Handle image upload
        if image_file is not None:
            # Generate unique filename
            timestamp = int(datetime.now().timestamp())
            original_name = Path(image_file.name).stem
            extension = Path(image_file.name).suffix
            filename = f"{timestamp}_{original_name}{extension}"
            
            # Get file content
            file_content = image_file.getbuffer()
            
            # Upload based on configuration
            if save_cfg["type"] == "gdrive" and st.session_state["gdrive_service"]:
                # Upload to Google Drive
                image_url = upload_to_google_drive(
                    st. session_state["gdrive_service"],
                    file_content,
                    filename,
                    st.session_state["gdrive_folder_id"]
                )
                if not image_url:
                    st.error("Failed to upload to Google Drive")
                    
            elif save_cfg["type"] == "gdrive_manual":
                # Save locally but create Google Drive link
                local_path = os.path.join(DEFAULT_UPLOADS, filename)
                with open(local_path, "wb") as f:
                    f.write(file_content)
                # Create expected Google Drive URL
                folder_url = save_cfg["folder_url"]. rstrip("/")
                image_url = f"{folder_url}/{filename}"
                st.info(f"File saved locally.  Manual upload required to: {folder_url}")
                
            else:  # Local storage
                local_path = os.path.join(save_cfg. get("path", DEFAULT_UPLOADS), filename)
                with open(local_path, "wb") as f:
                    f.write(file_content)
                image_url = local_path
        
        # Determine final category
        if st.session_state["category_input"] == "Other":
            final_category = st. session_state["custom_category_input"] or "Other"
        elif st.session_state. get("subcategory_input") == "Other":
            final_category = f"{st.session_state['category_input']} - {st. session_state['custom_category_input']}"
        elif st.session_state. get("subcategory_input") and st.session_state. get("subcategory_input") != "Select...":
            final_category = f"{st.session_state['category_input']} - {st.session_state['subcategory_input']}"
        else:
            final_category = st.session_state["category_input"]
        
        # Create entry
        entry = {
            "Title": st.session_state["title_input"],
            "Description": st.session_state["description_input"],
            "Date": st.session_state["date_input"]. strftime("%Y-%m-%d"),
            "Category": final_category,
            "Cost": float(st.session_state["cost_input"]),
            "Receipt Filename": filename,
            "Receipt Link": image_url
        }
        
        st.session_state["damages"].append(entry)
        st.success("✅ Damage added successfully!")
        
        # Clear form inputs
        st.session_state["title_input"] = ""
        st.session_state["description_input"] = ""
        st.session_state["date_input"] = datetime.today()
        st.session_state["category_input"] = CATEGORY_LIST[0]
        st.session_state["subcategory_input"] = ""
        st.session_state["custom_category_input"] = ""
        st.session_state["cost_input"] = 0.0
        st.session_state["image_input"] = None
        st.rerun()

# --- Display damages and analysis ---
st.header("📊 Damage Summary")

if st.session_state["damages"]:
    df = pd.DataFrame(st.session_state["damages"])
    
    # Display metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        total_cost = df["Cost"].sum()
        st.metric("Total Damages", f"${total_cost:,.2f}")
    with col2:
        st.metric("Number of Entries", len(df))
    with col3:
        avg_cost = df["Cost"].mean()
        st.metric("Average Cost", f"${avg_cost:,.2f}")
    
    # Tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📋 All Entries", "📊 Category Analysis", "🔗 Receipt Links", "📥 Export"])
    
    with tab1:
        st.subheader("All Damage Entries")
        # Create display dataframe with formatted costs
        display_df = df.copy()
        display_df["Cost"] = display_df["Cost"].apply(lambda x: f"${x:,.2f}")
        st.dataframe(
            display_df[["Title", "Description", "Date", "Category", "Cost", "Receipt Filename"]],
            use_container_width=True
        )
    
    with tab2:
        st.subheader("Cost Analysis by Category")
        
        # Category summary
        category_summary = (
            df.groupby("Category")["Cost"]
            .agg(["count", "sum", "mean"])
            .rename(columns={
                "count": "Number of Entries",
                "sum": "Total Cost",
                "mean": "Average Cost"
            })
            .reset_index()
        )
        category_summary["Total Cost"] = category_summary["Total Cost"].apply(lambda x: f"${x:,.2f}")
        category_summary["Average Cost"] = category_summary["Average Cost"].apply(lambda x: f"${x:,.2f}")
        
        st.dataframe(category_summary, use_container_width=True)
        
        # Simple bar chart
        chart_df = df.groupby("Category")["Cost"].sum().reset_index()
        st.bar_chart(chart_df.set_index("Category"))
    
    with tab3:
        st.subheader("📎 Uploaded Receipts")
        for idx, row in df.iterrows():
            if row.get("Receipt Link"):
                url = row["Receipt Link"]
                name = row.get("Receipt Filename") or "Receipt"
                title = row.get("Title", "")
                
                if str(url).startswith("http"):
                    st. markdown(f"**{title}** - [{name}]({url}) 🔗")
                else:
                    col1, col2 = st. columns([3, 1])
                    with col1:
                        st.markdown(f"**{title}** - {name}")
                    with col2:
                        if os.path.exists(url):
                            with open(url, "rb") as f:
                                st.download_button(
                                    "⬇️ Download",
                                    data=f,
                                    file_name=name,
                                    key=f"dl_{idx}"
                                )
    
    with tab4:
        st.subheader("📥 Export Options")
        
        # Prepare export data
        export_df = df. copy()
        
        # Add summary rows
        summary_rows = []
        for category, group in df.groupby("Category"):
            summary_rows.append({
                "Title": f"SUBTOTAL: {category}",
                "Description": "",
                "Date": "",
                "Category": category,
                "Cost": group["Cost"]. sum(),
                "Receipt Filename": "",
                "Receipt Link": ""
            })
        
        # Add grand total
        summary_rows.append({
            "Title": "GRAND TOTAL",
            "Description": "",
            "Date": "",
            "Category": "ALL CATEGORIES",
            "Cost": df["Cost"].sum(),
            "Receipt Filename": "",
            "Receipt Link": ""
        })
        
        # Export to Excel
        excel_buffer = pd.ExcelWriter('damages_export.xlsx', engine='openpyxl')
        
        try:
            # Main data sheet
            export_df.to_excel(excel_buffer, sheet_name='Damage Entries', index=False)
            
            # Category summary sheet
            category_summary_export = df.groupby("Category")["Cost"].agg(["count", "sum"]).reset_index()
            category_summary_export.columns = ["Category", "Number of Entries", "Total Cost"]
            category_summary_export.to_excel(excel_buffer, sheet_name='Category Summary', index=False)
            
            # Summary with subtotals
            summary_df = pd.concat([export_df, pd.DataFrame(summary_rows)], ignore_index=True)
            summary_df.to_excel(excel_buffer, sheet_name='Full Report', index=False)
            
            excel_buffer.close()
            
            with open('damages_export.xlsx', 'rb') as f:
                excel_data = f.read()
            
            col1, col2 = st. columns(2)
            with col1:
                st.download_button(
                    "📊 Download Excel Report",
                    data=excel_data,
                    file_name=f"damages_report_{datetime. now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            with col2:
                csv_data = export_df.to_csv(index=False)
                st.download_button(
                    "📄 Download CSV",
                    data=csv_data,
                    file_name=f"damages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
        except Exception as e:
            st.error(f"Error creating export: {e}")

else:
    st.info("No damages recorded yet. Use the form above to add your first entry.")

# --- Instructions ---
with st.expander("📖 Instructions for Use"):
    st.markdown("""
    ### Getting Started:
    1. **Configure Storage** (one time): Choose Google Drive or local storage in the configuration section
    2. **Add Damages**: Fill out the form with damage details and upload receipts
    3. **Review & Export**: View summaries and export to Excel for legal proceedings
    
    ### Features:
    - ✅ Automatic categorization with subcategories
    - ✅ Receipt/invoice upload with Google Drive integration
    - ✅ Automatic cost calculations and summaries
    - ✅ Excel export with clickable links to receipts
    - ✅ Category-wise cost breakdown
    
    ### For Google Drive Integration:
    - Files are automatically uploaded to your specified folder
    - Links in the Excel file will open directly in Google Drive
    - Ensure the folder is shared appropriately for others to view
    
    ### Tips:
    - Be consistent with categories for better organization
    - Include detailed descriptions for clarity in legal proceedings
    - Upload all relevant receipts and invoices
    - Export regularly to maintain backups
    """)
