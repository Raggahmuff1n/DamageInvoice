import streamlit as st
import pandas as pd
from datetime import datetime
import os
from pathlib import Path
import urllib.parse

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
DEFAULT_UPLOADS = "uploads"
os.makedirs(DEFAULT_UPLOADS, exist_ok=True)

# --- Session defaults for data storage ---
if "damages" not in st.session_state:
    st.session_state["damages"] = []

# --- Properly initialize form keys with correct types BEFORE creating widgets ---
if "title_input" not in st.session_state:
    st.session_state["title_input"] = ""
if "description_input" not in st.session_state:
    st.session_state["description_input"] = ""
if "date_input" not in st.session_state:
    st.session_state["date_input"] = datetime.today()
if "category_input" not in st.session_state:
    st.session_state["category_input"] = CATEGORY_LIST[0]
if "custom_category_input" not in st.session_state:
    st.session_state["custom_category_input"] = ""
if "cost_input" not in st.session_state:
    st.session_state["cost_input"] = 0.0
if "image_input" not in st.session_state:
    st.session_state["image_input"] = None

# Save location config stored per session
if "save_config" not in st.session_state:
    st.session_state["save_config"] = None
if "save_config_set" not in st.session_state:
    st.session_state["save_config_set"] = False

st.set_page_config(page_title="Damage Invoice Tracker", layout="wide")
st.title("Damage Invoice Tracker")

# --- Save location UI (asked once per session) ---
with st.expander("Configure where uploaded receipts will be saved (asked once per session)", expanded=not st.session_state["save_config_set"]):
    st.write("Choose how you want uploaded files to be saved and how links are generated in the export.")
    save_type = st.selectbox("Save location type", ["Local (save to server uploads folder)", "External (provide base URL for shared drive)"])
    if save_type.startswith("Local"):
        st.info("Files will be saved into the app's uploads folder on the server.")
        local_save_path = st.text_input("Local save folder path (optional, leave blank to use './uploads')", value="")
    else:
        st.info("Provide a base URL where files will be accessible (e.g. a shared folder public URL). The app will create links as base_url/filename.")
        external_base_url = st.text_input("External base URL (e.g. https://drive.example.com/shared/myfolder) - no trailing slash preferred", value="")
        external_save_path = st.text_input("Optional server-side path where you want actual files written (if the server has the drive mounted). Leave blank if not applicable.", value="")
    set_btn = st.button("Set save location")
    if set_btn:
        if save_type.startswith("Local"):
            save_path = local_save_path.strip() or DEFAULT_UPLOADS
            os.makedirs(save_path, exist_ok=True)
            st.session_state["save_config"] = {"type": "local", "base_url": "", "save_path": save_path}
            st.session_state["save_config_set"] = True
            st.success(f"Save location set to local folder: {save_path}")
        else:
            base = external_base_url.strip()
            if not base:
                st.error("Please provide an external base URL.")
            else:
                save_path = external_save_path.strip() or DEFAULT_UPLOADS
                try:
                    os.makedirs(save_path, exist_ok=True)
                except Exception:
                    pass
                st.session_state["save_config"] = {"type": "external", "base_url": base.rstrip("/"), "save_path": save_path}
                st.session_state["save_config_set"] = True
                st.success(f"External base URL set. Files will be saved to: {save_path} (if writable). Links will be built from: {base.rstrip('/')}/<filename>")

if st.session_state["save_config_set"]:
    cfg = st.session_state["save_config"]
    st.info(f"Current save config: {cfg}")

# --- Form: all widgets reference session-state keys (no default 'value' arg) ---
with st.form("damage_form"):
    st.subheader("Enter a New Damage")
    title = st.text_input("Title*", key="title_input")
    description = st.text_area("Description (optional)", key="description_input")
    date = st.date_input("Date*", key="date_input")
    category = st.selectbox("Category*", CATEGORY_LIST, key="category_input")
    custom_category = ""
    if category == "Other":
        custom_category = st.text_input("Please specify category:", key="custom_category_input")
    cost = st.number_input("Cost (USD)*", min_value=0.0, step=0.01, format="%.2f", key="cost_input")
    image_file = st.file_uploader("Upload Receipt/Image (optional)", type=["png", "jpg", "jpeg", "pdf"], key="image_input")
    submitted = st.form_submit_button("Add Damage")

# --- Handle submit ---
if submitted:
    if not st.session_state["save_config_set"]:
        st.warning("Please set a save location in the 'Configure...' section before adding entries.")
    else:
        save_cfg = st.session_state["save_config"]
        filename = ""
        image_url = ""
        save_path = save_cfg.get("save_path", DEFAULT_UPLOADS) or DEFAULT_UPLOADS

        if image_file is not None:
            filename = f"{int(datetime.now().timestamp())}_{Path(image_file.name).name}"
            # attempt to save to configured save_path first (if writable)
            local_target = os.path.join(save_path, filename)
            try:
                with open(local_target, "wb") as f:
                    f.write(image_file.getbuffer())
                saved_to = local_target
            except Exception:
                # fallback to default uploads folder
                saved_to = os.path.join(DEFAULT_UPLOADS, filename)
                with open(saved_to, "wb") as f:
                    f.write(image_file.getbuffer())

            # Build image URL according to config
            if save_cfg["type"] == "external" and save_cfg.get("base_url"):
                image_url = save_cfg["base_url"].rstrip("/") + "/" + urllib.parse.quote(filename)
            else:
                image_url = saved_to

        entry = {
            "Title": st.session_state["title_input"],
            "Description": st.session_state["description_input"],
            "Date": st.session_state["date_input"].strftime("%Y-%m-%d") if isinstance(st.session_state["date_input"], datetime) else str(st.session_state["date_input"]),
            "Category": st.session_state["custom_category_input"] if st.session_state["category_input"] == "Other" else st.session_state["category_input"],
            "Cost": float(st.session_state["cost_input"] or 0.0),
            "Image Filename": filename,
            "Image URL": image_url
        }
        st.session_state["damages"].append(entry)
        st.success("Damage added!")

        # Clear form inputs by resetting session state keys to appropriate types, then rerun
        st.session_state["title_input"] = ""
        st.session_state["description_input"] = ""
        st.session_state["date_input"] = datetime.today()
        st.session_state["category_input"] = CATEGORY_LIST[0]
        st.session_state["custom_category_input"] = ""
        st.session_state["cost_input"] = 0.0
        st.session_state["image_input"] = None
        st.experimental_rerun()

# --- Display table, totals, category summary, export ---
st.header("All Damages")
df = pd.DataFrame(st.session_state["damages"])
if not df.empty:
    display_df = df.copy()
    st.dataframe(display_df[["Title", "Description", "Date", "Category", "Cost", "Image Filename", "Image URL"]])

    total_cost = df["Cost"].sum()
    st.markdown(f"### **Grand Total Cost: ${total_cost:,.2f}**")

    category_summary = (
        df.groupby("Category")["Cost"]
        .agg(["count", "sum"])
        .rename(columns={"count": "Number of Entries", "sum": "Total Cost"})
        .reset_index()
    )
    st.subheader("Total Cost per Category")
    st.dataframe(category_summary)

    st.subheader("Uploaded file links")
    for idx, row in df.iterrows():
        if row.get("Image URL"):
            url = row["Image URL"]
            name = row.get("Image Filename") or url
            if str(url).startswith("http"):
                st.markdown(f"- [{name}]({url})")
            else:
                st.markdown(f"- {name} — saved at: `{url}`")
                try:
                    with open(url, "rb") as f:
                        st.download_button(f"Download {name}", data=f, file_name=name, key=f"dl_{idx}")
                except Exception:
                    pass

    excel_file = "damages_export.xlsx"
    try:
        with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Damage Entries", index=False)
            category_summary.to_excel(writer, sheet_name="Category Summary", index=False)
        with open(excel_file, "rb") as ef:
            st.download_button("Export Excel file (.xlsx)", data=ef, file_name="damages.xlsx")
    except Exception as e:
        st.error(f"Error creating Excel export: {e}")
        csv_file = "damages_export.csv"
        df.to_csv(csv_file, index=False)
        with open(csv_file, "rb") as cf:
            st.download_button("Export CSV file", data=cf, file_name="damages.csv")
else:
    st.info("No damages recorded yet.")

with st.expander("Instructions for use"):
    st.markdown("""
    - Configure the save location once per session using the 'Configure...' area.
    - Fill the form and press "Add Damage". After submit the form will be cleared and ready for the next entry.
    - Use the export button to download an Excel file that contains the 'Image URL' column.
    - Note: Streamlit Cloud's filesystem is ephemeral; for persistent storage use an external drive mount or API-based upload (Google Drive API, etc.).
    """)
