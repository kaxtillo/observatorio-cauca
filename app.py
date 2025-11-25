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
    
    # --- 1. DEFINICIÓN DE MAPAS DE COLUMNAS ---
    mapa_hembras = {
        'AFTOSA_BOVINOS_HEMBRAS_MENORES_A_3_MESES': '0-3 meses',
        'AFTOSA_BOVINOS_HEMBRAS_MENORES_DE_3_A_8_MESES': '3-8 meses',
        'AFTOSA_BOVINOS_DE_8_A_12_MESES': '8-12 meses',
        'AFTOSA_BOVINOS_HEMBRAS_1___2_AÑOS': '1-2 años',
        'AFTOSA_BOVINOS_HEMBRAS_2___3_AÑOS': '2-3 años',
        'AFTOSA_BOVINOS_HEMBRAS_3___5_AÑOS': '3-5 años',
        'AFTOSA_BOVINOS_HEMBRAS_MAYORES_A_5_AÑOS': '> 5 años'
    }

    mapa_machos = {
        'AFTOSA_BOVINOS_MACHOS_MENORES_A_3_MESES': '< 3 meses', 
        'AFTOSA_BOVINOS_MACHOS_3_HASTA_8_MESES': '3-8 meses',
        'AFTOSA_BOVINOS_MACHOS_8_HASTA_12_MESES': '8-12 meses',
        'AFTOSA_BOVINOS_TERNEROS_MENORES_A_1_AÑO': 'Terneros < 1 año',
        'AFTOSA_BOVINOS_MACHOS_1___2_AÑOS': '1-2 años',
        'AFTOSA_BOVINOS_MACHOS_2___3_AÑOS': '2-3 años',
        'AFTOSA_BOVINOS_MACHOS_MAYORES_A_3_AÑOS': '> 3 años'
    }

    # --- 2. LISTA MAESTRA DE ORDENAMIENTO (De menor a mayor edad) ---
    # Esta lista define el orden exacto en que aparecerán las barras
    orden_cronologico = [
        '0-3 meses', '< 3 meses',
        '3-8 meses',
        '8-12 meses', 'Terneros < 1 año',
        '1-2 años',
        '2-3 años',
        '3-5 años', '> 3 años',
        '> 5 años'
    ]

    # Listas para construir el DataFrame
    datos_edad = []
    datos_sexo = []
    datos_poblacion = []

    # Procesar Hembras
    for col_name, etiqueta in mapa_hembras.items():
        if col_name in df_filtered.columns:
            total = df_filtered[col_name].sum()
            datos_edad.append(etiqueta)
            datos_sexo.append('Hembra')
            datos_poblacion.append(total)

    # Procesar Machos
    for col_name, etiqueta in mapa_machos.items():
        if col_name in df_filtered.columns:
            total = df_filtered[col_name].sum()
            if total >= 0: 
                datos_edad.append(etiqueta)
                datos_sexo.append('Macho')
                datos_poblacion.append(total)

    # Crear el DataFrame
    piramide_df = pd.DataFrame({
        'Edad': datos_edad,
        'Sexo': datos_sexo,
        'Poblacion': datos_poblacion
    })

    # --- 3. APLICAR EL ORDENAMIENTO ---
    # Convertimos la columna 'Edad' a un tipo Categórico con orden definido
    # Filtramos la lista maestra para usar solo las categorías que existen en los datos actuales
    categorias_existentes = [x for x in orden_cronologico if x in piramide_df['Edad'].unique()]
    
    piramide_df['Edad'] = pd.Categorical(
        piramide_df['Edad'], 
        categories=categorias_existentes, 
        ordered=True
    )
    
    # Ordenamos el DataFrame según esa categoría
    piramide_df = piramide_df.sort_values('Edad')

    # Asignar valores negativos a Machos
    # Usamos .copy() explícito para evitar Warnings de Pandas
    piramide_df_plot = piramide_df.copy()
    piramide_df_plot.loc[piramide_df_plot['Sexo'] == 'Macho', 'Poblacion'] *= -1
    
    # --- 4. GRAFICAR ---
    fig_piramide = go.Figure()
    
    # Trazo Hembras
    df_h = piramide_df_plot[piramide_df_plot['Sexo'] == 'Hembra']
    fig_piramide.add_trace(go.Bar(
        y=df_h['Edad'], x=df_h['Poblacion'],
        orientation='h', name='Hembras', marker_color='#E91E63'
    ))
    
    # Trazo Machos
    df_m = piramide_df_plot[piramide_df_plot['Sexo'] == 'Macho']
    fig_piramide.add_trace(go.Bar(
        y=df_m['Edad'], x=df_m['Poblacion'],
        orientation='h', name='Machos', marker_color='#2196F3'
    ))
    
    # Calcular máximo para centrar el gráfico
    max_val = piramide_df_plot['Poblacion'].abs().max()
    if pd.isna(max_val) or max_val == 0: max_val = 100

    fig_piramide.update_layout(
        title='Pirámide de Edad y Sexo (Ordenada por edad)',
        barmode='relative',
        xaxis=dict(
            title='Población',
            range=[-max_val*1.1, max_val*1.1] 
        ),
        # Esto asegura que Plotly respete el orden categórico que definimos
        yaxis=dict(type='category'),
        height=600,
        bargap=0.1
    )
    st.plotly_chart(fig_piramide, use_container_width=True)
    
    st.markdown("---")
    st.subheader("2. Distribución de Población Bovina por Municipio")
    
    # Gráfico de Barras Municipios
    top_munis = df_filtered.groupby('MUNICIPIO')['TOTAL_BOVINOS'].sum().sort_values(ascending=False)
    top_munis_df = top_munis.reset_index(name='Población Bovina') 
    
    fig_bar = px.bar(
        top_munis_df, 
        x='Población Bovina', 
        y='MUNICIPIO', 
        orientation='h', 
        color='Población Bovina',
        color_continuous_scale='Viridis'
    )
    fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, height=600)
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
