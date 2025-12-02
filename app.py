import streamlit as st
import pandas as pd
from datetime import datetime
import os
from pathlib import Path
import base64
import io
from PIL import Image

# --- Page Configuration ---
st.set_page_config(
    page_title="Damage Invoice Tracker", 
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'About': "Damage tracker for legal proceedings"
    }
)

# --- Custom CSS for mobile responsiveness ---
st.markdown("""
<style>
    /* Mobile responsive adjustments */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
        }
        .stButton > button {
            width: 100%;
            margin-top: 0.5rem;
        }
    }
    
    /* Make file uploader more prominent */
    .uploadedFile {
        background-color: #f0f8ff;
        border-radius: 5px;
        padding: 10px;
    }
    
    /* Style for clickable links */
    .receipt-link {
        color: #0066cc;
        text-decoration: none;
        font-weight: bold;
    }
    
    .receipt-link:hover {
        text-decoration: underline;
    }
</style>
""", unsafe_allow_html=True)

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

# --- Initialize Session State (without conflicting with widget keys) ---
if "damages" not in st.session_state:
    st.session_state["damages"] = []

if "drive_folder_url" not in st.session_state:
    st.session_state["drive_folder_url"] = ""

if "drive_folder_configured" not in st.session_state:
    st.session_state["drive_folder_configured"] = False

if "uploaded_files_data" not in st.session_state:
    st.session_state["uploaded_files_data"] = {}

# Track if form should be cleared
if "clear_form" not in st.session_state:
    st.session_state["clear_form"] = False

# --- Helper Functions ---
def save_uploaded_file(uploaded_file):
    """Save uploaded file to session state and return base64 data"""
    bytes_data = uploaded_file.getvalue()
    filename = uploaded_file.name
    
    # Generate unique filename
    timestamp = int(datetime.now().timestamp())
    unique_filename = f"{timestamp}_{filename}"
    
    # Store in session state
    st.session_state["uploaded_files_data"][unique_filename] = {
        'data': bytes_data,
        'original_name': filename,
        'size': len(bytes_data)
    }
    
    return unique_filename

def generate_drive_link(folder_url, filename):
    """Generate expected Google Drive link"""
    if folder_url:
        # Clean the folder URL
        folder_url = folder_url.rstrip('/')
        # For now, we'll create a placeholder link structure
        # Users will need to manually upload and the link will work once the file is there
        return f"{folder_url}/{filename}"
    return filename

# --- Main App ---
st.title("⚖️ Damage Invoice Tracker")
st.markdown("### Legal Proceedings Documentation System")

# --- Configuration Section ---
with st.expander("⚙️ Configure Google Drive Folder (One-time Setup)", expanded=not st.session_state["drive_folder_configured"]):
    st.markdown("""
    📁 **Set your Google Drive folder where receipts will be stored**
    
    1. Create or open a folder in Google Drive
    2. Right-click → "Get link" → Set to "Anyone with the link can view"
    3. Copy the folder URL and paste below
    """)
    
    drive_url = st.text_input(
        "Google Drive Folder URL:",
        value=st.session_state. get("drive_folder_url", "https://drive.google.com/drive/folders/1HIu5XR7pFg8s49AG8Yiu_7aCK9HMeT8N"),
        help="Example: https://drive.google.com/drive/folders/..."
    )
    
    col1, col2 = st. columns([1, 3])
    with col1:
        if st.button("Save Configuration", type="primary", use_container_width=True):
            st.session_state["drive_folder_url"] = drive_url
            st.session_state["drive_folder_configured"] = True
            st.success("✅ Configuration saved!")
            st.rerun()
    
    with col2:
        st.info("ℹ️ You'll manually upload files to this folder. The app generates the links.")

if st.session_state["drive_folder_configured"]:
    st.success(f"✅ Connected to folder: `{st.session_state['drive_folder_url']}`")

# --- Entry Form ---
st.markdown("---")
st. subheader("📝 Add New Damage Entry")

with st. form("damage_form", clear_on_submit=True):
    # Responsive columns - stack on mobile
    col1, col2 = st.columns([1, 1])
    
    with col1:
        title = st.text_input(
            "Title *",
            placeholder="Brief description",
            key="form_title"
        )
        
        category = st.selectbox(
            "Category *",
            CATEGORY_LIST,
            key="form_category"
        )
        
        # Show subcategories if available
        subcategory = ""
        custom_subcategory = ""
        if category in SUBCATEGORIES:
            subcategory = st.selectbox(
                f"Subcategory",
                ["Select... "] + SUBCATEGORIES[category],
                key="form_subcategory"
            )
            
            # Custom input for "Other" subcategory
            if subcategory == "Other":
                custom_subcategory = st.text_input(
                    "Specify:",
                    placeholder="Enter custom subcategory",
                    key="form_custom_subcategory"
                )
        
        # Custom input for "Other" main category
        custom_category = ""
        if category == "Other":
            custom_category = st. text_input(
                "Specify category:",
                placeholder="Enter custom category",
                key="form_custom_category"
            )
    
    with col2:
        date = st.date_input(
            "Date *",
            value=datetime.today(),
            key="form_date"
        )
        
        cost = st.number_input(
            "Cost (USD) *",
            min_value=0.0,
            step=0.01,
            format="%.2f",
            value=0.0,
            key="form_cost"
        )
        
        description = st.text_area(
            "Description",
            height=70,
            placeholder="Additional details (optional)",
            key="form_description"
        )
    
    # File upload - full width for better mobile experience
    image_file = st.file_uploader(
        "📎 Upload Receipt/Invoice",
        type=["png", "jpg", "jpeg", "pdf"],
        help="Upload supporting documentation",
        key="form_file"
    )
    
    # Submit button - full width on mobile
    submitted = st.form_submit_button(
        "➕ Add Damage Entry",
        type="primary",
        use_container_width=True
    )

# --- Handle Form Submission ---
if submitted:
    if not title:
        st.error("❌ Please provide a title")
    elif cost <= 0:
        st.error("❌ Please enter a valid cost amount")
    else:
        # Handle file upload
        filename = ""
        file_link = ""
        
        if image_file is not None:
            # Save file to session state
            filename = save_uploaded_file(image_file)
            
            # Generate Google Drive link (for manual upload)
            if st.session_state["drive_folder_configured"]:
                file_link = generate_drive_link(st.session_state["drive_folder_url"], filename)
            else:
                file_link = filename
        
        # Determine final category
        if category == "Other":
            final_category = custom_category if custom_category else "Other"
        elif category in SUBCATEGORIES and subcategory not in ["Select...", None, ""]:
            if subcategory == "Other":
                subcategory_text = custom_subcategory if custom_subcategory else "Other"
            else:
                subcategory_text = subcategory
            final_category = f"{category} - {subcategory_text}"
        else:
            final_category = category
        
        # Create entry
        entry = {
            "Title": title,
            "Description": description,
            "Date": date.strftime("%Y-%m-%d"),
            "Category": final_category,
            "Cost": float(cost),
            "Receipt": filename,
            "Link": file_link
        }
        
        st.session_state["damages"].append(entry)
        
        # Show success message with instructions
        st.success("✅ Damage entry added successfully!")
        
        if image_file and st.session_state["drive_folder_configured"]:
            st. info(f"""
            📤 **Next Step:** Upload `{filename}` to your Google Drive folder:
            1. Download the file using the link below
            2. Upload to your Google Drive folder
            3. The link in the spreadsheet will work automatically
            """)
            
            # Provide download link for the file
            if filename in st.session_state["uploaded_files_data"]:
                file_data = st.session_state["uploaded_files_data"][filename]['data']
                st.download_button(
                    label=f"⬇️ Download {filename} for Google Drive upload",
                    data=file_data,
                    file_name=filename,
                    mime="application/octet-stream",
                    key=f"download_{filename}"
                )
        
        # Trigger rerun to clear form
        st.rerun()

# --- Display Damages ---
st.markdown("---")
st. header("📊 Damage Summary & Export")

if st.session_state["damages"]:
    df = pd.DataFrame(st.session_state["damages"])
    
    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        total_cost = df["Cost"].sum()
        st.metric("💰 Total Damages", f"${total_cost:,.2f}")
    with col2:
        st.metric("📝 Total Entries", len(df))
    with col3:
        avg_cost = df["Cost"].mean()
        st.metric("📊 Average Cost", f"${avg_cost:,.2f}")
    with col4:
        st.metric("📁 Categories", df["Category"].nunique())
    
    # Tabs for different views
    tab1, tab2, tab3 = st.tabs(["📋 All Entries", "📊 Analysis", "📥 Export"])
    
    with tab1:
        # Display entries
        for idx, row in df.iterrows():
            with st.expander(f"{row['Title']} - ${row['Cost']:,.2f} ({row['Date']})"):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.write(f"**Category:** {row['Category']}")
                    if row['Description']:
                        st.write(f"**Description:** {row['Description']}")
                with col2:
                    st.write(f"**Cost:** ${row['Cost']:,.2f}")
                    st.write(f"**Date:** {row['Date']}")
                
                if row. get('Link') and row['Link']:
                    if row['Link'].startswith('http'):
                        st.markdown(f"📎 [View Receipt]({row['Link']})")
                    else:
                        st.write(f"📎 Receipt: {row. get('Receipt', 'N/A')}")
                    
                    # Provide download if file is in session
                    if row.get('Receipt') in st.session_state. get("uploaded_files_data", {}):
                        file_data = st.session_state["uploaded_files_data"][row['Receipt']]['data']
                        st.download_button(
                            "⬇️ Download Receipt",
                            data=file_data,
                            file_name=row['Receipt'],
                            key=f"entry_download_{idx}"
                        )
    
    with tab2:
        # Category breakdown
        st.subheader("Category Breakdown")
        
        category_summary = df.groupby("Category"). agg({
            "Cost": ["count", "sum", "mean"]
        }).round(2)
        category_summary.columns = ["Count", "Total ($)", "Average ($)"]
        category_summary = category_summary.sort_values("Total ($)", ascending=False)
        
        st.dataframe(category_summary, use_container_width=True)
        
        # Simple chart
        st.bar_chart(category_summary["Total ($)"])
    
    with tab3:
        st.subheader("Export Options")
        
        # Prepare Excel file with multiple sheets
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Main entries sheet
            df.to_excel(writer, sheet_name='Damage Entries', index=False)
            
            # Category summary sheet
            category_summary_export = df.groupby("Category").agg({
                "Cost": ["count", "sum"]
            }).round(2)
            category_summary_export.columns = ["Number of Entries", "Total Cost"]
            category_summary_export. to_excel(writer, sheet_name='Category Summary')
            
            # Detailed report with subtotals
            detailed_df = df.copy()
            subtotal_rows = []
            
            # Add subtotal rows
            for category in df["Category"].unique():
                cat_data = df[df["Category"] == category]
                subtotal_row = {
                    "Title": f"SUBTOTAL - {category}",
                    "Description": "",
                    "Date": "",
                    "Category": category,
                    "Cost": cat_data["Cost"].sum(),
                    "Receipt": "",
                    "Link": ""
                }
                subtotal_rows.append(subtotal_row)
            
            # Add grand total
            grand_total_row = {
                "Title": "GRAND TOTAL",
                "Description": "",
                "Date": "",
                "Category": "ALL CATEGORIES",
                "Cost": df["Cost"].sum(),
                "Receipt": "",
                "Link": ""
            }
            
            # Combine all data
            subtotal_df = pd.DataFrame(subtotal_rows)
            grand_total_df = pd.DataFrame([grand_total_row])
            detailed_df = pd.concat([detailed_df, subtotal_df, grand_total_df], ignore_index=True)
            
            detailed_df.to_excel(writer, sheet_name='Detailed Report', index=False)
        
        excel_data = output.getvalue()
        
        col1, col2 = st. columns(2)
        with col1:
            st.download_button(
                "📊 Download Excel Report",
                data=excel_data,
                file_name=f"damage_report_{datetime. now().strftime('%Y%m%d_%H%M')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col2:
            csv_data = df.to_csv(index=False). encode('utf-8')
            st.download_button(
                "📄 Download CSV",
                data=csv_data,
                file_name=f"damages_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        # Instructions for upload
        if st.session_state["drive_folder_configured"]:
            st.info("""
            📤 **To complete the process:**
            1. Download the Excel report above
            2. Upload any receipt files to your Google Drive folder
            3. The links in the Excel file will work once files are uploaded
            4. Share the Excel file and Google Drive folder with your attorney
            """)

else:
    st.info("No damages recorded yet. Add your first entry using the form above.")

# --- Instructions ---
with st.expander("📖 How to Use This App"):
    st.markdown("""
    ### Quick Start:
    
    1. **One-time Setup:**
       - Create a folder in Google Drive
       - Set it to "Anyone with link can view"
       - Paste the folder URL in the configuration section
    
    2. **Adding Damages:**
       - Fill out the form with damage details
       - Upload receipt/invoice images
       - Click "Add Damage Entry"
       - Download the receipt file and upload it to your Google Drive folder
    
    3. **Export for Legal Use:**
       - Review all entries in the summary
       - Download the Excel report
       - Share both the Excel file and Google Drive folder with your attorney
    
    ### Mobile Usage:
    - This app works on all devices
    - Take photos of receipts directly from your phone
    - Upload and track damages on the go
    
    ### Tips:
    - Be consistent with categories
    - Upload clear photos of all receipts
    - Add descriptions for context
    - Export regularly for backup
    """)

# --- Footer ---
st.markdown("---")
st.caption("Damage Invoice Tracker v2.0 | Designed for legal proceedings documentation")
