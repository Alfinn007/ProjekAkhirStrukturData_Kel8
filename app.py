import streamlit as st
import json
import folium
from folium.plugins import AntPath
import itertools 
import math
from streamlit_folium import st_folium

# --- IMPORT MODULE BUATAN SENDIRI ---
try:
    from modules.graph_algo import TobaccoGraph
except ImportError:
    st.error("⚠️ Error: File 'modules/graph_algo.py' tidak ditemukan.")
    st.stop()

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Sistem Optimasi Tembakau", layout="wide", initial_sidebar_state="expanded")

# --- DATA USER (Hardcoded) ---
USERS = {
    "bos@tembakau.com": {"pass": "admin123", "role": "bos", "name": "Bapak Pimpinan"},
    "karyawan@tembakau.com": {"pass": "user123", "role": "karyawan", "name": "Staff Logistik"}
}

# --- FUNGSI HITUNG JARAK (HAVERSINE) ---
def hitung_jarak(lat1, lon1, lat2, lon2):
    R = 6371.0
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    dlon = lon2_rad - lon1_rad
    dlat = lat2_rad - lat1_rad
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

# --- FUNGSI LOAD & SAVE DATA ---
@st.cache_data
def load_data():
    try:
        with open('data/data_tembakau.json', 'r') as f: 
            data = json.load(f)
        return data
    except FileNotFoundError:
        return {
            "nodes": {
                "Wuluhan": {"lat": -8.2289, "lon": 113.4864},
                "Ambulu": {"lat": -8.3447, "lon": 113.6067},
                "Balung": {"lat": -8.2611, "lon": 113.5239},
                "Gudang_Pusat": {"lat": -8.1721, "lon": 113.7007}
            }
        }

def save_data(new_data):
    import os
    if not os.path.exists('data'):
        os.makedirs('data')
    with open('data/data_tembakau.json', 'w') as f:
        json.dump(new_data, f, indent=4)
    st.cache_data.clear()

# --- SESSION STATE ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'user_role' not in st.session_state:
    st.session_state.user_role = None
if 'route_result' not in st.session_state:
    st.session_state.route_result = None

# --- LOGIN PAGE ---
def login_page():
    st.markdown("<h1 style='text-align: center;'>🔐 Login Sistem Distribusi</h1>", unsafe_allow_html=True)
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Masuk", use_container_width=True)
            if submit:
                if email in USERS and USERS[email]["pass"] == password:
                    st.session_state.logged_in = True
                    st.session_state.user_role = USERS[email]["role"]
                    st.session_state.user_name = USERS[email]["name"]
                    st.rerun()
                else:
                    st.error("Email atau Password salah!")
    st.info("Akun Demo: bos@tembakau.com / admin123")
    st.info("Akun Demo: karyawan@tembakau.com / user123")

# --- MAIN APP ---
def main_app():
    data = load_data()
    
    # Ambil koordinat saja, abaikan data['edges']
    koordinat = {}
    for nama, info in data['nodes'].items():
        koordinat[nama] = (info['lat'], info['lon'])

    # --- SIDEBAR ---
    with st.sidebar:
        st.title(f"👨‍💼 {st.session_state.user_name}")
        st.caption(f"Akses: {st.session_state.user_role.upper()}")
        
        if st.button("Logout", type="secondary"):
            st.session_state.logged_in = False
            st.session_state.route_result = None
            st.rerun()
        
        st.markdown("---")
        
        menu_options = ["Pencarian Rute"]
        if st.session_state.user_role == "bos":
            menu_options.append("Manajemen Jalur (Bos)")
        
        menu = st.radio("Navigasi Menu", menu_options)
        
        st.markdown("---")
        
        # --- LOGIKA BARU: GENERATE JALUR OTOMATIS (Full Connected) ---
        # Kita buat semua kemungkinan jalur antar titik
        all_possible_routes = []
        node_names = sorted(list(koordinat.keys()))
        
        # itertools.combinations membuat pasangan unik: (A, B), (A, C), (B, C) dst.
        for u, v in itertools.combinations(node_names, 2):
            all_possible_routes.append(f"{u} -> {v}")

        # PARAMETER CONFIG
        st.subheader("⚙️ Parameter & Simulasi")
        
        rusak = st.multiselect(
            "🚧 Simulasi Jalan Putus/Macet",
            options=all_possible_routes,
            help="Pilih jalur untuk diputus. Karena sistem otomatis, jalur alternatif akan langsung dicari."
        )
        
        with st.expander("💰 Konfigurasi Biaya"):
            harga_bbm = st.number_input("Harga Solar / Liter", value=6800)
            konsumsi_bbm = st.number_input("Konsumsi BBM (Km/L)", value=8)
            kecepatan = st.number_input("Kecepatan Rata-rata (Km/Jam)", value=40)

    # --- INIT GRAPH OTOMATIS (MENGABAIKAN JSON EDGES) ---
    graph = TobaccoGraph()
    
    # Loop untuk menghubungkan SEMUA titik dengan SEMUA titik (Mesh Topology)
    # Kecuali yang dipilih di menu "Rusak"
    for u, v in itertools.combinations(node_names, 2):
        route_name_1 = f"{u} -> {v}" # A ke B
        route_name_2 = f"{v} -> {u}" # B ke A (untuk jaga-jaga pengecekan string)
        
        # Cek apakah jalur ini sedang disimulasikan rusak
        if route_name_1 not in rusak and route_name_2 not in rusak:
            lat1, lon1 = koordinat[u]
            lat2, lon2 = koordinat[v]
            
            # Hitung Jarak Real-time
            jarak = hitung_jarak(lat1, lon1, lat2, lon2)
            
            # Masukkan ke Graph
            # add_edge di class Anda biasanya sudah bolak-balik (undirected), 
            # tapi tidak ada salahnya memastikan logika di sini.
            graph.add_edge(u, v, jarak)

    # --- MENU 1: RUTE + OPTIMASI TSP ---
    if menu == "Pencarian Rute":
        st.title("🚛 Optimasi Rute Distribusi (Mode Otomatis)")
        st.info("ℹ️ Sistem menggunakan mode **Fully Connected**. Semua titik dianggap terhubung garis lurus kecuali diblokir.")

        if rusak:
            st.warning(f"⚠️ {len(rusak)} jalur dinonaktifkan.")
        
        col_input, col_map = st.columns([1, 2])
        
        with col_input:
            st.markdown("### 📍 Rencana Perjalanan")
            start_node = st.selectbox("Dari (Gudang/Pos)", node_names)
            
            available_stops = [loc for loc in node_names if loc != start_node]
            stops = st.multiselect(
                "Titik Singgah (Urutan akan dioptimasi)", 
                available_stops
            )
            
            if len(stops) == 8:
                st.caption("⚠️ Batas maksimum titik tercapai (8 titik).")
            
            available_ends = [loc for loc in node_names if loc != start_node and loc not in stops]
            end_node = st.selectbox("Tujuan Akhir", available_ends if available_ends else node_names)

            calc_btn = st.button("🚀 Hitung Rute Tercepat", type="primary")
            

        # --- LOGIKA PERHITUNGAN ---
        if calc_btn:
            if len(stops) > 8:
                st.error("Terlalu banyak titik singgah!")
                st.stop()
            best_route_sequence = []
            best_full_path = []
            min_total_dist = float('inf')
            found_solution = False
            
            permuted_stops = list(itertools.permutations(stops))
            if not permuted_stops:
                permuted_stops = [()]

            progress_text = "Menganalisis rute terbaik..."
            my_bar = st.progress(0, text=progress_text)
            
            for idx, p_stop in enumerate(permuted_stops):
                my_bar.progress(int((idx / len(permuted_stops)) * 100))
                
                current_sequence = [start_node] + list(p_stop) + [end_node]
                current_dist = 0
                current_full_path = []
                valid_sequence = True
                
                for i in range(len(current_sequence) - 1):
                    c_start = current_sequence[i]
                    c_end = current_sequence[i+1]
                    
                    path_seg, dist_seg = graph.dijkstra(c_start, c_end)
                    
                    if not path_seg:
                        valid_sequence = False
                        break
                    
                    if i == 0:
                        current_full_path.extend(path_seg)
                    else:
                        current_full_path.extend(path_seg[1:])
                    
                    current_dist += dist_seg
                
                if valid_sequence:
                    if current_dist < min_total_dist:
                        min_total_dist = current_dist
                        best_route_sequence = current_sequence
                        best_full_path = current_full_path
                        found_solution = True
            
            my_bar.empty()

            if found_solution:
                st.session_state.route_result = {
                    "success": True,
                    "dist": round(min_total_dist, 2),
                    "sequence": best_route_sequence,
                    "full_path": best_full_path,
                    "start": start_node,
                    "end": end_node,
                    "stops": stops
                }
            else:
                st.session_state.route_result = {"success": False}

        # --- TAMPILKAN HASIL ---
        if st.session_state.route_result:
            result = st.session_state.route_result
            
            if result["success"]:
                with col_input:
                    st.success("✅ Rute Optimal Ditemukan!")
                    total_liter = result["dist"] / konsumsi_bbm
                    total_biaya = total_liter * harga_bbm
                    waktu_menit = (result["dist"] / kecepatan) * 60
                    
                    c1, c2 = st.columns(2)
                    c1.metric("Jarak Total", f"{result['dist']} Km")
                    c1.metric("Estimasi Waktu", f"{int(waktu_menit)} Min")
                    c2.metric("BBM", f"{total_liter:.1f} L")
                    c2.metric("Biaya BBM", f"Rp {int(total_biaya):,}")
                    
                    st.markdown("---")
                    st.markdown("### 🔄 Urutan Kunjungan:")
                    for i, node in enumerate(result["sequence"]):
                        icon = "🏁" if i == len(result["sequence"])-1 else "➡️"
                        if i == 0: icon = "🏠"
                        st.write(f"{icon} **{node}**")

                with col_map:
                    st.markdown("### 🗺️ Visualisasi Peta")
                    
                    # --- FITUR BARU: TOMBOL TAMPILKAN JALUR RUSAK ---
                    show_error_paths = st.checkbox("🔴 Tampilkan Jalur Error (Rusak/Macet)", value=True)

                    center_lat, center_lon = koordinat[result["start"]]
                    m = folium.Map(location=[center_lat, center_lon], zoom_start=11)
                    
                    # 1. GAMBAR JALUR RUSAK (Jika dicentang)
                    if show_error_paths and rusak:
                        for jalur_str in rusak:
                            # Format string: "NodeA -> NodeB"
                            try:
                                origin, dest = jalur_str.split(" -> ")
                                if origin in koordinat and dest in koordinat:
                                    path_coords_error = [koordinat[origin], koordinat[dest]]
                                    
                                    # Gambar garis merah putus-putus
                                    folium.PolyLine(
                                        locations=path_coords_error, 
                                        color="red", 
                                        weight=4, 
                                        opacity=0.6,
                                        dash_array='10, 10',  # Membuat garis putus-putus
                                        tooltip=f"⛔ JALUR TERPUTUS: {origin} ke {dest}"
                                    ).add_to(m)
                                    
                                    # Tambahkan icon silang di tengah jalur (opsional, visual manis)
                                    mid_lat = (koordinat[origin][0] + koordinat[dest][0]) / 2
                                    mid_lon = (koordinat[origin][1] + koordinat[dest][1]) / 2
                                    folium.Marker(
                                        [mid_lat, mid_lon],
                                        icon=folium.Icon(color='red', icon='remove', prefix='fa'),
                                        tooltip="Blokir"
                                    ).add_to(m)
                            except ValueError:
                                continue

                    # 2. GAMBAR GARIS RUTE OPTIMAL (Biru)
                    path_coords = [koordinat[nama] for nama in result["full_path"] if nama in koordinat]
                    if path_coords:
                        folium.PolyLine(
                            locations=path_coords, 
                            color="blue", 
                            weight=6, 
                            opacity=0.8,
                            tooltip="Jalur Optimal"
                        ).add_to(m)
                        
                        # Animasi gerak (AntPath) agar lebih keren
                        AntPath(
                            locations=path_coords,
                            dash_array=[10, 20],
                            delay=1000,
                            color='cyan',
                            pulse_color='white',
                            weight=3,
                            opacity=0.6
                        ).add_to(m)
                    
                    # 3. GAMBAR MARKER (Titik Lokasi)
                    for nama, coord in koordinat.items():
                        color = "lightgray"; icon = "info-sign"; popup = nama
                        
                        if nama == result["start"]:
                            color = "green"; icon = "play"
                        elif nama == result["end"]:
                            color = "red"; icon = "flag"
                        elif nama in result["stops"]:
                            urutan = result["sequence"].index(nama)
                            color = "orange"; icon = "star"
                            popup = f"{nama} (Urutan: {urutan})"
                        
                        folium.Marker(coord, popup=popup, icon=folium.Icon(color=color, icon=icon)).add_to(m)
                    
                    st_folium(m, width=800, height=500)
            else:
                st.error("❌ Jalur tidak ditemukan! Semua akses ke tujuan mungkin terblokir.")

    # --- MENU 2: MANAJEMEN (BOS) ---
    elif menu == "Manajemen Jalur (Bos)":
        st.title("🛠️ Manajemen Lokasi (Node)")
        st.info("ℹ️ Klik pada peta untuk mendapatkan koordinat lokasi baru secara otomatis.")
        
        tab1, tab3 = st.tabs(["➕ Tambah Node (Peta)", "📂 Data JSON"])
        
        with tab1:
            # 1. Tampilkan Peta untuk Picking
            st.markdown("### 🗺️ Pilih Lokasi di Peta")
            
            # Tentukan tengah peta (bisa ambil rata-rata dari node yang ada atau hardcode Jember)
            center_lat, center_lon = -8.25, 113.6 
            m_picker = folium.Map(location=[center_lat, center_lon], zoom_start=11)
            
            # Tampilkan node yang SUDAH ADA sebagai referensi (warna abu-abu)
            for nama, info in data['nodes'].items():
                folium.Marker(
                    [info['lat'], info['lon']], 
                    popup=f"{nama} (Sudah ada)", 
                    icon=folium.Icon(color="gray", icon="info-sign")
                ).add_to(m_picker)

            # Tambahkan instruksi klik
            m_picker.add_child(folium.LatLngPopup())

            # Render peta dan tangkap event klik
            map_data = st_folium(m_picker, height=400, width="100%", key="map_picker")

            # 2. Logika Menangkap Koordinat
            # Default value jika belum klik
            click_lat = -8.2000
            click_lon = 113.6000

            if map_data and map_data.get("last_clicked"):
                click_lat = map_data["last_clicked"]["lat"]
                click_lon = map_data["last_clicked"]["lng"]
                st.success(f"📍 Titik terpilih: {click_lat:.5f}, {click_lon:.5f}")
            else:
                st.caption("👆 Silakan klik peta di atas untuk mengisi koordinat otomatis.")

            st.markdown("---")

            # 3. Form Input Data
            with st.form("add_node"):
                st.subheader("📝 Detail Lokasi Baru")
                
                col_form1, col_form2 = st.columns(2)
                
                with col_form1:
                    name = st.text_input("Nama Lokasi Baru (Cth: Gudang_Wirolegi)")
                
                with col_form2:
                    # Value mengambil dari variabel click_lat/lon yang update saat peta diklik
                    lat = st.number_input("Latitude", value=click_lat, format="%.5f")
                    lon = st.number_input("Longitude", value=click_lon, format="%.5f")
                
                if st.form_submit_button("💾 Simpan Lokasi"):
                    if name and name not in data['nodes']:
                        data['nodes'][name] = {"lat": lat, "lon": lon}
                        save_data(data)
                        st.success(f"✅ Lokasi '{name}' berhasil disimpan! Koordinat: {lat}, {lon}")
                        
                        # Hapus cache/session agar peta ter-refresh
                        st.session_state.pop("map_picker", None) 
                        import time
                        time.sleep(1) # Jeda sedikit agar user membaca pesan sukses
                        st.rerun()
                    elif name in data['nodes']:
                        st.error("❌ Nama lokasi sudah ada! Harap gunakan nama lain.")
                    else: 
                        st.error("❌ Nama tidak boleh kosong.")
        
        with tab3:
            st.write("Data Mentah (JSON):")
            st.json(data)

if st.session_state.logged_in:
    main_app()
else:
    login_page()