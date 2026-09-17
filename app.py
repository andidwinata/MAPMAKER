import streamlit as st
import pandas as pd
import io

# Konfigurasi Halaman Streamlit
st.set_page_config(page_title="Sales Map Maker - 12 Rayon", layout="wide")

st.title("🗺️ Sales Map Maker: Konverter Data ke KML & Peta Interaktif")
st.markdown("Unggah file Excel (`.xlsx`) atau data mentah outlet Anda untuk dipetakan ke 12 Rayon dan diunduh dalam format KML.")

# 1. Widget Upload File di Sidebar
st.sidebar.header("📁 Unggah Data Outlet")
uploaded_file = st.sidebar.file_uploader("Pilih file Excel (.xlsx) atau teks (.txt/.csv)", type=["xlsx", "xls", "txt", "csv"])

@st.cache_data
def process_uploaded_file(file):
    # Deteksi jenis file
    if file.name.endswith('.xlsx') or file.name.endswith('.xls'):
        df = pd.read_excel(file)
    else:
        # Coba baca txt/csv dengan pemisah umum (tab atau koma)
        try:
            df = pd.read_csv(file, sep='\t')
            if len(df.columns) <= 1:
                file.seek(0)
                df = pd.read_csv(file, sep=',')
        except:
            file.seek(0)
            df = pd.read_csv(file)
            
    # Fungsi normalisasi koordinat jika format integer panjang
    def parse_lat_lon(row):
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

    df['FIXED_LAT'] = [parse_lat_lon(row)[0] for _, row in df.iterrows()]
    df['FIXED_LONG'] = [parse_lat_lon(row)[1] for _, row in df.iterrows()]
    return df

# Jika file belum diunggah, gunakan default file yang ada atau beri panduan
if uploaded_file is not None:
    try:
        df = process_uploaded_file(uploaded_file)
        st.sidebar.success(f"Berhasil memuat {len(df)} baris data!")
    except Exception as e:
        st.error(f"Gagal memproses file: {e}")
        st.stop()
else:
    st.info("👋 Silakan unggah file Excel/TXT Anda melalui panel sidebar di sebelah kiri untuk mulai.")
    # Coba load file bawaan jika ada di direktori
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
        st.warning("⚠️ Menggunakan data bawaan sistem (`longlat.xlsx`). Unggah file Anda sendiri di sidebar untuk menggantinya.")
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

# Fungsi Generator KML dari DataFrame yang difilter
def generate_kml_string(data_subset):
    kml_header = '<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2">\n<Document>\n    <name>Sales Map - 12 Rayon</name>\n'
    kml_footer = '</Document>\n</kml>'
    
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
            <scale>0.8</scale>
            <Icon>
                <href>http://maps.google.com/mapfiles/kml/paddle/wht-circle.png</href>
            </Icon>
        </IconStyle>
    </Style>''')
        
    for rayon in rayons_in_data:
        kml_content.append(f'''
    <Folder>
        <name>Rayon {rayon}</name>''')
        subset = data_subset[data_subset['RAYON'] == rayon]
        for _, row in subset.iterrows():
            lat, lon = row['FIXED_LAT'], row['FIXED_LONG']
            if pd.isna(lat) or pd.isna(lon): continue
            cust_name = str(row.get('CUSTNAME', '')).replace('&', '&amp;')
            cust_no = str(row.get('CUSTNO', ''))
            alamat = str(row.get('ALAMAT', '')).replace('&', '&amp;')
            kecamatan = str(row.get('KECAMATAN', '')).replace('&', '&amp;')
            slsname = str(row.get('SLSNAME', '')).replace('&', '&amp;')
            pemilik = str(row.get('PEMILIK', '')).replace('&', '&amp;')
            
            desc = f"Pemilik: {pemilik}&#10;Alamat: {alamat}, {kecamatan}&#10;Rayon: {rayon}&#10;Sales: {slsname}"
            
            kml_content.append(f'''
        <Placemark>
            <name>{cust_name} ({cust_no})</name>
            <description>{desc}</description>
            <styleUrl>#style_{rayon}</styleUrl>
            <Point>
                <coordinates>{lon},{lat},0</coordinates>
            </Point>
        </Placemark>''')
        kml_content.append('\n    </Folder>')
        
    kml_content.append(kml_footer)
    return "".join(kml_content)

kml_data = generate_kml_string(filtered_df)

st.sidebar.download_button(
    label="📥 Download File KML (Sesuai Filter)",
    data=kml_data,
    file_name="Sales_Map_Filtered.kml",
    mime="application/vnd.google-earth.kml+xml"
)

# 3. Tampilkan Peta Interaktif menggunakan Folium
import folium
from streamlit_folium import st_folium

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

st.info(Menampilkan **{len(filtered_df)}** dari total **{len(df)}** outlet pada peta.)
st_folium(m, width=1200, height=550)

with st.expander("Lihat Tabel Data Outlet"):
    st.dataframe(filtered_df)
