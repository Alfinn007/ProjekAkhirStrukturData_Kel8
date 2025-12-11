import streamlit as st
import json
import folium
import itertools 
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
            },
            "edges": [
                {"from": "Wuluhan", "to": "Ambulu", "weight": 7},
                {"from": "Wuluhan", "to": "Balung", "weight": 10},
                {"from": "Ambulu", "to": "Gudang_Pusat", "weight": 20}
            ]
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

# [FIX] Inisialisasi State untuk Hasil Perhitungan agar tidak hilang saat Rerun
if 'route_result' not in st.session_state:
    st.session_state.route_result = None # Akan diisi dictionary hasil

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
    st.info("Akun Demo:\n\nBos: bos@tembakau.com / admin123\n\nKaryawan: karyawan@tembakau.com / user123")

# --- MAIN APP ---
def main_app():
    data = load_data()
    
    # --- SIDEBAR ---
    with st.sidebar:
        st.title(f"👨‍💼 {st.session_state.user_name}")
        st.caption(f"Akses: {st.session_state.user_role.upper()}")
        
        if st.button("Logout", type="secondary"):
            st.session_state.logged_in = False
            # Reset hasil hitungan juga saat logout
            st.session_state.route_result = None
            st.rerun()
        
        st.markdown("---")
        
        menu_options = ["Pencarian Rute"]
        if st.session_state.user_role == "bos":
            menu_options.append("Manajemen Jalur (Bos)")
        
        menu = st.radio("Navigasi Menu", menu_options)
        
        st.markdown("---")
        
        # PARAMETER CONFIG
        st.subheader("⚙️ Parameter & Simulasi")
        all_routes = [f"{e['from']} -> {e['to']}" for e in data['edges']]
        rusak = st.multiselect(
            "🚧 Simulasi Jalan Putus/Macet",
            options=all_routes,
            help="Jalur yang dipilih akan dianggap putus oleh algoritma."
        )
        
        with st.expander("💰 Konfigurasi Biaya"):
            harga_bbm = st.number_input("Harga Solar / Liter", value=6800)
            konsumsi_bbm = st.number_input("Konsumsi BBM (Km/L)", value=8)
            kecepatan = st.number_input("Kecepatan Rata-rata (Km/Jam)", value=40)

    # --- INIT GRAPH (Imported Class) ---
    graph = TobaccoGraph()
    koordinat = {}

    for nama, info in data['nodes'].items():
        koordinat[nama] = (info['lat'], info['lon'])

    for rute in data['edges']:
        nama_rute = f"{rute['from']} -> {rute['to']}"
        if nama_rute not in rusak:
            graph.add_edge(rute['from'], rute['to'], rute['weight'])

    # --- MENU 1: RUTE + OPTIMASI TSP ---
    if menu == "Pencarian Rute":
        st.title("🚛 Optimasi Rute Distribusi")
        
        if rusak:
            st.warning(f"⚠️ Mode Simulasi Aktif: {len(rusak)} jalur dinonaktifkan.")
        
        col_input, col_map = st.columns([1, 2])
        
        with col_input:
            list_lokasi = sorted(list(koordinat.keys()))
            
            st.markdown("### 📍 Rencana Perjalanan")
            start_node = st.selectbox("Dari (Gudang/Pos)", list_lokasi)
            
            available_stops = [loc for loc in list_lokasi if loc != start_node]
            stops = st.multiselect(
                "Titik Singgah (Urutan akan dioptimasi)", 
                available_stops
            )
            
            available_ends = [loc for loc in list_lokasi if loc != start_node and loc not in stops]
            end_node = st.selectbox("Tujuan Akhir", available_ends if available_ends else list_lokasi)

            calc_btn = st.button("🚀 Hitung Rute Tercepat", type="primary")

        # --- LOGIKA TOMBOL (SIMPAN HASIL KE SESSION STATE) ---
        if calc_btn:
            best_route_sequence = []
            best_full_path = []
            min_total_dist = float('inf')
            found_solution = False
            
            permuted_stops = list(itertools.permutations(stops))
            if not permuted_stops:
                permuted_stops = [()]

            progress_text = "Menganalisis kombinasi rute..."
            my_bar = st.progress(0, text=progress_text)
            total_perms = len(permuted_stops)
            
            for idx, p_stop in enumerate(permuted_stops):
                my_bar.progress(int((idx / total_perms) * 100), text=f"Cek Kombinasi {idx+1}...")
                
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
                # [FIX] SIMPAN KE SESSION STATE
                st.session_state.route_result = {
                    "success": True,
                    "dist": min_total_dist,
                    "sequence": best_route_sequence,
                    "full_path": best_full_path,
                    "start": start_node,
                    "end": end_node,
                    "stops": stops
                }
            else:
                st.session_state.route_result = {"success": False}

        # --- TAMPILKAN HASIL DARI SESSION STATE (AGAR TIDAK HILANG SAAT RERUN) ---
        if st.session_state.route_result:
            result = st.session_state.route_result
            
            if result["success"]:
                with col_input:
                    st.success("✅ Rute Optimal Ditemukan!")
                    total_liter = result["dist"] / konsumsi_bbm
                    total_biaya = total_liter * harga_bbm
                    waktu_menit = (result["dist"] / kecepatan) * 60
                    
                    c1, c2 = st.columns(2)
                    c1.metric("Jarak", f"{result['dist']} Km")
                    c1.metric("Waktu", f"{int(waktu_menit)} Min")
                    c2.metric("BBM", f"{total_liter:.1f} L")
                    c2.metric("Biaya", f"Rp {int(total_biaya):,}")
                    
                    st.markdown("---")
                    st.markdown("### 🔄 Urutan Kunjungan:")
                    for i, node in enumerate(result["sequence"]):
                        icon = "🏁" if i == len(result["sequence"])-1 else "➡️"
                        if i == 0: icon = "🏠"
                        st.write(f"{icon} **{node}**")

                with col_map:
                    center_lat, center_lon = koordinat[result["start"]]
                    m = folium.Map(location=[center_lat, center_lon], zoom_start=11)
                    
                    path_coords = [koordinat[nama] for nama in result["full_path"]]
                    folium.PolyLine(locations=path_coords, color="blue", weight=5, opacity=0.8).add_to(m)
                    
                    for nama, coord in koordinat.items():
                        color = "lightgray"; icon = "info-sign"; popup = nama
                        
                        if nama == result["start"]:
                            color = "green"; icon = "play"
                        elif nama == result["end"]:
                            color = "red"; icon = "flag"
                        elif nama in result["stops"]:
                            try:
                                urutan = result["sequence"].index(nama)
                                color = "orange"; icon = "star"
                                popup = f"{nama} (Urutan: {urutan})"
                            except: pass
                        
                        if nama in result["full_path"] or nama in koordinat:
                            folium.Marker(coord, popup=popup, icon=folium.Icon(color=color, icon=icon)).add_to(m)
                    
                    st_folium(m, width=800, height=500)
            else:
                st.error("❌ Jalur tidak ditemukan! Cek apakah ada jalan yang terputus.")

    # --- MENU 2: MANAJEMEN (BOS) ---
    elif menu == "Manajemen Jalur (Bos)":
        st.title("🛠️ Manajemen Database")
        tab1, tab2, tab3 = st.tabs(["➕ Tambah Node", "🛣️ Tambah Edge", "📂 Data JSON"])
        
        with tab1:
            with st.form("add_node"):
                name = st.text_input("Nama Lokasi Baru")
                lat = st.number_input("Latitude", value=-8.2, format="%.4f")
                lon = st.number_input("Longitude", value=113.6, format="%.4f")
                if st.form_submit_button("Simpan"):
                    if name and name not in data['nodes']:
                        data['nodes'][name] = {"lat": lat, "lon": lon}
                        save_data(data)
                        st.success("Tersimpan!")
                        st.rerun()
                    else: st.error("Nama invalid/duplikat.")
        
        with tab2:
            with st.form("add_edge"):
                loks = sorted(list(koordinat.keys()))
                f_node = st.selectbox("Dari", loks)
                t_node = st.selectbox("Ke", loks)
                w = st.number_input("Jarak (KM)", min_value=1)
                if st.form_submit_button("Simpan"):
                    if f_node != t_node:
                        exists = any(((e['from']==f_node and e['to']==t_node) or (e['from']==t_node and e['to']==f_node)) for e in data['edges'])
                        if not exists:
                            data['edges'].append({"from": f_node, "to": t_node, "weight": w})
                            save_data(data)
                            st.success("Tersimpan!")
                            st.rerun()
                        else: st.warning("Sudah ada.")
                    else: st.error("Titik sama.")
        
        with tab3:
            st.json(data)

if st.session_state.logged_in:
    main_app()
else:
    login_page()