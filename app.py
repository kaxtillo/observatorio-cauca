import streamlit as st
import pandas as pd
import plotly.express as px
from streamlit_folium import st_folium
import folium
from folium.plugins import HeatMap

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Observatorio Epidemiológico Cauca", layout="wide", page_icon="🐄")

st.title("🐄 Observatorio de Vigilancia Vacunación - Cauca - 2022")
st.markdown("Análisis de datos de vacunación bovina - Ciclo I 2022")

# 2. CARGA DE DATOS (Con caché para velocidad)
@st.cache_data
def load_data():
    # Asegúrate de que el nombre del archivo coincida
    df = pd.read_csv('ARCHIVO PLANO CAUCA 1-2022 (2).csv', delimiter=';', encoding='latin1')
    
    # Limpieza básica
    df['LATITUD'] = df['LATITUD'].astype(str).str.replace(',', '.').astype(float)
    df['LONGITUD'] = df['LONGITUD'].astype(str).str.replace(',', '.').astype(float)
    
    # Calcular Total Bovinos
    cols_bovinos = [c for c in df.columns if 'AFTOSA_BOVINOS' in c and '_AÑO' not in c]
    df[cols_bovinos] = df[cols_bovinos].fillna(0)
    df['TOTAL_BOVINOS'] = df[cols_bovinos].sum(axis=1)
    
    # Filtrar coordenadas válidas
    df = df[(df['LATITUD'] > 0) & (df['LONGITUD'] < 0)]
    
    return df

try:
    df = load_data()
except Exception as e:
    st.error(f"Error cargando datos: {e}")
    st.stop()

# 3. BARRA LATERAL (FILTROS)
st.sidebar.header("Filtros de Visualización")
municipio_filter = st.sidebar.multiselect(
    "Seleccionar Municipio:",
    options=df['MUNICIPIO'].unique(),
    default=df['MUNICIPIO'].unique()[:3] # Por defecto selecciona los 3 primeros
)

# Aplicar filtro
if municipio_filter:
    df_filtered = df[df['MUNICIPIO'].isin(municipio_filter)]
else:
    df_filtered = df

# 4. KPIs (INDICADORES CLAVE)
col1, col2, col3 = st.columns(3)
col1.metric("Total Predios Filtrados", f"{len(df_filtered):,}")
col2.metric("Población Bovina", f"{int(df_filtered['TOTAL_BOVINOS'].sum()):,}")
promedio = df_filtered['TOTAL_BOVINOS'].mean()
col3.metric("Promedio Animales/Predio", f"{promedio:.1f}")

# 5. PESTAÑAS DE ANÁLISIS
tab1, tab2, tab3 = st.tabs(["🗺️ Mapas Interactivos", "📊 Demografía y Vocación", "🚨 Detección de Anomalías"])

with tab1:
    st.header("Distribución Geoespacial")
    col_map1, col_map2 = st.columns(2)
    
    with col_map1:
        st.subheader("Mapa de Calor (Densidad)")
        # Mapa Folium
        m = folium.Map(location=[df_filtered['LATITUD'].mean(), df_filtered['LONGITUD'].mean()], zoom_start=9)
        heat_data = df_filtered[['LATITUD', 'LONGITUD']].values.tolist()
        HeatMap(heat_data, radius=10).add_to(m)
        st_folium(m, height=500, use_container_width=True)
        
    with col_map2:
        st.subheader("Distribución por Tamaño del Hato")
        # Mapa Plotly
        fig_scatter = px.scatter_map(
            df_filtered, lat="LATITUD", lon="LONGITUD", color="MUNICIPIO", size="TOTAL_BOVINOS",
            zoom=8, height=500
        )
        fig_scatter.update_layout(map_style="open-street-map")
        st.plotly_chart(fig_scatter, use_container_width=True)

with tab2:
    st.header("Estructura del Hato Ganadero")
    
    # Gráfico de Barras Municipios
    top_munis = df_filtered.groupby('MUNICIPIO')['TOTAL_BOVINOS'].sum().sort_values(ascending=False).head(15)
    fig_bar = px.bar(top_munis, orientation='h', title="Top Municipios por Población")
    st.plotly_chart(fig_bar, use_container_width=True)

with tab3:
    st.header("Vigilancia: Predios con Cero Bovinos")
    # Filtrar errores
    df_error = df_filtered[df_filtered['TOTAL_BOVINOS'] == 0]
    st.warning(f"Se encontraron {len(df_error)} predios con registro pero con 0 animales.")
    
    if not df_error.empty:
        fig_error = px.scatter_map(
            df_error, lat="LATITUD", lon="LONGITUD", color_discrete_sequence=["red"],
            zoom=9, height=500, title="Ubicación de Registros Anómalos (0 Animales)"
        )
        fig_error.update_layout(map_style="open-street-map")
        st.plotly_chart(fig_error, use_container_width=True)
        
        with st.expander("Ver tabla de datos anómalos"):
            st.dataframe(df_error[['MUNICIPIO', 'VEREDA', 'GANADERO', 'NOMBRE_PREDIO']])

# Pie de página
st.markdown("---")
st.markdown("© 2024 Observatorio Epidemiológico - Desarrollado con Python y Streamlit")
