import streamlit as st
import pandas as pd
from datetime import datetime
import os

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
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

if "damages" not in st.session_state:
    st.session_state["damages"] = []

st.set_page_config(page_title="Damage Invoice Tracker", layout="wide")
st.title("Damage Invoice Tracker")

with st.form("damage_form"):
    st.subheader("Enter a New Damage")
    title = st.text_input("Title*", "")
    description = st.text_area("Description (optional)", "")
    date = st.date_input("Date*", value=datetime.today())
    category = st.selectbox("Category*", CATEGORY_LIST)
    custom_category = ""
    if category == "Other":
        custom_category = st.text_input("Please specify category:")
    cost = st.number_input("Cost (USD)*", min_value=0.0, step=0.01)
    image_file = st.file_uploader("Upload Receipt/Image (optional)", type=["png", "jpg", "jpeg", "pdf"])
    submitted = st.form_submit_button("Add Damage")

if submitted:
    img_path = ""
    if image_file is not None:
        img_path = os.path.join(UPLOAD_FOLDER, image_file.name)
        with open(img_path, "wb") as f:
            f.write(image_file.getbuffer())

    entry = {
        "Title": title,
        "Description": description,
        "Date": date.strftime("%Y-%m-%d"),
        "Category": custom_category if category == "Other" else category,
        "Cost": cost,
        "Receipt/Image": os.path.basename(img_path) if img_path else ""
    }
    st.session_state["damages"].append(entry)
    st.success("Damage added!")

st.header("All Damages")
df = pd.DataFrame(st.session_state["damages"])
if not df.empty:
    st.write(df)
    total_cost = df["Cost"].sum()
    st.markdown(f"### **Grand Total Cost: ${total_cost:,.2f}**")

    # Category summary
    category_summary = (
        df.groupby("Category")["Cost"]
        .agg(["count", "sum"])
        .rename(columns={"count": "Number of Entries", "sum": "Total Cost"})
        .reset_index()
    )

    st.subheader("Total Cost per Category")
    st.write(category_summary)

    # Excel export with two sheets
    excel_file = "damages_export.xlsx"
    with pd.ExcelWriter(excel_file) as writer:
        df.to_excel(writer, sheet_name="Damage Entries", index=False)
        category_summary.to_excel(writer, sheet_name="Category Summary", index=False)
    st.download_button("Export Excel file", data=open(excel_file, "rb"), file_name="damages.xlsx")
else:
    st.info("No damages recorded yet.")

with st.expander("Instructions for use"):
    st.markdown("""
    - Fill in the form to add damages. All fields are required except description and file upload.
    - View all entered damages and grand totals.
    - Export the Excel file, which includes ALL details plus a category summary.
    """)
