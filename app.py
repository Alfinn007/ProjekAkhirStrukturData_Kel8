import streamlit as st
import json
import folium
from streamlit_folium import st_folium 
from modules.graph_algo import TobbacoGraph

st.set_page_config(page_title="Sistem Optimasi Tembakau", layout="wide")
st.title(" Sistem Optimasi Tembakau Jember")
st.markdown("Aplikasi untuk menemukan rute optimal dalam distribusi tembakau menggunakan algoritma Dijkstra.")

@st.cache_data
def load_data():
    try:
        with open('data/data_tembakau.json', 'r') as f: 
            data = json.load(f)
        return data
    except FileNotFoundError:
        return None

data = load_data()
if not data:
    st.error("Data JSON tidak ditemukan di folder data/.")
    st.stop()

graph = TobbacoGraph()
koordinat = {}

for nama, info in data['nodes'].items():
    koordinat[nama] = (info['lat'], info['lon'])

for rute in data['edges']:
    graph.add_edge(rute['from'], rute['to'], rute['weight'])

if 'hasil_path' not in st.session_state:
    st.session_state.hasil_path = None
if 'hasil_jarak' not in st.session_state:
    st.session_state.hasil_jarak = 0

def hitung_rute():
    start = st.session_state.start_lokasi
    end = st.session_state.end_lokasi
    
    if start == end:
        st.toast("Lokasi asal dan tujuan tidak boleh sama!")
        st.session_state.hasil_path = None
    else:
        path, jarak = graph.dijkstra(start, end)
        st.session_state.hasil_path = path
        st.session_state.hasil_jarak = jarak

st.sidebar.header("Pilih Rute")
list_lokasi = sorted(list(koordinat.keys()))
st.sidebar.selectbox("Lokasi Awal", list_lokasi, index=0, key="start_lokasi")
st.sidebar.selectbox("Lokasi Tujuan", list_lokasi, index=1, key="end_lokasi")
st.sidebar.button("Cari Rute Optimal", type="primary", on_click=hitung_rute)

if st.session_state.hasil_path:
    path = st.session_state.hasil_path
    total_jarak = st.session_state.hasil_jarak
    
    col1, col2 = st.columns(2)
    with col1:
        st.success(f" Rute Ditemukan!")
        st.metric("Total Jarak", f"{total_jarak} km")
    with col2:
        st.info(" Jalur:")
        st.write(" ".join(path))

    st.subheader("Peta Rute Optimal")
    
    with st.container():
        center_lat, center_lon = koordinat[path[0]]
        m = folium.Map(location=[center_lat, center_lon], zoom_start=12)
        for nama, coord in koordinat.items():
            color = "gray"
            icon_type = "info-sign"
            
            if nama in path:
                color = "orange"
                if nama == path[0]:
                    color = "green"; icon_type = "play"
                elif nama == path[-1]:
                    color = "red"; icon_type = "stop"
                    
            folium.Marker(location=coord, popup=nama, tooltip=nama, icon=folium.Icon(color=color, icon=icon_type)).add_to(m)

        path_coords = [koordinat[nama] for nama in path]
        folium.PolyLine(locations=path_coords, color="blue", weight=5, opacity=0.8, tooltip=f"Jarak: {total_jarak}km").add_to(m)

        st_folium(m, width=800, height=500, returned_objects=[])

elif st.session_state.get('start_lokasi') != st.session_state.get('end_lokasi'):
    st.info("Klik tombol 'Cari Rute Optimal' di samping untuk mulai.")

st.markdown("---")
with st.expander("Data Lokasi dan Rute"):
    st.json(data)