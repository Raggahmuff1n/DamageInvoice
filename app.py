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

# --- Custom CSS ---
st.markdown("""
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

if "drive_folder_url" not in st. session_state:
    st.session_state["drive_folder_url"] = ""

if "drive_folder_configured" not in st. session_state:
    st.session_state["drive_folder_configured"] = False

if "uploaded_files_data" not in st. session_state:
    st.session_state["uploaded_files_data"] = {}

if "project_name" not in st.session_state:
    st.session_state["project_name"] = ""

if "project_created_date" not in st. session_state:
    st.session_state["project_created_date"] = ""

if "project_active" not in st. session_state:
    st.session_state["project_active"] = False

if "delete_mode" not in st. session_state:
    st.session_state["delete_mode"] = False


def save_uploaded_file(uploaded_file):
    bytes_data = uploaded_file.getvalue()
    filename = uploaded_file. name
    timestamp = int(datetime.now(). timestamp())
    unique_filename = str(timestamp) + "_" + filename
    st.session_state["uploaded_files_data"][unique_filename] = {
        'data': bytes_data,
        'original_name': filename,
        'size': len(bytes_data)
    }
    return unique_filename


def generate_drive_link(folder_url, filename):
    if folder_url:
        folder_url = folder_url. rstrip('/')
        return folder_url + "/" + filename
    return filename


def save_project_to_json():
    project_data = {
        "project_name": st. session_state["project_name"],
        "project_created_date": st.session_state["project_created_date"],
        "drive_folder_url": st.session_state["drive_folder_url"],
        "damages": st.session_state["damages"],
        "last_saved": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return json.dumps(project_data, indent=2)


def load_project_from_json(json_data):
    try:
        project_data = json.loads(json_data)
        st.session_state["project_name"] = project_data.get("project_name", "")
        st.session_state["project_created_date"] = project_data.get("project_created_date", "")
        st. session_state["drive_folder_url"] = project_data. get("drive_folder_url", "")
        st.session_state["drive_folder_configured"] = bool(project_data. get("drive_folder_url"))
        st.session_state["damages"] = project_data. get("damages", [])
        st. session_state["project_active"] = True
        return True
    except Exception as e:
        st.error("Error loading project: " + str(e))
        return False


def delete_damage_entry(index):
    if index >= 0 and index < len(st. session_state["damages"]):
        deleted_item = st.session_state["damages"].pop(index)
        return deleted_item
    return None


def create_comprehensive_excel_report(damages_df, project_name):
    output = io.BytesIO()
    
    if len(damages_df) == 0:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            empty_df = pd.DataFrame({'Message': ['No damages recorded yet']})
            empty_df.to_excel(writer, sheet_name='No Data', index=False)
        return output. getvalue()
    
    with pd. ExcelWriter(output, engine='openpyxl') as writer:
        total_cost = damages_df['Cost'].sum()
        
        # SHEET 1: EXECUTIVE SUMMARY
        summary_data = []
        summary_data.append(['DAMAGE CLAIM SUMMARY REPORT', '', ''])
        summary_data.append(['Project: ' + project_name, '', ''])
        summary_data. append(['', '', ''])
        summary_data.append(['Report Generated:', datetime.now().strftime("%Y-%m-%d %H:%M"), ''])
        summary_data.append(['', '', ''])
        summary_data. append(['KEY METRICS', '', ''])
        summary_data.append(['Total Damages Claimed:', "${:,.2f}".format(total_cost), ''])
        summary_data. append(['Number of Damage Items:', len(damages_df), ''])
        summary_data. append(['Number of Categories:', damages_df['Category']. nunique(), ''])
        summary_data.append(['Average Damage Amount:', "${:,.2f}".format(damages_df['Cost']. mean()), ''])
        summary_data.append(['Highest Single Damage:', "${:,.2f}".format(damages_df['Cost'].max()), ''])
        summary_data.append(['Lowest Single Damage:', "${:,.2f}".format(damages_df['Cost']. min()), ''])
        summary_data.append(['Date Range:', str(damages_df['Date'].min()) + " to " + str(damages_df['Date'].max()), ''])
        summary_data.append(['', '', ''])
        summary_data.append(['CATEGORY BREAKDOWN', 'Amount', 'Percentage of Total'])
        
        for category in sorted(damages_df['Category'].unique()):
            cat_total = damages_df[damages_df['Category'] == category]['Cost'].sum()
            percentage = (cat_total / total_cost * 100) if total_cost > 0 else 0
            summary_data. append([category, "${:,.2f}".format(cat_total), "{:.1f}%".format(percentage)])
        
        summary_data.append(['', '', ''])
        summary_data.append(['GRAND TOTAL:', "${:,.2f}".format(total_cost), '100.0%'])
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='Executive Summary', index=False, header=False)
        
        # SHEET 2: ALL DAMAGES CATEGORIZED
        categorized_list = []
        categorized_list.append(['COMPREHENSIVE DAMAGE LIST - ORGANIZED BY CATEGORY', '', '', '', '', '', ''])
        categorized_list.append(['Project: ' + project_name, '', '', '', '', '', ''])
        categorized_list.append(['', '', '', '', '', '', ''])
        
        sorted_df = damages_df. sort_values(['Category', 'Date'])
        current_category = None
        category_totals = {}
        
        for idx, row in sorted_df.iterrows():
            if current_category != row['Category']:
                if current_category is not None:
                    categorized_list.append(['', '', '', '', '', '', ''])
                    categorized_list. append(['', '', '', 'SUBTOTAL - ' + current_category + ':', "${:,.2f}".format(category_totals[current_category]), '', ''])
                    categorized_list. append(['', '', '', '', '', '', ''])
                
                current_category = row['Category']
                category_totals[current_category] = 0
                categorized_list.append(['=== CATEGORY: ' + current_category + ' ===', '', '', '', '', '', ''])
                categorized_list. append(['Date', 'Title', 'Description', 'Amount', 'Receipt File', 'Receipt Link', 'Notes'])
            
            categorized_list.append([
                row['Date'],
                row['Title'],
                row. get('Description', ''),
                "${:,.2f}".format(row['Cost']),
                row. get('Receipt', ''),
                row.get('Link', ''),
                ''
            ])
            category_totals[current_category] = category_totals[current_category] + row['Cost']
        
        if current_category:
            categorized_list.append(['', '', '', '', '', '', ''])
            categorized_list.append(['', '', '', 'SUBTOTAL - ' + current_category + ':', "${:,.2f}".format(category_totals[current_category]), '', ''])
        
        categorized_list.append(['', '', '', '', '', '', ''])
        categorized_list.append(['', '', '', '', '', '', ''])
        categorized_list.append(['===================', '', '', 'GRAND TOTAL ALL DAMAGES:', "${:,.2f}".format(damages_df['Cost']. sum()), '', ''])
        
        categorized_df = pd.DataFrame(categorized_list)
        categorized_df. to_excel(writer, sheet_name='All Damages Categorized', index=False, header=False)
        
        # SHEET 3: CATEGORY ANALYSIS
        analysis_data = []
        analysis_data. append(['DETAILED CATEGORY ANALYSIS', '', '', '', ''])
        analysis_data.append(['Project: ' + project_name, '', '', '', ''])
        analysis_data.append(['', '', '', '', ''])
        
        for category in sorted(damages_df['Category'].unique()):
            cat_data = damages_df[damages_df['Category'] == category]
            cat_total = cat_data['Cost']. sum()
            percentage = (cat_total / total_cost * 100) if total_cost > 0 else 0
            
            analysis_data. append(['=== ' + category + ' ===', '', '', '', ''])
            analysis_data.append(['Number of Items:', len(cat_data), '', '', ''])
            analysis_data.append(['Total Amount:', "${:,.2f}".format(cat_total), '', '', ''])
            analysis_data.append(['Percentage of Total:', "{:.1f}%".format(percentage), '', '', ''])
            analysis_data.append(['Average per Item:', "${:,. 2f}".format(cat_data['Cost'].mean()), '', '', ''])
            analysis_data. append(['Highest Item:', "${:,.2f}".format(cat_data['Cost'].max()), '', '', ''])
            analysis_data.append(['Lowest Item:', "${:,.2f}".format(cat_data['Cost']. min()), '', '', ''])
            analysis_data.append(['', '', '', '', ''])
        
        analysis_df = pd.DataFrame(analysis_data)
        analysis_df.to_excel(writer, sheet_name='Category Analysis', index=False, header=False)
        
        # SHEET 4: CHRONOLOGICAL LIST
        chrono_data = []
        chrono_data.append(['CHRONOLOGICAL DAMAGE LIST WITH RUNNING TOTAL', '', '', '', ''])
        chrono_data.append(['Project: ' + project_name, '', '', '', ''])
        chrono_data. append(['', '', '', '', ''])
        chrono_data.append(['Date', 'Category', 'Title', 'Amount', 'Running Total'])
        
        sorted_chrono = damages_df.sort_values('Date')
        running_total = 0
        
        for idx, row in sorted_chrono.iterrows():
            running_total = running_total + row['Cost']
            chrono_data.append([
                row['Date'],
                row['Category'],
                row['Title'],
                "${:,.2f}".format(row['Cost']),
                "${:,.2f}".format(running_total)
            ])
        
        chrono_data.append(['', '', '', '', ''])
        chrono_data.append(['', '', 'FINAL TOTAL:', "${:,.2f}".format(total_cost), ''])
        
        chrono_df = pd.DataFrame(chrono_data)
        chrono_df.to_excel(writer, sheet_name='Chronological View', index=False, header=False)
        
        # SHEET 5: RECEIPT TRACKING
        receipt_data = []
        receipt_data. append(['RECEIPT DOCUMENTATION STATUS', '', '', ''])
        receipt_data.append(['Project: ' + project_name, '', '', ''])
        receipt_data.append(['', '', '', ''])
        receipt_data. append(['Status', 'Count', 'Amount', ''])
        
        with_receipts = damages_df[damages_df['Receipt'] != '']
        without_receipts = damages_df[damages_df['Receipt'] == '']
        
        receipt_data.append(['Items with Receipts:', len(with_receipts), "${:,. 2f}".format(with_receipts['Cost'].sum()), ''])
        receipt_data.append(['Items without Receipts:', len(without_receipts), "${:,. 2f}".format(without_receipts['Cost'].sum()), ''])
        receipt_data.append(['Total Items:', len(damages_df), "${:,.2f}". format(total_cost), ''])
        receipt_data.append(['', '', '', ''])
        
        if len(without_receipts) > 0:
            receipt_data.append(['ITEMS NEEDING RECEIPTS:', '', '', ''])
            receipt_data.append(['Date', 'Title', 'Amount', ''])
            for idx, row in without_receipts.iterrows():
                receipt_data.append([row['Date'], row['Title'], "${:,. 2f}".format(row['Cost']), ''])
        else:
            receipt_data.append(['All items have receipts uploaded', '', '', ''])
        
        receipt_data.append(['', '', '', ''])
        receipt_data.append(['Google Drive Folder:', st.session_state. get("drive_folder_url", "Not configured"), '', ''])
        
        receipt_df = pd.DataFrame(receipt_data)
        receipt_df.to_excel(writer, sheet_name='Receipt Status', index=False, header=False)
    
    return output.getvalue()


def create_legal_summary_document(damages_df, project_name):
    if len(damages_df) == 0:
        return "No damages recorded yet."
    
    total_cost = damages_df['Cost'].sum()
    
    lines = []
    lines.append("=" * 80)
    lines. append("                        DAMAGE CLAIM DOCUMENTATION")
    lines. append("                           LEGAL SUMMARY REPORT")
    lines.append("=" * 80)
    lines.append("")
    lines.append("PROJECT NAME: " + project_name)
    lines.append("REPORT GENERATED: " + datetime.now().strftime('%Y-%m-%d at %H:%M'))
    lines.append("")
    lines. append("-" * 80)
    lines.append("I. EXECUTIVE SUMMARY")
    lines. append("-" * 80)
    lines.append("")
    lines.append("TOTAL DAMAGES CLAIMED: ${:,.2f}". format(total_cost))
    lines. append("")
    lines.append("Key Statistics:")
    lines. append("* Total Number of Damage Items: " + str(len(damages_df)))
    lines.append("* Number of Categories: " + str(damages_df['Category']. nunique()))
    lines.append("* Date Range: " + str(damages_df['Date'].min()) + " to " + str(damages_df['Date'].max()))
    lines.append("* Average Damage Amount: ${:,.2f}".format(damages_df['Cost'].mean()))
    lines.append("* Highest Single Damage: ${:,.2f}".format(damages_df['Cost'].max()))
    lines.append("* Lowest Single Damage: ${:,.2f}".format(damages_df['Cost'].min()))
    lines.append("")
    lines.append("-" * 80)
    lines.append("II. DAMAGE BREAKDOWN BY CATEGORY")
    lines.append("-" * 80)
    
    for category in sorted(damages_df['Category']. unique()):
        cat_data = damages_df[damages_df['Category'] == category]
        cat_total = cat_data['Cost'].sum()
        percentage = (cat_total / total_cost * 100) if total_cost > 0 else 0
        
        lines.append("")
        lines.append(category. upper())
        lines.append("=" * len(category))
        lines.append("Total: ${:,.2f} ({:.1f}% of total damages)".format(cat_total, percentage))
        lines.append("Number of Items: " + str(len(cat_data)))
        lines.append("Average per Item: ${:,.2f}". format(cat_data['Cost'].mean()))
        lines.append("")
        lines.append("Itemized List:")
        
        for idx, row in cat_data. iterrows():
            lines.append("  - " + str(row['Date']) + " - " + row['Title'] + ": ${:,. 2f}".format(row['Cost']))
            if row. get('Description'):
                lines.append("    Description: " + str(row['Description']))
            if row. get('Receipt'):
                lines.append("    Receipt: " + str(row['Receipt']))
        
        lines.append("")
        lines.append("  CATEGORY SUBTOTAL: ${:,.2f}".format(cat_total))
    
    lines.append("")
    lines. append("-" * 80)
    lines.append("III.  CHRONOLOGICAL LISTING")
    lines. append("-" * 80)
    lines.append("")
    
    sorted_by_date = damages_df.sort_values('Date')
    running_total = 0
    for idx, row in sorted_by_date. iterrows():
        running_total = running_total + row['Cost']
        lines.append("{} | {} | ${:,. 2f} | Running: ${:,.2f}".format(
            row['Date'], row['Title'][:40], row['Cost'], running_total))
    
    lines. append("")
    lines.append("-" * 80)
    lines.append("IV. RECEIPT DOCUMENTATION STATUS")
    lines. append("-" * 80)
    lines.append("")
    lines.append("Total Items: " + str(len(damages_df)))
    lines.append("Items with Receipts: " + str(len(damages_df[damages_df['Receipt'] != ''])))
    lines.append("Items Missing Receipts: " + str(len(damages_df[damages_df['Receipt'] == ''])))
    lines.append("")
    lines.append("Receipt Storage Location:")
    lines. append(st.session_state.get('drive_folder_url', 'Not configured'))
    lines. append("")
    lines.append("-" * 80)
    lines.append("V. TOTAL DAMAGES SUMMARY")
    lines. append("-" * 80)
    lines.append("")
    lines.append("+-------------------------------------------+")
    lines.append("|                                           |")
    lines.append("|   GRAND TOTAL OF ALL DAMAGES:             |")
    lines.append("|                                           |")
    lines.append("|        ${:>15,.2f}                  |".format(total_cost))
    lines.append("|                                           |")
    lines.append("+-------------------------------------------+")
    lines.append("")
    lines.append("-" * 80)
    lines.append("                           END OF REPORT")
    lines.append("-" * 80)
    lines.append("Project: " + project_name)
    lines.append("Generated: " + datetime. now().strftime('%Y-%m-%d %H:%M'))
    lines.append("=" * 80)
    
    return "\n".join(lines)


# --- Main App ---
st.title("Damage Invoice Tracker")
st.markdown("### Legal Proceedings Documentation System")

# --- Project Management Section ---
if not st.session_state["project_active"]:
    st.markdown("---")
    st. header("Project Management")
    
    tab1, tab2 = st.tabs(["Create New Project", "Load Existing Project"])
    
    with tab1:
        st. subheader("Start a New Damage Claim Project")
        
        new_project_name = st.text_input(
            "Project Name *",
            placeholder="e.g., Smith vs. Johnson - Vehicle Accident 2024",
            help="Give your project a descriptive name"
        )
        
        if st.button("Create Project", type="primary", use_container_width=True):
            if new_project_name:
                st.session_state["project_name"] = new_project_name
                st.session_state["project_created_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.session_state["project_active"] = True
                st.session_state["damages"] = []
                st.success("Project '" + new_project_name + "' created successfully!")
                st.rerun()
            else:
                st.error("Please enter a project name")
    
    with tab2:
        st.subheader("Load a Previously Saved Project")
        
        uploaded_project = st.file_uploader(
            "Upload Project File (. json)",
            type=["json"],
            help="Select a previously saved project file"
        )
        
        if uploaded_project is not None:
            if st.button("Load Project", type="primary", use_container_width=True):
                json_data = uploaded_project.read(). decode('utf-8')
                if load_project_from_json(json_data):
                    st.success("Project '" + st.session_state['project_name'] + "' loaded!")
                    st. rerun()
        
        st.info("Save your project regularly to keep your work safe.  Upload the . json file here to continue.")

else:
    # --- Active Project Header ---
    total_damages = sum(d['Cost'] for d in st.session_state['damages'])
    
    st.markdown(
        "<div style='background: linear-gradient(90deg, #1f4e79 0%, #2e75b6 100%); "
        "color: white; padding: 1rem; border-radius: 10px; margin-bottom: 1rem;'>"
        "<h3 style='margin: 0; color: white;'>Project: " + st. session_state['project_name'] + "</h3>"
        "<p style='margin: 0. 5rem 0 0 0; font-size: 0.9rem; color: #e0e0e0;'>"
        "Created: " + st.session_state['project_created_date'] + " | "
        "Entries: " + str(len(st.session_state['damages'])) + " | "
        "Total: ${:,.2f}</p></div>".format(total_damages),
        unsafe_allow_html=True
    )
    
    # --- Project Actions ---
    col1, col2, col3 = st.columns(3)
    
    with col1:
        project_json = save_project_to_json()
        safe_name = st.session_state['project_name']. replace(' ', '_'). replace('/', '-')
        st.download_button(
            "Save Project",
            data=project_json,
            file_name=safe_name + "_" + datetime.now(). strftime('%Y%m%d_%H%M') + ".json",
            mime="application/json",
            use_container_width=True
        )
    
    with col2:
        if st.button("Switch Project", use_container_width=True):
            st.session_state["project_active"] = False
            st. rerun()
    
    with col3:
        if st. session_state["delete_mode"]:
            delete_label = "Done Editing"
        else:
            delete_label = "Edit/Delete Entries"
        if st.button(delete_label, use_container_width=True):
            st. session_state["delete_mode"] = not st.session_state["delete_mode"]
            st.rerun()
    
    # --- Google Drive Configuration ---
    with st.expander("Configure Google Drive Folder", expanded=not st.session_state["drive_folder_configured"]):
        drive_url = st.text_input(
            "Google Drive Folder URL:",
            value=st.session_state. get("drive_folder_url", ""),
            help="Example: https://drive. google.com/drive/folders/..."
        )
        
        if st. button("Save Configuration"):
            st.session_state["drive_folder_url"] = drive_url
            st.session_state["drive_folder_configured"] = True
            st.success("Configuration saved!")
            st.rerun()

    if st.session_state["drive_folder_configured"]:
        st.success("Google Drive folder configured")
    
    # --- Delete Mode ---
    if st.session_state["delete_mode"]:
        st. markdown("---")
        st.warning("**Edit Mode Active** - Click the X button next to any entry to delete it")
        
        if st.session_state["damages"]:
            for idx, damage in enumerate(st. session_state["damages"]):
                col1, col2, col3, col4, col5 = st.columns([1, 2, 3, 2, 1])
                
                with col1:
                    st.write("#" + str(idx + 1))
                with col2:
                    st.write(damage['Date'])
                with col3:
                    title_text = damage['Title']
                    if len(title_text) > 35:
                        title_text = title_text[:35] + "..."
                    st.write(title_text)
                with col4:
                    st.write("${:,.2f}".format(damage['Cost']))
                with col5:
                    if st.button("X", key="delete_" + str(idx)):
                        deleted = delete_damage_entry(idx)
                        if deleted:
                            st.success("Deleted: " + deleted['Title'])
                            st.rerun()
        else:
            st. info("No entries to delete")
    
    else:
        # --- Entry Form ---
        st. markdown("---")
        st.subheader("Add New Damage Entry")

        with st.form("damage_form", clear_on_submit=True):
            col1, col2 = st.columns([1, 1])
            
            with col1:
                title = st.text_input("Title *", placeholder="Brief description")
                category = st.selectbox("Category *", CATEGORY_LIST)
                
                subcategory = ""
                custom_subcategory = ""
                if category in SUBCATEGORIES:
                    subcategory = st.selectbox("Subcategory", ["Select... "] + SUBCATEGORIES[category])
                    if subcategory == "Other":
                        custom_subcategory = st.text_input("Specify subcategory:")
                
                custom_category = ""
                if category == "Other":
                    custom_category = st.text_input("Specify category:")
            
            with col2:
                date = st.date_input("Date *", value=datetime.today())
                cost = st.number_input("Cost (USD) *", min_value=0. 0, step=0.01, format="%.2f", value=0.0)
                description = st.text_area("Description", height=70, placeholder="Additional details (optional)")
            
            image_file = st.file_uploader("Upload Receipt/Invoice", type=["png", "jpg", "jpeg", "pdf"])
            submitted = st.form_submit_button("Add Damage Entry", type="primary", use_container_width=True)

        if submitted:
            if not title:
                st.error("Please provide a title")
            elif cost <= 0:
                st.error("Please enter a valid cost amount")
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
                    final_category = category + " - " + subcategory_text
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
                st.success("Damage entry added!")
                
                if image_file and st.session_state["drive_folder_configured"]:
                    st.info("Upload '" + filename + "' to your Google Drive folder")
                    if filename in st.session_state["uploaded_files_data"]:
                        file_data = st.session_state["uploaded_files_data"][filename]['data']
                        st.download_button(
                            label="Download " + filename,
                            data=file_data,
                            file_name=filename,
                            mime="application/octet-stream",
                            key="download_" + filename
                        )
                
                st.rerun()
    
    # --- Display Section ---
    st. markdown("---")
    st.header("Damage Summary")

    if st.session_state["damages"]:
        df = pd.DataFrame(st.session_state["damages"])
        total_cost = df["Cost"].sum()
        
        # Metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("TOTAL DAMAGES", "${:,.2f}".format(total_cost))
        with col2:
            st.metric("Total Items", len(df))
        with col3:
            st.metric("Average", "${:,.2f}".format(df['Cost'].mean()))
        with col4:
            st.metric("Categories", df["Category"].nunique())
        
        # Category breakdown
        st.markdown("### Breakdown by Category")
        
        for category in sorted(df['Category'].unique()):
            cat_data = df[df['Category'] == category]
            cat_total = cat_data['Cost'].sum()
            percentage = (cat_total / total_cost * 100) if total_cost > 0 else 0
            
            with st.expander("**" + category + "** - ${:,.2f} ({:.1f}%)".format(cat_total, percentage)):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write("**Total:** ${:,.2f}".format(cat_total))
                with col2:
                    st.write("**Items:** " + str(len(cat_data)))
                with col3:
                    st. write("**Average:** ${:,.2f}".format(cat_data['Cost']. mean()))
                
                st.markdown("**Items:**")
                for idx, item in cat_data. iterrows():
                    receipt_status = " [Receipt]" if item['Receipt'] else ""
                    st.write("- " + item['Date'] + " - " + item['Title'] + ": **${:,.2f}**".format(item['Cost']) + receipt_status)
        
        # Grand Total
        st.markdown("---")
        st. markdown(
            "<div style='background-color: #d4edda; padding: 1. 5rem; border-radius: 10px; "
            "border: 2px solid #28a745; text-align: center;'>"
            "<h2 style='color: #155724; margin: 0;'>GRAND TOTAL DAMAGES</h2>"
            "<h1 style='color: #155724; margin: 0. 5rem 0; font-size: 3rem;'>${:,.2f}</h1>"
            "<p style='color: #155724; margin: 0;'>{} items across {} categories</p>"
            "</div>".format(total_cost, len(df), df['Category'].nunique()),
            unsafe_allow_html=True
        )
        
        # Export Section
        st.markdown("---")
        st.markdown("### Export for Attorney")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            excel_data = create_comprehensive_excel_report(df, st.session_state["project_name"])
            safe_name = st. session_state['project_name'].replace(' ', '_').replace('/', '-')
            st.download_button(
                "Download Excel Report",
                data=excel_data,
                file_name=safe_name + "_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument. spreadsheetml. sheet",
                use_container_width=True
            )
        
        with col2:
            legal_summary = create_legal_summary_document(df, st.session_state["project_name"])
            st. download_button(
                "Download Legal Summary",
                data=legal_summary,
                file_name=safe_name + "_Legal_Summary.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        with col3:
            csv_data = df.to_csv(index=False). encode('utf-8')
            st. download_button(
                "Download CSV Data",
                data=csv_data,
                file_name=safe_name + "_Data.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        # Data Table
        st. markdown("---")
        st. subheader("All Entries")
        display_df = df.copy()
        display_df['Cost'] = display_df['Cost'].apply(lambda x: "${:,.2f}".format(x))
        display_df['Has Receipt'] = display_df['Receipt'].apply(lambda x: 'Yes' if x else 'No')
        st.dataframe(
            display_df[['Date', 'Category', 'Title', 'Description', 'Cost', 'Has Receipt']],
            use_container_width=True,
            height=400
        )

    else:
        st.info("No damages recorded yet. Add your first entry using the form above.")

# --- Footer ---
st.markdown("---")
st.caption("Damage Invoice Tracker v4.0 | Legal Documentation System")
