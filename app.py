import streamlit as st
import pandas as pd
import io
import folium
from streamlit_folium import st_folium

# Konfigurasi Halaman Streamlit
st.set_page_config(page_title="Sales Map Maker - SLSNAME & RAYON", layout="wide")

st.title("🗺️ Sales Map Maker: Hierarki SLSNAME $\rightarrow$ RAYON")
st.markdown("Unggah file data outlet Anda. File KML yang diunduh akan otomatis terstruktur rapi: **Folder Utama (SLSNAME) $\rightarrow$ Sub-Folder (RAYON)** dengan warna penanda berbeda.")

# 1. Widget Upload File di Sidebar
st.sidebar.header("📁 Unggah Data Outlet")
uploaded_file = st.sidebar.file_uploader("Pilih file data mentah (.txt / .csv) atau Excel (.xlsx)", type=["xlsx", "xls", "txt", "csv"])

@st.cache_data
def process_uploaded_file(file):
    filename = file.name.lower()
    if filename.endswith('.xlsx') or filename.endswith('.xls'):
        df = pd.read_excel(file)
    else:
        try:
            content = file.getvalue().decode("utf-8")
        except:
            file.seek(0)
            content = file.getvalue().decode("latin1")
            
        df = pd.read_csv(io.StringIO(content), sep='|')
            
    def parse_lat_lon(row):
        try:
            lat = str(row['LATITUDE']).strip()
            lon = str(row['LONGITUDE']).strip()
            
            if '.' in lat:
                lat_f = float(lat)
            else:
                lat_f = float(lat)
                while abs(lat_f) > 10:
                    lat_f /= 10
                    
            if '.' in lon:
                lon_f = float(lon)
            else:
                lon_f = float(lon)
                while abs(lon_f) > 180:
                    lon_f /= 10
            return lat_f, lon_f
        except:
            return None, None

    coords = [parse_lat_lon(row) for _, row in df.iterrows()]
    df['FIXED_LAT'] = [c[0] for c in coords]
    df['FIXED_LONG'] = [c[1] for c in coords]
    
    # Validasi kolom RAYON dan SLSNAME
    if 'RAYON' not in df.columns or df['RAYON'].isna().all():
        df['RAYON'] = 'R01'
    else:
        df['RAYON'] = df['RAYON'].fillna('R01').astype(str).str.strip()
        
    if 'SLSNAME' not in df.columns or df['SLSNAME'].isna().all():
        df['SLSNAME'] = 'General Sales'
    else:
        df['SLSNAME'] = df['SLSNAME'].fillna('General Sales').astype(str).str.strip()

    return df

if uploaded_file is not None:
    try:
        df = process_uploaded_file(uploaded_file)
        st.sidebar.success(f"Berhasil memuat {len(df)} baris data!")
    except Exception as e:
        st.error(f"Gagal memproses file: {e}")
        st.stop()
else:
    st.info("👋 Silakan unggah file data mentah (`.txt` atau `.xlsx`) Anda melalui panel sidebar di sebelah kiri.")
    try:
        df = pd.read_excel('longlat.xlsx', sheet_name='Sheet1')
        def parse_lat_lon_def(row):
            lat = str(row['LATITUDE']).strip()
            lon = str(row['LONGITUDE']).strip()
            lat_f = float(lat) if '.' in lat else float(lat) / 1e14 if abs(float(lat))>10 else float(lat)
            while abs(lat_f) > 10: lat_f /= 10
            lon_f = float(lon) if '.' in lon else float(lon) / 1e14 if abs(float(lon))>180 else float(lon)
            while abs(lon_f) > 180: lon_f /= 10
            return lat_f, lon_f
        df['FIXED_LAT'] = [parse_lat_lon_def(r)[0] for _, r in df.iterrows()]
        df['FIXED_LONG'] = [parse_lat_lon_def(r)[1] for _, r in df.iterrows()]
        st.warning("⚠️ Menggunakan data bawaan sistem (`longlat.xlsx`). Unggah file Anda di sidebar untuk menggantinya.")
    except:
        st.stop()

# 2. Sidebar Filter & Tombol KML
st.sidebar.header("🔍 Filter & Ekspor")

all_rayons = sorted(df['RAYON'].dropna().unique())
selected_rayons = st.sidebar.multiselect("Pilih Rayon:", all_rayons, default=all_rayons)

all_sales = sorted(df['SLSNAME'].dropna().unique())
selected_sales = st.sidebar.multiselect("Pilih Sales (SLSNAME):", all_sales, default=all_sales)

filtered_df = df[df['RAYON'].isin(selected_rayons) & df['SLSNAME'].isin(selected_sales)]

st.sidebar.markdown("---")
st.sidebar.subheader("📥 Unduh KML")

# Generator KML Berbasis SLSNAME > RAYON
def generate_slsname_rayon_kml(data_subset):
    kml_header = '<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n    <name>Sales Route Map (SLSNAME > RAYON)</name>\n'
    kml_footer = '</Document>\n</kml>'
    
    # Palet Warna KML (AABBGGRR) untuk Rayon
    rayon_kml_colors = {
        'R01': 'ff0000ff', 'R02': 'ffff0000', 'R03': 'ff00ff00', 'R04': 'ff800080',
        'R05': 'ff007fff', 'R06': 'ff00ffff', 'R07': 'ff2a4aa6', 'R08': 'ffff80ff',
        'R09': 'ff808080', 'R10': 'ff80c066', 'R11': 'ff3c4dfc', 'R12': 'ffcbe08d'
    }
    
    rayons_in_data = sorted(data_subset['RAYON'].dropna().unique())
    kml_content = [kml_header]
    
    for rayon in rayons_in_data:
        color = rayon_kml_colors.get(rayon, 'ffffffff')
        kml_content.append(f'''
    <Style id="style_{rayon}">
        <IconStyle>
            <color>{color}</color>
            <scale>0.9</scale>
            <Icon>
                <href>http://maps.google.com/mapfiles/kml/paddle/wht-circle.png</href>
            </Icon>
        </IconStyle>
    </Style>''')
        
    sales_list = sorted(data_subset['SLSNAME'].dropna().unique())
    for sales in sales_list:
        safe_sales = str(sales).replace('&', '&amp;').strip()
        # Level 1: Folder Nama Sales (SLSNAME)
        kml_content.append(f'''
    <Folder>
        <name>{safe_sales}</name>''')
        
        sales_subset = data_subset[data_subset['SLSNAME'] == sales]
        rayons_for_sales = sorted(sales_subset['RAYON'].dropna().unique())
        
        for rayon in rayons_for_sales:
            # Level 2: Sub-folder Rayon (RAYON) di dalam folder Sales
            kml_content.append(f'''
        <Folder>
            <name>Rayon {rayon}</name>''')
            
            rayon_subset = sales_subset[sales_subset['RAYON'] == rayon]
            for _, row in rayon_subset.iterrows():
                lat, lon = row.get('FIXED_LAT'), row.get('FIXED_LONG')
                if pd.isna(lat) or pd.isna(lon): continue
                cust_name = str(row.get('CUSTNAME', '')).replace('&', '&amp;')
                cust_no = str(row.get('CUSTNO', ''))
                alamat = str(row.get('ALAMAT', '')).replace('&', '&amp;')
                kecamatan = str(row.get('KECAMATAN', '')).replace('&', '&amp;')
                pemilik = str(row.get('PEMILIK', '')).replace('&', '&amp;')
                
                desc = f"Pemilik: {pemilik}&#10;Alamat: {alamat}, {kecamatan}&#10;Rayon: {rayon}&#10;Sales: {sales}"
                
                kml_content.append(f'''
            <Placemark>
                <name>{cust_name} ({cust_no})</name>
                <description>{desc}</description>
                <styleUrl>#style_{rayon}</styleUrl>
                <Point>
                    <coordinates>{lon},{lat},0</coordinates>
                </Point>
            </Placemark>''')
            kml_content.append('\n        </Folder>')
            
        kml_content.append('\n    </Folder>')
        
    kml_content.append(kml_footer)
    return "".join(kml_content)

kml_data = generate_slsname_rayon_kml(filtered_df)

st.sidebar.download_button(
    label="📥 Download KML (SLSNAME $\rightarrow$ RAYON)",
    data=kml_data,
    file_name="Sales_SLSNAME_RAYON.kml",
    mime="application/vnd.google-earth.kml+xml"
)

# 3. Tampilkan Peta Interaktif di Web
rayon_colors_map = {
    'R01': 'red', 'R02': 'blue', 'R03': 'green', 'R04': 'purple',
    'R05': 'orange', 'R06': 'cadetblue', 'R07': 'darkred', 'R08': 'pink',
    'R09': 'gray', 'R10': 'lightgreen', 'R11': 'beige', 'R12': 'darkblue'
}

m = folium.Map(location=[-4.95, 119.58], zoom_start=11, control_scale=True)

for _, row in filtered_df.iterrows():
    lat = row['FIXED_LAT']
    lon = row['FIXED_LONG']
    if pd.isna(lat) or pd.isna(lon): continue
    
    cust_name = str(row.get('CUSTNAME', ''))
    cust_no = str(row.get('CUSTNO', ''))
    alamat = str(row.get('ALAMAT', ''))
    kecamatan = str(row.get('KECAMATAN', ''))
    rayon = str(row.get('RAYON', ''))
    slsname = str(row.get('SLSNAME', ''))
    pemilik = str(row.get('PEMILIK', ''))
    
    popup_html = f"""
    <div style="font-family: Arial; font-size: 12px; width: 220px;">
        <b>{cust_name}</b> ({cust_no})<br>
        <b>Pemilik:</b> {pemilik}<br>
        <b>Alamat:</b> {alamat}, {kecamatan}<br>
        <b>Rayon:</b> {rayon}<br>
        <b>Sales:</b> {slsname}
    </div>
    """
    color = rayon_colors_map.get(rayon, 'gray')
    
    folium.CircleMarker(
        location=[lat, lon],
        radius=5,
        color=color,
        fill=True,
        fill_color=color,
        fill_opacity=0.8,
        popup=folium.Popup(popup_html, max_width=250),
        tooltip=f"{cust_name} ({rayon})"
    ).add_to(m)

st.info(f"Menampilkan **{len(filtered_df)}** dari total **{len(df)}** outlet pada peta.")
st_folium(m, width=1200, height=550)

with st.expander("Lihat Tabel Data Outlet"):
    st.dataframe(filtered_df)
