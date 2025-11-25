import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
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
    st.header("Análisis de la Estructura del Hato Ganadero")
    
    st.subheader("1. Pirámide Poblacional Bovina (Edad y Sexo)")
    
    # 1. Preparación de datos para la Pirámide
    
    # Definir las columnas de población y las etiquetas de edad
    cols_hemb = [c for c in df_filtered.columns if 'AFTOSA_BOVINOS_HEMBRAS' in c]
    cols_mach = [c for c in df_filtered.columns if 'AFTOSA_BOVINOS_MACHOS' in c and '_MENORES_A_3_MESES' not in c and '_3_HASTA_8_MESES' not in c and '_8_HASTA_12_MESES' not in c]
    
    # Etiquetas de Edad y Reordenamiento
    age_labels = [
        "Menores a 3 meses (H)", "3 a 8 meses (H)", "8 a 12 meses (H)",
        "1 a 2 años (H)", "2 a 3 años (H)", "3 a 5 años (H)", "Mayores a 5 años (H)",
        "Terneros < 1 año (M)", "1 a 2 años (M)", "2 a 3 años (M)", "Mayores a 3 años (M)"
    ]
    
    # La columna 'TOTAL_BOVINOS_MACHOS_MENORES_A_1_AÑO' es una suma para el lado macho.
    # En este dataset en particular, las etiquetas de macho son más simplificadas,
    # por lo que las agruparemos para coincidir con el número de categorías del lado hembra.
    
    # Crear un DataFrame simplificado para la pirámide
    data_hemb = df_filtered[cols_hemb].sum()
    data_mach = df_filtered[cols_mach].sum()
    
    # Reorganizar los datos en un formato de pirámide
    piramide_df = pd.DataFrame({
        'Edad': [
            "0-3 meses", "3-8 meses", "8-12 meses", 
            "1-2 años", "2-3 años", "3-5 años", "5+ años",
            "Terneros < 1 año", "1-2 años", "2-3 años", "3+ años"
        ],
        'Sexo': ['Hembra'] * len(cols_hemb) + ['Macho'] * len(cols_mach),
        'Poblacion': pd.concat([data_hemb, data_mach])
    })
    
    # Asignar valores negativos a Machos para la visualización de pirámide
    piramide_df.loc[piramide_df['Sexo'] == 'Macho', 'Poblacion'] = piramide_df['Poblacion'] * -1
    
    # Generar Pirámide (usando go.Figure ya que px.bar requiere un truco más complejo)
    fig_piramide = go.Figure()
    
    # Hembras (Positivo)
    fig_piramide.add_trace(go.Bar(
        y=piramide_df[piramide_df['Sexo'] == 'Hembra']['Edad'].tolist(),
        x=piramide_df[piramide_df['Sexo'] == 'Hembra']['Poblacion'].tolist(),
        orientation='h',
        name='Hembras',
        marker_color='#FF88AA' # Rosa
    ))
    
    # Machos (Negativo)
    fig_piramide.add_trace(go.Bar(
        y=piramide_df[piramide_df['Sexo'] == 'Macho']['Edad'].tolist(),
        x=piramide_df[piramide_df['Sexo'] == 'Macho']['Poblacion'].tolist(),
        orientation='h',
        name='Machos',
        marker_color='#0088FF' # Azul
    ))
    
    # Configuración de layout
    fig_piramide.update_layout(
        title='Pirámide de Edad y Sexo del Hato',
        barmode='relative',
        xaxis=dict(
            tickvals=[-1000, -500, 0, 500, 1000], # Ajusta estos valores al rango real de tu población
            ticktext=['1K', '500', '0', '500', '1K'], # Etiquetas (simétricas)
            title='Población',
            range=[-max(piramide_df['Poblacion'].abs())*1.1, max(piramide_df['Poblacion'].abs())*1.1] # Rango dinámico
        ),
        height=600
    )
    st.plotly_chart(fig_piramide, use_container_width=True)
    
    st.markdown("---")
    st.subheader("2. Distribución de Población Bovina por Municipio")
    
    # Gráfico de Barras Municipios (El código que ya tenías)
    top_munis = df_filtered.groupby('MUNICIPIO')['TOTAL_BOVINOS'].sum().sort_values(ascending=False)
    # Convertimos a DataFrame para que Plotly funcione bien con la columna 'índice'
    top_munis_df = top_munis.reset_index(name='Población Bovina') 
    
    fig_bar = px.bar(
        top_munis_df, 
        x='Población Bovina', 
        y='MUNICIPIO', 
        orientation='h', 
        title="Top Municipios por Población Bovina",
        color='Población Bovina',
        color_continuous_scale=px.colors.sequential.Viridis
    )
    fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
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
