import streamlit as st
import pandas as pd
import io
import requests
import json
from datetime import date

st.set_page_config(page_title="Reservation Manager", layout="wide")
st.title("🏡 Multi-Property Reservation Manager")

# n8n webhook configuration
N8N_WEBHOOK_URL = st.sidebar.text_input(
    "n8n Webhook URL", 
    placeholder="https://your-n8n-instance.com/webhook/your-webhook-id",
    help="Enter your n8n webhook URL"
)

# Session state init
if 'property_count' not in st.session_state:
    st.session_state.property_count = 1

if st.button("➕ Add Another Property"):
    st.session_state.property_count += 1

def reservation_form(index):
    with st.expander(f"📋 Reservation #{index + 1}", expanded=True):
        st.subheader("👤 Client Info")
        client_name = st.text_input("Client Name", key=f"client_name_{index}")
        reservation_date = st.date_input("Reservation Date", key=f"date_{index}", value=date.today())

        st.subheader("🏘️ Property Info")
        prop_address = st.text_input("Property Address", key=f"address_{index}")
        property_setting = st.selectbox(
            "Property Setting",
            ["Urban", "Suburban", "Rural", "Beachfront", "Mountain", "Resort", "Custom"],
            key=f"setting_{index}"
        )
        custom_setting = ""
        if property_setting == "Custom":
            custom_setting = st.text_input("Enter Custom Setting", key=f"custom_setting_{index}")

        st.subheader("🗓️ Reservation Details")
        villa_name = st.text_input("Villa Name/Number", key=f"villa_{index}")
        status = st.radio("Reservation Status", ["RESERVED!", "CANCELED!", "UPDATE!"], key=f"status_{index}")

        clean_type = st.multiselect(
            "Type of Clean Required",
            ["Check-out/Check-in (CO/CI)", "Stay-over (SO)", "Fresh-up (FU)", "Deep Cleaning (DC)", "Construction Cleaning (COC)"],
            key=f"clean_type_{index}"
        )

        pax = st.number_input("PAX (No. of Guests)", min_value=0, key=f"pax_{index}")
        start_time = st.time_input("Start Time", key=f"start_{index}")
        st.markdown("**Check-OUT Time:** 12:00 PM")
        st.markdown("**Check-IN Time:** 2:00 PM")

        st.subheader("🧺 Laundry & Linen")
        laundry = st.radio("Laundry Services Required?", ["Yes", "No"], key=f"laundry_{index}")
        linen_comments = st.text_area("Linen Needed/Comments", key=f"linen_{index}")

        st.subheader("🔑 Access & Keys")
        keys = st.radio("Keys Provided?", ["Yes", "No"], key=f"keys_{index}")
        alarm_code = st.radio("Alarm/Key Codes Available?", ["Yes", "No"], key=f"alarm_{index}")
        garage = st.radio("Garage (Bayside)?", ["Yes", "No"], key=f"garage_{index}")

        st.subheader("🧴 Amenities Checklist")
        amenities = {
            "Toilet Paper (per bathroom)": "1 roll",
            "Kitchen Paper Towel": "1 roll",
            "Coffee": "NA",
            "Tea": "NA",
            "Sugar": "NA",
            "Hand Soap": "NA",
            "Shower Gel": "NA",
            "Conditioner": "NA",
            "Welcome Groceries Package": "NA",
        }

        amenity_data = {}
        for item, qty in amenities.items():
            restock = st.radio(f"{item} - Qty: {qty}", ["✔", "X"], key=f"{item}_{index}")
            amenity_data[item] = restock

        st.subheader("🗒️ Additional Comments/Instructions")
        comments = st.text_area("Comments", key=f"comments_{index}")

        return {
            "Reservation #": index + 1,
            "Client Name": client_name,
            "Reservation Date": str(reservation_date),
            "Property Address": prop_address,
            "Property Setting": custom_setting if property_setting == "Custom" else property_setting,
            "Villa Name": villa_name,
            "Status": status,
            "Clean Type": ", ".join(clean_type),
            "PAX": pax,
            "Start Time": str(start_time),
            "Laundry": laundry,
            "Linen Comments": linen_comments,
            "Keys Provided": keys,
            "Alarm/Key Code": alarm_code,
            "Garage": garage,
            "Amenities": amenity_data,
            "Additional Comments": comments
        }

# Collect reservation entries
reservations = []
for i in range(st.session_state.property_count):
    reservations.append(reservation_form(i))

# Format CSV
def format_reservations_to_csv(data):
    flat_data = []
    for res in data:
        base = {k: v for k, v in res.items() if k != "Amenities"}
        for item, restock in res["Amenities"].items():
            base[f"Amenity - {item}"] = restock
        flat_data.append(base)
    return pd.DataFrame(flat_data)

# Function to send data to n8n
def send_to_n8n(webhook_url, csv_data, reservations_data):
    try:
        payload = {
            "csv_data": csv_data.decode('utf-8'),
            "reservations": reservations_data,
            "timestamp": str(date.today()),
            "total_reservations": len(reservations_data)
        }
        
        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        if response.status_code == 200:
            return True, "Data sent successfully to n8n!"
        else:
            return False, f"Error: {response.status_code} - {response.text}"
    
    except requests.exceptions.RequestException as e:
        return False, f"Connection error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"

# Submit and export
if st.button("✅ Submit & Save as CSV"):
    df = format_reservations_to_csv(reservations)
    csv_data = df.to_csv(index=False).encode('utf-8')
    
    # Always show success message and download button
    st.success("✅ Reservation data saved!")
    st.download_button("📥 Download CSV", csv_data, file_name="reservations.csv", mime="text/csv")
    
    # Send to n8n if webhook URL is provided
    if N8N_WEBHOOK_URL:
        with st.spinner("Sending data to n8n..."):
            success, message = send_to_n8n(N8N_WEBHOOK_URL, csv_data, reservations)
            
            if success:
                st.success(f"🚀 {message}")
            else:
                st.error(f"❌ Failed to send to n8n: {message}")
    else:
        st.info("💡 Add your n8n webhook URL in the sidebar to automatically send data to n8n")
    
    # Display the data
    st.dataframe(df)

# Display current configuration
if N8N_WEBHOOK_URL:
    st.sidebar.success("✅ n8n webhook configured")
else:
    st.sidebar.warning("⚠️ No n8n webhook URL configured")

st.sidebar.markdown("---")
st.sidebar.markdown("### 📋 Usage Instructions")
st.sidebar.markdown("""
1. Enter your n8n webhook URL in the sidebar
2. Fill out reservation forms
3. Click 'Submit & Save as CSV'
4. Data will be sent to n8n automatically
5. Download CSV file as backup
""")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🔗 n8n Payload Structure")
st.sidebar.code("""
{
    "csv_data": "string (CSV content)",
    "reservations": [...],
    "timestamp": "YYYY-MM-DD",
    "total_reservations": number
}
""", language="json")
