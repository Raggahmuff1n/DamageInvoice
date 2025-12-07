import streamlit as st
import pandas as pd
from datetime import datetime
import io
import json

st.set_page_config(
    page_title="Damage Invoice Tracker",
    layout="wide",
    initial_sidebar_state="collapsed"
)

st.markdown("""
<style>
    @media (max-width: 768px) {
        .block-container { padding-left: 1rem; padding-right: 1rem; }
        .stButton > button { width: 100%; margin-top: 0.5rem; }
    }
</style>
""", unsafe_allow_html=True)

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
        "Vehicle repair/replacement", "Rental vehicle costs",
        "Damage to home or real estate", "Damage to personal belongings", "Other"
    ],
    "Economic/Financial Loss": [
        "Lost wages or income", "Loss of earning capacity", "Business interruption",
        "Out-of-pocket expenses", "Replacement costs", "Other"
    ],
    "Medical & Health-Related": [
        "Medical bills", "Medication costs", "Rehabilitation or physical therapy",
        "Mental health therapy", "Other"
    ],
    "Emotional & Psychological Damages": [
        "Pain and suffering", "Emotional distress", "Loss of enjoyment of life",
        "Grief and bereavement", "Other"
    ],
    "Special Circumstances": [
        "Pet loss and related costs", "Temporary housing costs",
        "Childcare expenses", "Travel expenses", "Other"
    ],
    "Legal & Administrative Costs": [
        "Attorney fees", "Court filing fees", "Expert witness fees", "Other"
    ],
    "Future Damages": [
        "Projected medical care", "Future therapy", "Long-term disability costs", "Other"
    ]
}

if "damages" not in st. session_state:
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
        return folder_url. rstrip('/') + "/" + filename
    return filename


def save_project_to_json():
    project_data = {
        "project_name": st.session_state["project_name"],
        "project_created_date": st.session_state["project_created_date"],
        "drive_folder_url": st.session_state["drive_folder_url"],
        "damages": st.session_state["damages"],
        "last_saved": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    return json.dumps(project_data, indent=2)


def load_project_from_json(json_data):
    try:
        project_data = json.loads(json_data)
        st.session_state["project_name"] = project_data. get("project_name", "")
        st.session_state["project_created_date"] = project_data.get("project_created_date", "")
        st.session_state["drive_folder_url"] = project_data.get("drive_folder_url", "")
        st. session_state["drive_folder_configured"] = bool(project_data. get("drive_folder_url"))
        st.session_state["damages"] = project_data. get("damages", [])
        st. session_state["project_active"] = True
        return True
    except Exception as e:
        st.error("Error loading project: " + str(e))
        return False


def delete_damage_entry(index):
    if index >= 0 and index < len(st. session_state["damages"]):
        return st.session_state["damages"].pop(index)
    return None


def format_currency(amount):
    return "${:,.2f}".format(amount)


def create_excel_report(damages_df, project_name):
    output = io.BytesIO()
    
    if len(damages_df) == 0:
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pd.DataFrame({'Message': ['No damages recorded']}).to_excel(
                writer, sheet_name='No Data', index=False)
        return output. getvalue()
    
    with pd. ExcelWriter(output, engine='openpyxl') as writer:
        total_cost = damages_df['Cost'].sum()
        
        # Sheet 1: Executive Summary
        summary_rows = [
            ['DAMAGE CLAIM SUMMARY REPORT', '', ''],
            ['Project: ' + project_name, '', ''],
            ['', '', ''],
            ['Report Generated:', datetime.now().strftime("%Y-%m-%d %H:%M"), ''],
            ['', '', ''],
            ['KEY METRICS', '', ''],
            ['Total Damages Claimed:', format_currency(total_cost), ''],
            ['Number of Damage Items:', len(damages_df), ''],
            ['Number of Categories:', damages_df['Category']. nunique(), ''],
            ['Average Damage Amount:', format_currency(damages_df['Cost'].mean()), ''],
            ['Highest Single Damage:', format_currency(damages_df['Cost'].max()), ''],
            ['Lowest Single Damage:', format_currency(damages_df['Cost'].min()), ''],
            ['Date Range:', str(damages_df['Date'].min()) + " to " + str(damages_df['Date'].max()), ''],
            ['', '', ''],
            ['CATEGORY BREAKDOWN', 'Amount', 'Percentage']
        ]
        
        for category in sorted(damages_df['Category'].unique()):
            cat_total = damages_df[damages_df['Category'] == category]['Cost'].sum()
            pct = (cat_total / total_cost * 100) if total_cost > 0 else 0
            summary_rows. append([category, format_currency(cat_total), "{:.1f}%".format(pct)])
        
        summary_rows.append(['', '', ''])
        summary_rows.append(['GRAND TOTAL:', format_currency(total_cost), '100. 0%'])
        
        pd.DataFrame(summary_rows).to_excel(writer, sheet_name='Executive Summary', index=False, header=False)
        
        # Sheet 2: All Damages Categorized
        cat_rows = [
            ['COMPREHENSIVE DAMAGE LIST BY CATEGORY', '', '', '', '', '', ''],
            ['Project: ' + project_name, '', '', '', '', '', ''],
            ['', '', '', '', '', '', '']
        ]
        
        sorted_df = damages_df. sort_values(['Category', 'Date'])
        current_cat = None
        cat_totals = {}
        
        for idx, row in sorted_df.iterrows():
            if current_cat != row['Category']:
                if current_cat is not None:
                    cat_rows. append(['', '', '', '', '', '', ''])
                    cat_rows.append(['', '', '', 'SUBTOTAL - ' + current_cat + ':',
                                    format_currency(cat_totals[current_cat]), '', ''])
                    cat_rows.append(['', '', '', '', '', '', ''])
                
                current_cat = row['Category']
                cat_totals[current_cat] = 0
                cat_rows.append(['=== CATEGORY: ' + current_cat + ' ===', '', '', '', '', '', ''])
                cat_rows.append(['Date', 'Title', 'Description', 'Amount', 'Receipt File', 'Link', 'Notes'])
            
            cat_rows.append([
                row['Date'], row['Title'], row. get('Description', ''),
                format_currency(row['Cost']), row.get('Receipt', ''), row.get('Link', ''), ''
            ])
            cat_totals[current_cat] = cat_totals[current_cat] + row['Cost']
        
        if current_cat:
            cat_rows.append(['', '', '', '', '', '', ''])
            cat_rows.append(['', '', '', 'SUBTOTAL - ' + current_cat + ':',
                            format_currency(cat_totals[current_cat]), '', ''])
        
        cat_rows.append(['', '', '', '', '', '', ''])
        cat_rows.append(['', '', '', 'GRAND TOTAL:', format_currency(total_cost), '', ''])
        
        pd.DataFrame(cat_rows).to_excel(writer, sheet_name='All Damages Categorized', index=False, header=False)
        
        # Sheet 3: Category Analysis
        analysis_rows = [
            ['DETAILED CATEGORY ANALYSIS', '', '', '', ''],
            ['Project: ' + project_name, '', '', '', ''],
            ['', '', '', '', '']
        ]
        
        for category in sorted(damages_df['Category'].unique()):
            cat_data = damages_df[damages_df['Category'] == category]
            cat_total = cat_data['Cost'].sum()
            pct = (cat_total / total_cost * 100) if total_cost > 0 else 0
            
            analysis_rows. append(['=== ' + category + ' ===', '', '', '', ''])
            analysis_rows.append(['Number of Items:', len(cat_data), '', '', ''])
            analysis_rows.append(['Total Amount:', format_currency(cat_total), '', '', ''])
            analysis_rows.append(['Percentage of Total:', "{:.1f}%".format(pct), '', '', ''])
            analysis_rows.append(['Average per Item:', format_currency(cat_data['Cost'].mean()), '', '', ''])
            analysis_rows.append(['Highest Item:', format_currency(cat_data['Cost'].max()), '', '', ''])
            analysis_rows.append(['Lowest Item:', format_currency(cat_data['Cost']. min()), '', '', ''])
            analysis_rows.append(['', '', '', '', ''])
        
        pd.DataFrame(analysis_rows).to_excel(writer, sheet_name='Category Analysis', index=False, header=False)
        
        # Sheet 4: Chronological View
        chrono_rows = [
            ['CHRONOLOGICAL DAMAGE LIST', '', '', '', ''],
            ['Project: ' + project_name, '', '', '', ''],
            ['', '', '', '', ''],
            ['Date', 'Category', 'Title', 'Amount', 'Running Total']
        ]
        
        sorted_chrono = damages_df.sort_values('Date')
        running = 0
        for idx, row in sorted_chrono.iterrows():
            running = running + row['Cost']
            chrono_rows.append([row['Date'], row['Category'], row['Title'],
                               format_currency(row['Cost']), format_currency(running)])
        
        chrono_rows.append(['', '', '', '', ''])
        chrono_rows.append(['', '', 'FINAL TOTAL:', format_currency(total_cost), ''])
        
        pd.DataFrame(chrono_rows).to_excel(writer, sheet_name='Chronological View', index=False, header=False)
        
        # Sheet 5: Receipt Status
        receipt_rows = [
            ['RECEIPT DOCUMENTATION STATUS', '', '', ''],
            ['Project: ' + project_name, '', '', ''],
            ['', '', '', ''],
            ['Status', 'Count', 'Amount', '']
        ]
        
        with_rec = damages_df[damages_df['Receipt'] != '']
        without_rec = damages_df[damages_df['Receipt'] == '']
        
        receipt_rows.append(['With Receipts:', len(with_rec), format_currency(with_rec['Cost'].sum()), ''])
        receipt_rows.append(['Without Receipts:', len(without_rec), format_currency(without_rec['Cost']. sum()), ''])
        receipt_rows.append(['Total:', len(damages_df), format_currency(total_cost), ''])
        receipt_rows.append(['', '', '', ''])
        
        if len(without_rec) > 0:
            receipt_rows.append(['ITEMS NEEDING RECEIPTS:', '', '', ''])
            receipt_rows.append(['Date', 'Title', 'Amount', ''])
            for idx, row in without_rec.iterrows():
                receipt_rows.append([row['Date'], row['Title'], format_currency(row['Cost']), ''])
        else:
            receipt_rows.append(['All items have receipts', '', '', ''])
        
        receipt_rows.append(['', '', '', ''])
        receipt_rows.append(['Google Drive:', st.session_state. get("drive_folder_url", "Not configured"), '', ''])
        
        pd.DataFrame(receipt_rows).to_excel(writer, sheet_name='Receipt Status', index=False, header=False)
    
    return output.getvalue()


def create_legal_summary(damages_df, project_name):
    if len(damages_df) == 0:
        return "No damages recorded."
    
    total = damages_df['Cost'].sum()
    lines = []
    
    lines.append("=" * 80)
    lines. append("DAMAGE CLAIM DOCUMENTATION - LEGAL SUMMARY REPORT")
    lines.append("=" * 80)
    lines.append("")
    lines.append("PROJECT: " + project_name)
    lines.append("GENERATED: " + datetime.now().strftime('%Y-%m-%d %H:%M'))
    lines.append("")
    lines. append("-" * 80)
    lines.append("I. EXECUTIVE SUMMARY")
    lines.append("-" * 80)
    lines.append("")
    lines.append("TOTAL DAMAGES CLAIMED: " + format_currency(total))
    lines.append("")
    lines.append("Key Statistics:")
    lines. append("  Total Items: " + str(len(damages_df)))
    lines. append("  Categories: " + str(damages_df['Category']. nunique()))
    lines.append("  Date Range: " + str(damages_df['Date'].min()) + " to " + str(damages_df['Date'].max()))
    lines.append("  Average: " + format_currency(damages_df['Cost'].mean()))
    lines.append("  Highest: " + format_currency(damages_df['Cost'].max()))
    lines.append("  Lowest: " + format_currency(damages_df['Cost']. min()))
    lines.append("")
    lines.append("-" * 80)
    lines.append("II. BREAKDOWN BY CATEGORY")
    lines.append("-" * 80)
    
    for category in sorted(damages_df['Category'].unique()):
        cat_data = damages_df[damages_df['Category'] == category]
        cat_total = cat_data['Cost'].sum()
        pct = (cat_total / total * 100) if total > 0 else 0
        
        lines.append("")
        lines.append(category. upper())
        lines.append("=" * len(category))
        lines.append("Total: " + format_currency(cat_total) + " ({:.1f}%)".format(pct))
        lines. append("Items: " + str(len(cat_data)))
        lines. append("Average: " + format_currency(cat_data['Cost'].mean()))
        lines.append("")
        lines.append("Itemized:")
        
        for idx, row in cat_data. iterrows():
            lines.append("  - " + str(row['Date']) + " | " + row['Title'] + " | " + format_currency(row['Cost']))
        
        lines.append("")
        lines.append("SUBTOTAL: " + format_currency(cat_total))
    
    lines.append("")
    lines. append("-" * 80)
    lines.append("III.  CHRONOLOGICAL LIST")
    lines. append("-" * 80)
    lines.append("")
    
    running = 0
    for idx, row in damages_df.sort_values('Date'). iterrows():
        running = running + row['Cost']
        lines.append(str(row['Date']) + " | " + row['Title'][:30] + " | " + 
                    format_currency(row['Cost']) + " | Running: " + format_currency(running))
    
    lines.append("")
    lines.append("-" * 80)
    lines.append("IV. RECEIPT STATUS")
    lines.append("-" * 80)
    lines.append("")
    lines.append("Total Items: " + str(len(damages_df)))
    lines.append("With Receipts: " + str(len(damages_df[damages_df['Receipt'] != ''])))
    lines.append("Missing Receipts: " + str(len(damages_df[damages_df['Receipt'] == ''])))
    lines.append("Receipt Location: " + st. session_state.get('drive_folder_url', 'Not configured'))
    lines. append("")
    lines.append("-" * 80)
    lines.append("V. GRAND TOTAL")
    lines.append("-" * 80)
    lines.append("")
    lines.append("+------------------------------------------+")
    lines.append("|                                          |")
    lines.append("|   TOTAL DAMAGES: " + format_currency(total). rjust(20) + "   |")
    lines.append("|                                          |")
    lines.append("+------------------------------------------+")
    lines.append("")
    lines.append("=" * 80)
    lines.append("END OF REPORT")
    lines.append("=" * 80)
    
    return "\n".join(lines)


# Main App
st.title("Damage Invoice Tracker")
st. markdown("### Legal Proceedings Documentation System")

if not st.session_state["project_active"]:
    st.markdown("---")
    st. header("Project Management")
    
    tab1, tab2 = st.tabs(["Create New Project", "Load Existing Project"])
    
    with tab1:
        st. subheader("Start a New Project")
        new_name = st.text_input("Project Name *", placeholder="e.g., Smith vs. Johnson 2024")
        
        if st.button("Create Project", type="primary", use_container_width=True):
            if new_name:
                st.session_state["project_name"] = new_name
                st.session_state["project_created_date"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                st.session_state["project_active"] = True
                st.session_state["damages"] = []
                st.success("Project created!")
                st.rerun()
            else:
                st.error("Please enter a project name")
    
    with tab2:
        st.subheader("Load Saved Project")
        uploaded = st.file_uploader("Upload Project File (. json)", type=["json"])
        
        if uploaded is not None:
            if st.button("Load Project", type="primary", use_container_width=True):
                if load_project_from_json(uploaded. read(). decode('utf-8')):
                    st.success("Project loaded!")
                    st. rerun()

else:
    # Project Header
    total_dmg = sum(d['Cost'] for d in st.session_state['damages'])
    st.markdown(
        "<div style='background:linear-gradient(90deg,#1f4e79,#2e75b6);color:white;"
        "padding:1rem;border-radius:10px;margin-bottom:1rem;'>"
        "<h3 style='margin:0;color:white;'>Project: " + st. session_state['project_name'] + "</h3>"
        "<p style='margin:0. 5rem 0 0 0;color:#e0e0e0;'>Entries: " + str(len(st.session_state['damages'])) +
        " | Total: " + format_currency(total_dmg) + "</p></div>",
        unsafe_allow_html=True
    )
    
    # Action Buttons
    col1, col2, col3 = st.columns(3)
    
    with col1:
        safe_name = st.session_state['project_name']. replace(' ', '_'). replace('/', '-')
        st.download_button(
            "Save Project", data=save_project_to_json(),
            file_name=safe_name + "_" + datetime.now(). strftime('%Y%m%d') + ".json",
            mime="application/json", use_container_width=True
        )
    
    with col2:
        if st.button("Switch Project", use_container_width=True):
            st.session_state["project_active"] = False
            st.rerun()
    
    with col3:
        btn_label = "Done Editing" if st.session_state["delete_mode"] else "Edit/Delete"
        if st. button(btn_label, use_container_width=True):
            st.session_state["delete_mode"] = not st. session_state["delete_mode"]
            st.rerun()
    
    # Google Drive Config
    with st.expander("Configure Google Drive", expanded=not st.session_state["drive_folder_configured"]):
        drive_url = st.text_input("Google Drive Folder URL:", value=st.session_state.get("drive_folder_url", ""))
        if st.button("Save Config"):
            st.session_state["drive_folder_url"] = drive_url
            st.session_state["drive_folder_configured"] = True
            st. success("Saved!")
            st.rerun()
    
    # Delete Mode
    if st.session_state["delete_mode"]:
        st.markdown("---")
        st.warning("**Edit Mode** - Click X to delete entries")
        
        if st.session_state["damages"]:
            for idx, dmg in enumerate(st.session_state["damages"]):
                c1, c2, c3, c4, c5 = st.columns([1, 2, 3, 2, 1])
                c1.write("#" + str(idx + 1))
                c2. write(dmg['Date'])
                c3.write(dmg['Title'][:35])
                c4.write(format_currency(dmg['Cost']))
                if c5.button("X", key="del_" + str(idx)):
                    delete_damage_entry(idx)
                    st.rerun()
        else:
            st. info("No entries")
    
    else:
        # Entry Form
        st.markdown("---")
        st.subheader("Add New Damage Entry")
        
        with st.form("damage_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            
            with c1:
                title = st.text_input("Title *")
                category = st.selectbox("Category *", CATEGORY_LIST)
                
                subcategory = ""
                if category in SUBCATEGORIES:
                    subcategory = st. selectbox("Subcategory", ["Select... "] + SUBCATEGORIES[category])
                
                custom_cat = ""
                if category == "Other" or subcategory == "Other":
                    custom_cat = st. text_input("Specify:")
            
            with c2:
                date_val = st.date_input("Date *", value=datetime.today())
                cost_val = st. number_input("Cost (USD) *", min_value=0.0, step=0.01, format="%.2f", value=0.0)
                desc = st.text_area("Description", height=70)
            
            img_file = st. file_uploader("Upload Receipt", type=["png", "jpg", "jpeg", "pdf"])
            submitted = st.form_submit_button("Add Entry", type="primary", use_container_width=True)
        
        if submitted:
            if not title:
                st.error("Please provide a title")
            elif cost_val <= 0:
                st. error("Please enter a valid cost")
            else:
                fname = ""
                flink = ""
                
                if img_file:
                    fname = save_uploaded_file(img_file)
                    if st.session_state["drive_folder_configured"]:
                        flink = generate_drive_link(st.session_state["drive_folder_url"], fname)
                
                if category == "Other":
                    final_cat = custom_cat if custom_cat else "Other"
                elif subcategory and subcategory not in ["Select...", "Other", ""]:
                    final_cat = category + " - " + subcategory
                elif subcategory == "Other" and custom_cat:
                    final_cat = category + " - " + custom_cat
                else:
                    final_cat = category
                
                st.session_state["damages"]. append({
                    "Title": title,
                    "Description": desc,
                    "Date": date_val. strftime("%Y-%m-%d"),
                    "Category": final_cat,
                    "Cost": float(cost_val),
                    "Receipt": fname,
                    "Link": flink
                })
                st.success("Entry added!")
                st. rerun()
    
    # Summary
    st.markdown("---")
    st.header("Damage Summary")
    
    if st.session_state["damages"]:
        df = pd.DataFrame(st.session_state["damages"])
        total_cost = df["Cost"].sum()
        
        # Metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("TOTAL", format_currency(total_cost))
        m2.metric("Items", len(df))
        m3.metric("Average", format_currency(df['Cost'].mean()))
        m4.metric("Categories", df["Category"].nunique())
        
        # Category Breakdown
        st.markdown("### By Category")
        for cat in sorted(df['Category'].unique()):
            cat_df = df[df['Category'] == cat]
            cat_sum = cat_df['Cost'].sum()
            pct = (cat_sum / total_cost * 100) if total_cost > 0 else 0
            
            with st.expander(cat + " - " + format_currency(cat_sum) + " ({:.1f}%)".format(pct)):
                st.write("**Total:** " + format_currency(cat_sum))
                st. write("**Items:** " + str(len(cat_df)))
                for idx, item in cat_df. iterrows():
                    rec = " [Receipt]" if item['Receipt'] else ""
                    st.write("- " + item['Date'] + " - " + item['Title'] + ": " + format_currency(item['Cost']) + rec)
        
        # Grand Total
        st. markdown("---")
        st. markdown(
            "<div style='background:#d4edda;padding:1. 5rem;border-radius:10px;border:2px solid #28a745;text-align:center;'>"
            "<h2 style='color:#155724;margin:0;'>GRAND TOTAL</h2>"
            "<h1 style='color:#155724;font-size:3rem;margin:0. 5rem 0;'>" + format_currency(total_cost) + "</h1>"
            "<p style='color:#155724;'>" + str(len(df)) + " items in " + str(df['Category']. nunique()) + " categories</p></div>",
            unsafe_allow_html=True
        )
        
        # Export
        st.markdown("---")
        st. markdown("### Export for Attorney")
        e1, e2, e3 = st.columns(3)
        
        safe_name = st. session_state['project_name'].replace(' ', '_').replace('/', '-')
        
        with e1:
            st. download_button(
                "Excel Report", data=create_excel_report(df, st.session_state["project_name"]),
                file_name=safe_name + "_Report.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with e2:
            st.download_button(
                "Legal Summary", data=create_legal_summary(df, st.session_state["project_name"]),
                file_name=safe_name + "_Summary.txt", mime="text/plain", use_container_width=True
            )
        
        with e3:
            st.download_button(
                "CSV Data", data=df.to_csv(index=False). encode('utf-8'),
                file_name=safe_name + "_Data.csv", mime="text/csv", use_container_width=True
            )
        
        # Table View
        st. markdown("---")
        st.subheader("All Entries")
        show_df = df.copy()
        show_df['Cost'] = show_df['Cost'].apply(format_currency)
        show_df['Receipt'] = show_df['Receipt'].apply(lambda x: 'Yes' if x else 'No')
        st.dataframe(show_df[['Date', 'Category', 'Title', 'Cost', 'Receipt']], use_container_width=True)
    
    else:
        st.info("No damages recorded.  Add your first entry above.")

st.markdown("---")
st.caption("Damage Invoice Tracker v4.0")
