import streamlit as st
import pandas as pd
from datetime import datetime
import os
from pathlib import Path
import base64
import io
import json

# --- Page Configuration ---
st. set_page_config(
    page_title="Damage Invoice Tracker", 
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'About': "Damage tracker for legal proceedings"
    }
)

# --- Custom CSS for mobile responsiveness ---
st. markdown("""
<style>
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
    
    .project-header {
        background: linear-gradient(90deg, #1f4e79 0%, #2e75b6 100%);
        color: white;
        padding: 1rem;
        border-radius: 10px;
        margin-bottom: 1rem;
    }
    
    . export-section {
        background-color: #e8f4f8;
        padding: 1. 5rem;
        border-radius: 10px;
        margin-top: 1rem;
        border: 2px solid #1f77b4;
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

# --- Initialize Session State ---
if "damages" not in st.session_state:
    st.session_state["damages"] = []

if "drive_folder_url" not in st.session_state:
    st.session_state["drive_folder_url"] = ""

if "drive_folder_configured" not in st. session_state:
    st.session_state["drive_folder_configured"] = False

if "uploaded_files_data" not in st. session_state:
    st.session_state["uploaded_files_data"] = {}

if "project_name" not in st. session_state:
    st.session_state["project_name"] = ""

if "project_created_date" not in st. session_state:
    st.session_state["project_created_date"] = ""

if "project_active" not in st. session_state:
    st.session_state["project_active"] = False

if "delete_mode" not in st. session_state:
    st.session_state["delete_mode"] = False

# --- Helper Functions ---
def save_uploaded_file(uploaded_file):
    """Save uploaded file to session state and return filename"""
    bytes_data = uploaded_file.getvalue()
    filename = uploaded_file. name
    timestamp = int(datetime.now(). timestamp())
    unique_filename = f"{timestamp}_{filename}"
    
    st.session_state["uploaded_files_data"][unique_filename] = {
        'data': bytes_data,
        'original_name': filename,
        'size': len(bytes_data)
    }
    
    return unique_filename

def generate_drive_link(folder_url, filename):
    """Generate expected Google Drive link"""
    if folder_url:
        folder_url = folder_url. rstrip('/')
        return f"{folder_url}/{filename}"
    return filename

def save_project_to_json():
    """Save current project to JSON for download"""
    project_data = {
        "project_name": st.session_state["project_name"],
        "project_created_date": st.session_state["project_created_date"],
        "drive_folder_url": st.session_state["drive_folder_url"],
        "damages": st.session_state["damages"],
        "last_saved": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return json.dumps(project_data, indent=2)

def load_project_from_json(json_data):
    """Load project from JSON data"""
    try:
        project_data = json. loads(json_data)
        st. session_state["project_name"] = project_data.get("project_name", "")
        st. session_state["project_created_date"] = project_data. get("project_created_date", "")
        st.session_state["drive_folder_url"] = project_data.get("drive_folder_url", "")
        st.session_state["drive_folder_configured"] = bool(project_data. get("drive_folder_url"))
        st.session_state["damages"] = project_data.get("damages", [])
        st.session_state["project_active"] = True
        return True
    except Exception as e:
        st.error(f"Error loading project: {e}")
        return False

def delete_damage_entry(index):
    """Delete a damage entry by index"""
    if 0 <= index < len(st.session_state["damages"]):
        deleted_item = st.session_state["damages"]. pop(index)
        return deleted_item
    return None

def create_comprehensive_excel_report(damages_df, project_name):
    """Create a comprehensive, lawyer-friendly Excel report"""
    output = io.BytesIO()
    
    if len(damages_df) == 0:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            empty_df = pd. DataFrame({'Message': ['No damages recorded yet']})
            empty_df.to_excel(writer, sheet_name='No Data', index=False)
        return output.getvalue()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        
        # SHEET 1: EXECUTIVE SUMMARY
        total_cost = damages_df['Cost'].sum()
        
        summary_data = []
        summary_data.append(['DAMAGE CLAIM SUMMARY REPORT', '', ''])
        summary_data.append([f'Project: {project_name}', '', ''])
        summary_data.append(['', '', ''])
        summary_data.append(['Report Generated:', datetime.now().strftime("%Y-%m-%d %H:%M"), ''])
        summary_data.append(['', '', ''])
        summary_data. append(['KEY METRICS', '', ''])
        summary_data.append(['Total Damages Claimed:', f"${total_cost:,.2f}", ''])
        summary_data.append(['Number of Damage Items:', len(damages_df), ''])
        summary_data. append(['Number of Categories:', damages_df['Category']. nunique(), ''])
        summary_data.append(['Average Damage Amount:', f"${damages_df['Cost']. mean():,.2f}", ''])
        summary_data.append(['Highest Single Damage:', f"${damages_df['Cost'].max():,.2f}", ''])
        summary_data.append(['Lowest Single Damage:', f"${damages_df['Cost'].min():,.2f}", ''])
        summary_data.append(['Date Range:', f"{damages_df['Date']. min()} to {damages_df['Date'].max()}", ''])
        summary_data. append(['', '', ''])
        summary_data.append(['CATEGORY BREAKDOWN', 'Amount', 'Percentage of Total'])
        
        for category in sorted(damages_df['Category'].unique()):
            cat_total = damages_df[damages_df['Category'] == category]['Cost'].sum()
            percentage = (cat_total / total_cost * 100) if total_cost > 0 else 0
            summary_data. append([category, f"${cat_total:,.2f}", f"{percentage:.1f}%"])
        
        summary_data.append(['', '', ''])
        summary_data.append(['GRAND TOTAL:', f"${total_cost:,.2f}", '100. 0%'])
        
        summary_df = pd. DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Executive Summary', index=False, header=False)
        
        # SHEET 2: ALL DAMAGES (CATEGORIZED)
        categorized_list = []
        categorized_list.append(['COMPREHENSIVE DAMAGE LIST - ORGANIZED BY CATEGORY', '', '', '', '', '', ''])
        categorized_list.append([f'Project: {project_name}', '', '', '', '', '', ''])
        categorized_list.append(['', '', '', '', '', '', ''])
        
        sorted_df = damages_df. sort_values(['Category', 'Date'])
        
        current_category = None
        category_totals = {}
        
        for _, row in sorted_df.iterrows():
            if current_category != row['Category']:
                if current_category is not None:
                    categorized_list.append(['', '', '', '', '', '', ''])
                    categorized_list. append([
                        '', '', '', f'SUBTOTAL - {current_category}:',
                        f"${category_totals[current_category]:,. 2f}", '', ''
                    ])
                    categorized_list. append(['', '', '', '', '', '', ''])
                
                current_category = row['Category']
                category_totals[current_category] = 0
                
                categorized_list.append([f"=== CATEGORY: {current_category} ===", '', '', '', '', '', ''])
                categorized_list.append(['Date', 'Title', 'Description', 'Amount', 'Receipt File', 'Receipt Link', 'Notes'])
            
            categorized_list.append([
                row['Date'],
                row['Title'],
                row. get('Description', ''),
                f"${row['Cost']:,.2f}",
                row. get('Receipt', ''),
                row.get('Link', ''),
                ''
            ])
            
            category_totals[current_category] += row['Cost']
        
        if current_category:
            categorized_list.append(['', '', '', '', '', '', ''])
            categorized_list.append([
                '', '', '', f'SUBTOTAL - {current_category}:',
                f"${category_totals[current_category]:,. 2f}", '', ''
            ])
        
        categorized_list.append(['', '', '', '', '', '', ''])
        categorized_list.append(['', '', '', '', '', '', ''])
        categorized_list.append([
            '===================', '', '', 'GRAND TOTAL ALL DAMAGES:',
            f"${damages_df['Cost']. sum():,.2f}", '', ''
        ])
        
        categorized_df = pd.DataFrame(categorized_list)
        categorized_df. to_excel(writer, sheet_name='All Damages Categorized', index=False, header=False)
        
        # SHEET 3: CATEGORY ANALYSIS
        analysis_data = []
        analysis_data. append(['DETAILED CATEGORY ANALYSIS', '', '', '', ''])
        analysis_data.append([f'Project: {project_name}', '', '', '', ''])
        analysis_data. append(['', '', '', '', ''])
        
        for category in sorted(damages_df['Category'].unique()):
            cat_data = damages_df[damages_df['Category'] == category]
            cat_total = cat_data['Cost'].sum()
            percentage = (cat_total / total_cost * 100) if total_cost > 0 else 0
            
            analysis_data. append([f'=== {category} ===', '', '', '', ''])
            analysis_data.append(['Number of Items:', len(cat_data), '', '', ''])
            analysis_data.append(['Total Amount:', f"${cat_total:,.2f}", '', '', ''])
            analysis_data.append(['Percentage of Total:', f"{percentage:.1f}%", '', '', ''])
            analysis_data.append(['Average per Item:', f"${cat_data['Cost'].mean():,.2f}", '', '', ''])
            analysis_data.append(['Highest Item:', f"${cat_data['Cost']. max():,.2f}", '', '', ''])
            analysis_data.append(['Lowest Item:', f"${cat_data['Cost'].min():,.2f}", '', '', ''])
            analysis_data.append(['', '', '', '', ''])
        
        analysis_df = pd.DataFrame(analysis_data)
        analysis_df. to_excel(writer, sheet_name='Category Analysis', index=False, header=False)
        
        # SHEET 4: CHRONOLOGICAL LIST
        chrono_data = []
        chrono_data.append(['CHRONOLOGICAL DAMAGE LIST WITH RUNNING TOTAL', '', '', '', ''])
        chrono_data.append([f'Project: {project_name}', '', '', '', ''])
        chrono_data.append(['', '', '', '', ''])
        chrono_data.append(['Date', 'Category', 'Title', 'Amount', 'Running Total'])
        
        sorted_chrono = damages_df.sort_values('Date')
        running_total = 0
        
        for _, row in sorted_chrono.iterrows():
            running_total += row['Cost']
            chrono_data.append([
                row['Date'],
                row['Category'],
                row['Title'],
                f"${row['Cost']:,.2f}",
                f"${running_total:,.2f}"
            ])
        
        chrono_data.append(['', '', '', '', ''])
        chrono_data.append(['', '', 'FINAL TOTAL:', f"${total_cost:,.2f}", ''])
        
        chrono_df = pd. DataFrame(chrono_data)
        chrono_df.to_excel(writer, sheet_name='Chronological View', index=False, header=False)
        
        # SHEET 5: RECEIPT TRACKING
        receipt_data = []
        receipt_data. append(['RECEIPT DOCUMENTATION STATUS', '', '', ''])
        receipt_data.append([f'Project: {project_name}', '', '', ''])
        receipt_data.append(['', '', '', ''])
        receipt_data.append(['Status', 'Count', 'Amount', ''])
        
        with_receipts = damages_df[damages_df['Receipt'] != '']
        without_receipts = damages_df[damages_df['Receipt'] == '']
        
        receipt_data.append(['Items with Receipts:', len(with_receipts), f"${with_receipts['Cost'].sum():,.2f}", ''])
        receipt_data.append(['Items without Receipts:', len(without_receipts), f"${without_receipts['Cost'].sum():,.2f}", ''])
        receipt_data.append(['Total Items:', len(damages_df), f"${total_cost:,.2f}", ''])
        receipt_data.append(['', '', '', ''])
        
        if len(without_receipts) > 0:
            receipt_data.append(['ITEMS NEEDING RECEIPTS:', '', '', ''])
            receipt_data.append(['Date', 'Title', 'Amount', ''])
            for _, row in without_receipts.iterrows():
                receipt_data.append([row['Date'], row['Title'], f"${row['Cost']:,. 2f}", ''])
        else:
            receipt_data.append(['All items have receipts uploaded', '', '', ''])
        
        receipt_data.append(['', '', '', ''])
        receipt_data.append(['Google Drive Folder:', st.session_state. get("drive_folder_url", "Not configured"), '', ''])
        
        receipt_df = pd.DataFrame(receipt_data)
        receipt_df.to_excel(writer, sheet_name='Receipt Status', index=False, header=False)
    
    return output.getvalue()

def create_legal_summary_document(damages_df, project_name):
    """Create a formatted text document for legal proceedings"""
    if len(damages_df) == 0:
        return "No damages recorded yet."
    
    total_cost = damages_df['Cost'].sum()
    
    summary = f"""
================================================================================
                        DAMAGE CLAIM DOCUMENTATION
                           LEGAL SUMMARY REPORT
================================================================================

PROJECT NAME: {project_name}
REPORT GENERATED: {datetime. now().strftime('%Y-%m-%d at %H:%M')}

--------------------------------------------------------------------------------
I. EXECUTIVE SUMMARY
--------------------------------------------------------------------------------

TOTAL DAMAGES CLAIMED: ${total_cost:,.2f}

This document provides a comprehensive summary of all damages incurred, 
organized by category for legal proceedings. 

Key Statistics:
* Total Number of Damage Items: {len(damages_df)}
* Number of Categories: {damages_df['Category']. nunique()}
* Date Range: {damages_df['Date'].min()} to {damages_df['Date']. max()}
* Average Damage Amount: ${damages_df['Cost'].mean():,.2f}
* Highest Single Damage: ${damages_df['Cost'].max():,.2f}
* Lowest Single Damage: ${damages_df['Cost']. min():,.2f}

--------------------------------------------------------------------------------
II.  DAMAGE BREAKDOWN BY CATEGORY
--------------------------------------------------------------------------------
"""
    
    for category in sorted(damages_df['Category'].unique()):
        cat_data = damages_df[damages_df['Category'] == category]
        cat_total = cat_data['Cost'].sum()
        percentage = (cat_total / total_cost * 100) if total_cost > 0 else 0
        
        summary += f"""
{category. upper()}
{'=' * len(category)}
Total: ${cat_total:,.2f} ({percentage:.1f}% of total damages)
Number of Items: {len(cat_data)}
Average per Item: ${cat_data['Cost'].mean():,.2f}

Itemized List:
"""
        for _, row in cat_data.iterrows():
            summary += f"  - {row['Date']} - {row['Title']}: ${row['Cost']:,.2f}\n"
            if row. get('Description'):
                summary += f"    Description: {row['Description']}\n"
            if row.get('Receipt'):
                summary += f"    Receipt: {row['Receipt']}\n"
        
        summary += f"\n  CATEGORY SUBTOTAL: ${cat_total:,.2f}\n"
    
    summary += f"""
--------------------------------------------------------------------------------
III.  CHRONOLOGICAL LISTING
--------------------------------------------------------------------------------

"""
    sorted_by_date = damages_df.sort_values('Date')
    running_total = 0
    for _, row in sorted_by_date.iterrows():
        running_total += row['Cost']
        cat_short = row['Category'][:25] + "..." if len(row['Category']) > 25 else row['Category']
        title_short = row['Title'][:25] + "..." if len(row['Title']) > 25 else row['Title']
        summary += f"{row['Date']} | {cat_short:28} | {title_short:28} | ${row['Cost']:>10,.2f} | Running: ${running_total:>12,.2f}\n"
    
    summary += f"""
--------------------------------------------------------------------------------
IV. RECEIPT DOCUMENTATION STATUS
--------------------------------------------------------------------------------

Total Items: {len(damages_df)}
Items with Receipts: {len(damages_df[damages_df['Receipt'] != ''])}
Items Missing Receipts: {len(damages_df[damages_df['Receipt'] == ''])}

Receipt Storage Location:
{st.session_state.get('drive_folder_url', 'Not configured')}

--------------------------------------------------------------------------------
V. TOTAL DAMAGES SUMMARY
--------------------------------------------------------------------------------

+-------------------------------------------+
|                                           |
|   GRAND TOTAL OF ALL DAMAGES:             |
|                                           |
|        ${total_cost:>15,.2f}                  |
|                                           |
+-------------------------------------------+

This amount represents the total of all documented damages with supporting 
evidence as detailed above.

--------------------------------------------------------------------------------
                           END OF REPORT
--------------------------------------------------------------------------------
Prepared for: Legal Proceedings
Project: {project_name}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}
================================================================================
"""
    
    return summary

# --- Main App ---
st.title("⚖️ Damage Invoice Tracker")
st.markdown("### Legal Proceedings Documentation System")

# --- Project Management Section ---
if not st.session_state["project_active"]:
    st.markdown("---")
    st. header("📁 Project Management")
    
    tab1, tab2 = st.tabs(["🆕 Create New Project", "📂 Load Existing Project"])
    
    with tab1:
        st.subheader("Start a New Damage Claim Project")
        
        new_project_name = st.text_input(
            "Project Name *",
            placeholder="e.g., Smith vs. Johnson - Vehicle Accident 2024",
            help="Give your project a descriptive name for easy identification"
        )
        
        project_description = st.text_area(
            "Case Description (optional)",
            placeholder="Brief description of the case and damages being tracked.. .",
            height=100
        )
        
        if st.button("🚀 Create Project", type="primary", use_container_width=True):
            if new_project_name:
                st.session_state["project_name"] = new_project_name
                st.session_state["project_created_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.session_state["project_active"] = True
                st.session_state["damages"] = []
                st.success(f"✅ Project '{new_project_name}' created successfully!")
                st.rerun()
            else:
                st.error("❌ Please enter a project name")
    
    with tab2:
        st.subheader("Load a Previously Saved Project")
        
        uploaded_project = st.file_uploader(
            "Upload Project File (. json)",
            type=["json"],
            help="Select a previously saved project file to continue working"
        )
        
        if uploaded_project is not None:
            if st.button("📂 Load Project", type="primary", use_container_width=True):
                json_data = uploaded_project.read(). decode('utf-8')
                if load_project_from_json(json_data):
                    st.success(f"✅ Project '{st.session_state['project_name']}' loaded successfully!")
                    st.rerun()
        
        st.markdown("---")
        st.info("""
        💡 **How Project Files Work:**
        - When you save your project, you download a `.json` file
        - Keep this file safe - it contains all your damage entries
        - Upload it here to continue working on your project
        - You can save as many versions as you want
        """)

else:
    # --- Active Project Header ---
    total_damages = sum(d['Cost'] for d in st.session_state['damages'])
    st.markdown(f"""
    <div style="background: linear-gradient(90deg, #1f4e79 0%, #2e75b6 100%); 
                color: white; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;">
        <h3 style="margin: 0; color: white;">📁 Project: {st.session_state['project_name']}</h3>
        <p style="margin: 0. 5rem 0 0 0; font-size: 0.9rem; color: #e0e0e0;">
            Created: {st.session_state['project_created_date']} | 
            Entries: {len(st.session_state['damages'])} | 
            Total: ${total_damages:,.2f}
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # --- Project Actions ---
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        project_json = save_project_to_json()
        safe_name = st.session_state['project_name']. replace(' ', '_'). replace('/', '-')
        st.download_button(
            "💾 Save Project",
            data=project_json,
            file_name=f"{safe_name}_{datetime.now(). strftime('%Y%m%d_%H%M')}.json",
            mime="application/json",
            use_container_width=True,
            help="Download project file to continue later"
        )
    
    with col2:
        if st.button("🔄 Switch Project", use_container_width=True):
            st.session_state["project_active"] = False
            st.rerun()
    
    with col3:
        delete_label = "✅ Done Editing" if st.session_state["delete_mode"] else "🗑️ Edit/Delete"
        if st.button(delete_label, use_container_width=True):
            st.session_state["delete_mode"] = not st.session_state["delete_mode"]
            st.rerun()
    
    with col4:
        if st. button("📤 Quick Export", use_container_width=True, type="primary"):
            pass  # Export section is below
    
    # --- Configuration Section ---
    with st.expander("⚙️ Configure Google Drive Folder", expanded=not st.session_state["drive_folder_configured"]):
        st.markdown("📁 **Set your Google Drive folder where receipts will be stored**")
        
        drive_url = st.text_input(
            "Google Drive Folder URL:",
            value=st.session_state.get("drive_folder_url", ""),
            help="Example: https://drive. google.com/drive/folders/..."
        )
        
        if st. button("Save Configuration"):
            st.session_state["drive_folder_url"] = drive_url
            st.session_state["drive_folder_configured"] = True
            st. success("✅ Configuration saved!")
            st.rerun()

    if st.session_state["drive_folder_configured"]:
        st.success("✅ Google Drive folder configured")
    
    # --- Delete Mode UI ---
    if st.session_state["delete_mode"]:
        st.markdown("---")
        st.warning("🗑️ **Edit Mode Active** - Click the ❌ button next to any entry to delete it")
        
        if st.session_state["damages"]:
            for idx, damage in enumerate(st. session_state["damages"]):
                col1, col2, col3, col4, col5 = st.columns([1, 2, 3, 2, 1])
                
                with col1:
                    st.write(f"#{idx + 1}")
                with col2:
                    st.write(damage['Date'])
                with col3:
                    title_display = damage['Title'][:35] + "..." if len(damage['Title']) > 35 else damage['Title']
                    st. write(title_display)
                with col4:
                    st.write(f"${damage['Cost']:,.2f}")
                with col5:
                    if st.button("❌", key=f"delete_{idx}", help=f"Delete: {damage['Title']}"):
                        deleted = delete_damage_entry(idx)
                        if deleted:
                            st. success(f"Deleted: {deleted['Title']}")
                            st.rerun()
        else:
            st. info("No entries to delete")
    
    else:
        # --- Entry Form ---
        st. markdown("---")
        st.subheader("📝 Add New Damage Entry")

        with st.form("damage_form", clear_on_submit=True):
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
                
                subcategory = ""
                custom_subcategory = ""
                if category in SUBCATEGORIES:
                    subcategory = st. selectbox(
                        "Subcategory",
                        ["Select... "] + SUBCATEGORIES[category],
                        key="form_subcategory"
                    )
                    
                    if subcategory == "Other":
                        custom_subcategory = st.text_input(
                            "Specify:",
                            placeholder="Enter custom subcategory",
                            key="form_custom_subcategory"
                        )
                
                custom_category = ""
                if category == "Other":
                    custom_category = st.text_input(
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
                    min_value=0. 0,
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
            
            image_file = st.file_uploader(
                "📎 Upload Receipt/Invoice",
                type=["png", "jpg", "jpeg", "pdf"],
                help="Upload supporting documentation",
                key="form_file"
            )
            
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
                filename = ""
                file_link = ""
                
                if image_file is not None:
                    filename = save_uploaded_file(image_file)
                    if st.session_state["drive_folder_configured"]:
                        file_link = generate_drive_link(st.session_state["drive_folder_url"], filename)
                    else:
                        file_link = filename
                
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
                
                entry = {
                    "Title": title,
                    "Description": description,
                    "Date": date. strftime("%Y-%m-%d"),
                    "Category": final_category,
                    "Cost": float(cost),
                    "Receipt": filename,
                    "Link": file_link
                }
                
                st.session_state["damages"].append(entry)
                st.success("✅ Damage entry added successfully!")
                
                if image_file and st.session_state["drive_folder_configured"]:
                    st.info(f"📤 Upload `{filename}` to your Google Drive folder")
                    if filename in st.session_state["uploaded_files_data"]:
                        file_data = st.session_state["uploaded_files_data"][filename]['data']
                        st.download_button(
                            label=f"⬇️ Download {filename}",
                            data=file_data,
                            file_name=filename,
                            mime="application/octet-stream",
                            key=f"download_{filename}"
                        )
                
                st.rerun()
    
    # --- Display and Export Section ---
    st.markdown("---")
    st.header("📊 Damage Summary")

    if st.session_state["damages"]:
        df = pd.DataFrame(st.session_state["damages"])
        
        total_cost = df["Cost"].sum()
        
        # Main metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("💰 TOTAL DAMAGES", f"${total_cost:,.2f}")
        with col2:
            st.metric("📝 Total Items", len(df))
        with col3:
            st.metric("📊 Average", f"${df['Cost']. mean():,.2f}")
        with col4:
            st.metric("📁 Categories", df["Category"].nunique())
        
        # Category breakdown
        st.markdown("### 📂 Breakdown by Category")
        
        for category in sorted(df['Category'].unique()):
            cat_data = df[df['Category'] == category]
            cat_total = cat_data['Cost'].sum()
            percentage = (cat_total / total_cost * 100) if total_cost > 0 else 0
            
            with st.expander(f"**{category}** - ${cat_total:,. 2f} ({percentage:.1f}%)", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Total:** ${cat_total:,.2f}")
                with col2:
                    st.write(f"**Items:** {len(cat_data)}")
                with col3:
                    st. write(f"**Average:** ${cat_data['Cost'].mean():,.2f}")
                
                st.markdown("**Items:**")
                for _, item in cat_data. iterrows():
                    receipt_status = "✅" if item['Receipt'] else "❌"
                    st.write(f"• {item['Date']} - {item['Title']}: **${item['Cost']:,. 2f}** {receipt_status}")
        
        # Grand Total Display
        st.markdown("---")
        st. markdown(f"""
        <div style="background-color: #d4edda; padding: 1. 5rem; border-radius: 10px; 
                    border: 2px solid #28a745; text-align: center;">
            <h2 style="color: #155724; margin: 0;">💰 GRAND TOTAL DAMAGES</h2>
            <h1 style="color: #155724; margin: 0. 5rem 0; font-size: 3rem;">${total_cost:,.2f}</h1>
            <p style="color: #155724; margin: 0;">{len(df)} items across {df['Category']. nunique()} categories</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Export Section
        st.markdown("---")
        st.markdown("### 📥 Export for Attorney")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            excel_data = create_comprehensive_excel_report(df, st.session_state["project_name"])
            safe_name = st. session_state['project_name'].replace(' ', '_').replace('/', '-')
            st.download_button(
                "📊 Download Excel Report",
                data=excel_data,
                file_name=f"{safe_name}_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            st.caption("Complete formatted report")
        
        with col2:
            legal_summary = create_legal_summary_document(df, st.session_state["project_name"])
            st. download_button(
                "📄 Download Legal Summary",
                data=legal_summary,
                file_name=f"{safe_name}_Legal_Summary.txt",
                mime="text/plain",
                use_container_width=True
            )
            st.caption("Formatted text document")
        
        with col3:
            csv_data = df.to_csv(index=False). encode('utf-8')
            st. download_button(
                "📈 Download CSV Data",
                data=csv_data,
                file_name=f"{safe_name}_Data.csv",
                mime="text/csv",
                use_container_width=True
            )
            st.caption("Raw data format")
        
        # View tabs
        st.markdown("---")
        tab1, tab2, tab3 = st.tabs(["📋 All Entries", "📊 Charts", "📎 Receipts"])
        
        with tab1:
            display_df = df.copy()
            display_df['Cost_Display'] = display_df['Cost'].apply(lambda x: f"${x:,.2f}")
            display_df['Has Receipt'] = display_df['Receipt'].apply(lambda x: '✅' if x else '❌')
            st.dataframe(
                display_df[['Date', 'Category', 'Title', 'Description', 'Cost_Display', 'Has Receipt']]. rename(columns={'Cost_Display': 'Cost'}),
                use_container_width=True,
                height=400
            )
        
        with tab2:
            category_totals = df.groupby('Category')['Cost'].sum(). sort_values(ascending=False)
            st.bar_chart(category_totals)
        
        with tab3:
            receipts_uploaded = len(df[df['Receipt'] != ''])
            receipts_missing = len(df[df['Receipt'] == ''])
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("✅ With Receipts", receipts_uploaded)
            with col2:
                st.metric("❌ Missing Receipts", receipts_missing)
            
            if receipts_missing > 0:
                st.warning(f"**{receipts_missing} items need receipts:**")
                for _, item in df[df['Receipt'] == '']. iterrows():
                    st.write(f"• {item['Date']} - {item['Title']}: ${item['Cost']:,. 2f}")

    else:
        st.info("No damages recorded yet. Add your first entry using the form above.")

# --- Footer ---
st.markdown("---")
st.caption("Damage Invoice Tracker v4.0 | Legal Documentation System")
