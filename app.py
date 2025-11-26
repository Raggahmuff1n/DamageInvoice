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

# --- Session defaults for form clearing & save config ---
if "damages" not in st.session_state:
    st.session_state["damages"] = []

# keys for form fields so we can reset them after submit
form_keys = {
    "title": "title_input",
    "description": "description_input",
    "date": "date_input",
    "category": "category_input",
    "custom_category": "custom_category_input",
    "cost": "cost_input",
    "image": "image_input"
}
# initialize keys if missing
for k in form_keys.values():
    if k not in st.session_state:
        st.session_state[k] = "" if "date" not in k else datetime.today()

# Save location config stored per session
# st.session_state["save_config"] = {"type": "local" | "external", "base_url": "...", "save_path": "..."}
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
        st.info("You should provide a base URL that points to the location where files will be accessible (e.g. a shared Google Drive 'direct link' folder or other public/shared URL). For links in the spreadsheet to be valid, you must ensure the uploaded files are reachable at the provided base URL + filename.")
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
                # create save_path if writable
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

# --- Form ---
with st.form("damage_form"):
    st.subheader("Enter a New Damage")
    title = st.text_input("Title*", key=form_keys["title"])
    description = st.text_area("Description (optional)", key=form_keys["description"])
    date = st.date_input("Date*", key=form_keys["date"], value=datetime.today())
    category = st.selectbox("Category*", CATEGORY_LIST, key=form_keys["category"])
    custom_category = ""
    if category == "Other":
        custom_category = st.text_input("Please specify category:", key=form_keys["custom_category"])
    cost = st.number_input("Cost (USD)*", min_value=0.0, step=0.01, key=form_keys["cost"])
    image_file = st.file_uploader("Upload Receipt/Image (optional)", type=["png", "jpg", "jpeg", "pdf"], key=form_keys["image"])
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
            except Exception as e:
                # fallback to default uploads folder
                saved_to = os.path.join(DEFAULT_UPLOADS, filename)
                with open(saved_to, "wb") as f:
                    f.write(image_file.getbuffer())

            # Build image URL according to config
            if save_cfg["type"] == "external" and save_cfg.get("base_url"):
                # create URL-encoded filename and append
                image_url = save_cfg["base_url"].rstrip("/") + "/" + urllib.parse.quote(filename)
            else:
                # Local save: there may not be a public URL; we'll put a file path which can be used for download from the app
                # Use a relative path so that you can manually download from the server or use the app's download button
                image_url = saved_to

        entry = {
            "Title": title,
            "Description": description,
            "Date": date.strftime("%Y-%m-%d"),
            "Category": custom_category if category == "Other" else category,
            "Cost": float(cost or 0.0),
            "Image Filename": filename,
            "Image URL": image_url
        }
        st.session_state["damages"].append(entry)
        st.success("Damage added!")

        # Clear form inputs by resetting session state keys, then rerun to display cleared form
        st.session_state[form_keys["title"]] = ""
        st.session_state[form_keys["description"]] = ""
        st.session_state[form_keys["date"]] = datetime.today()
        st.session_state[form_keys["category"]] = CATEGORY_LIST[0]
        st.session_state[form_keys["custom_category"]] = ""
        st.session_state[form_keys["cost"]] = 0.0
        st.session_state[form_keys["image"]] = None
        st.experimental_rerun()

# --- Display table, totals, category summary, export ---
st.header("All Damages")
df = pd.DataFrame(st.session_state["damages"])
if not df.empty:
    # make a display copy
    display_df = df.copy()
    # for in-app convenience show clickable links under the table (DataFrame display may not make links clickable)
    st.dataframe(display_df[["Title", "Description", "Date", "Category", "Cost", "Image Filename", "Image URL"]])

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
    st.dataframe(category_summary)

    # Provide clickable links list for easy access (in-app)
    st.subheader("Uploaded file links")
    for idx, row in df.iterrows():
        if row.get("Image URL"):
            url = row["Image URL"]
            name = row.get("Image Filename") or url
            # if URL looks like a path on server, provide a download button instead
            if str(url).startswith("http"):
                st.markdown(f"- [{name}]({url})")
            else:
                st.markdown(f"- {name} — saved at: `{url}`")
                # download button for the local file
                try:
                    with open(url, "rb") as f:
                        st.download_button(f"Download {name}", data=f, file_name=name, key=f"dl_{idx}")
                except Exception:
                    pass

    # Excel export with two sheets (Damage Entries + Category Summary)
    excel_file = "damages_export.xlsx"
    try:
        with pd.ExcelWriter(excel_file, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Damage Entries", index=False)
            category_summary.to_excel(writer, sheet_name="Category Summary", index=False)
        with open(excel_file, "rb") as ef:
            st.download_button("Export Excel file (.xlsx)", data=ef, file_name="damages.xlsx")
    except Exception as e:
        st.error(f"Error creating Excel export: {e}")
        # Fallback CSV
        csv_file = "damages_export.csv"
        df.to_csv(csv_file, index=False)
        with open(csv_file, "rb") as cf:
            st.download_button("Export CSV file", data=cf, file_name="damages.csv")
else:
    st.info("No damages recorded yet.")

with st.expander("Instructions for use"):
    st.markdown("""
    - Configure the save location once per session using the 'Configure...' area.
      - For External: provide a base URL where files will be accessible (e.g. your shared folder link root). The app will attempt to save the file on the server and will create an Image URL as `base_url/filename`. You must ensure the shared folder is synced or mounted so the URL is valid.
      - For Local: files are saved into the server's uploads folder; the Image URL will be a file path on the server (not a public URL). Use the download button next to each saved file to retrieve it when available.
    - Fill the form and press "Add Damage". After submit the form will be cleared and ready for the next entry.
    - Use the export button to download an Excel file that contains the 'Image URL' column. If you provided an external base URL, the links will be clickable in Excel.
    - Note: If you deploy to Streamlit Community Cloud, writing to an external hosted drive (like Google Drive) requires that the drive be mounted or you implement an API-based upload (not included here).
    """)
