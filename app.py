import streamlit as st
import pandas as pd
from datetime import datetime
import os

# --- Configurations ---
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

# --- Session State ---
if "damages" not in st.session_state:
    st.session_state["damages"] = []

# --- App Layout ---
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
        "Image Path": img_path
    }
    st.session_state["damages"].append(entry)
    st.success("Damage added!")

# --- Table of Damages ---
st.header("All Damages")
df = pd.DataFrame(st.session_state["damages"])
if not df.empty:
    df_display = df.copy()
    # Optionally: For images, show as file name for now
    def image_link(path):
        if path and os.path.exists(path):
            return os.path.basename(path)
        return ""
    df_display["Receipt/Image"] = df_display["Image Path"].apply(image_link)
    st.write(df_display.drop("Image Path", axis=1))
    # Excel Export
    excel_file = "damages_export.xlsx"
    df.drop("Image Path", axis=1).to_excel(excel_file, index=False)
    st.download_button("Export Excel file", data=open(excel_file, "rb"), file_name="damages.xlsx")
else:
    st.info("No damages recorded yet.")

# --- Instructions pane ---
with st.expander("Instructions for use"):
    st.markdown("""
    1. Fill in the form to add new damages. You can upload receipts, invoices, or images (optional).
    2. Select the category that best describes the damage. If "Other", you'll be prompted to enter a custom category.
    3. All submitted damages will appear in the table below.
    4. You can export all the entries to an Excel file for sharing or reporting.
    """)
