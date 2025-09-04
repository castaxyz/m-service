import streamlit as st
import datetime
import os
import sqlite3
from abc import ABC, abstractmethod
from typing import List

#
# 1. Abstracción del Reproductor de Música (Music Player)
#
class IMusicPlayer(ABC):
    """Interfaz para un reproductor de música."""
    @abstractmethod
    def play(self, song_title: str):
        pass

class SpotifyPlayer(IMusicPlayer):
    """Implementación concreta para un reproductor de Spotify."""
    def play(self, song_title: str):
        st.info(f"Reproduciendo: **{song_title}** en Spotify...")

#
# 2. Abstracción del Repositorio de Historial (History Repository)
#
class IHistoryRepository(ABC):
    """Interfaz para un repositorio de historial de reproducciones."""
    @abstractmethod
    def save_playback(self, song_title: str):
        pass

    @abstractmethod
    def get_history(self) -> List[str]:
        pass

class SqlHistoryRepository(IHistoryRepository):
    """Implementación concreta para un repositorio de historial basado en SQLite."""
    def __init__(self, db_name="playback_history.db"):
        self.conn = sqlite3.connect(db_name)
        self._create_table()

    def _create_table(self):
        cursor = self.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY,
                song_title TEXT NOT NULL,
                timestamp TEXT NOT NULL
            )
        """)
        self.conn.commit()

    def save_playback(self, song_title: str):
        cursor = self.conn.cursor()
        timestamp = datetime.datetime.now().isoformat()
        cursor.execute("INSERT INTO history (song_title, timestamp) VALUES (?, ?)", (song_title, timestamp))
        self.conn.commit()
        st.success("Historial de reproducción guardado.")

    def get_history(self) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT song_title, timestamp FROM history ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        return [f"'{row[0]}' - {row[1]}" for row in rows]

#
# 3. Abstracción del Logger (Logger)
#
class ILogger(ABC):
    """Interfaz para un servicio de registro de logs.."""
    @abstractmethod
    def log(self, message: str):
        pass

class FileLogger(ILogger):
    """Implementación concreta para registrar logs en un archivo de texto."""
    def __init__(self, file_path="app_logs.txt"):
        self.file_path = file_path
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                f.write("--- Log de la Aplicación de Música ---\n") 

    def log(self, message: str):
        with open(self.file_path, "a") as f:
            f.write(f"[{datetime.datetime.now()}] {message}\n")
        st.info(f"Log guardado en '{self.file_path}'")

#
# Módulos de Alto Nivel
#
class MusicService:
    """Módulo de alto nivel que depende de abstracciones, no de implementaciones."""
    def __init__(self, player: IMusicPlayer, history_repo: IHistoryRepository, logger: ILogger):
        self.player = player
        self.history_repo = history_repo
        self.logger = logger

    def play_song(self, song_title: str):
        try:
            self.logger.log(f"Iniciando la reproducción de la canción: {song_title}")
            self.player.play(song_title)
            self.history_repo.save_playback(song_title)
            self.logger.log(f"Reproducción de '{song_title}' completada y registrada.")
        except Exception as e:
            self.logger.log(f"Error al reproducir la canción: {e}")
            st.error(f"Ocurrió un error: {e}")

    def get_playback_history(self) -> List[str]:
        return self.history_repo.get_history()

#
# Configuración e Interfaz de Streamlit
#
st.set_page_config(layout="wide")

st.markdown("""
<style>
.main-header {
    font-size: 2.5em;
    font-weight: bold;
    text-align: center;
    color: #1DB954;
    padding-bottom: 20px;
}
.stButton>button {
    background-color: #1DB954;
    color: white;
    font-weight: bold;
    border-radius: 25px;
    border: none;
    padding: 10px 24px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    transition: all 0.2s ease-in-out;
}
.stButton>button:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 8px rgba(0,0,0,0.2);
}
.stTabs [data-baseweb="tab-list"] {
    gap: 16px;
}
.stTabs [data-baseweb="tab"] {
    font-size: 1.1em;
    font-weight: bold;
    color: #B3B3B3;
}
.stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: #1DB954;
}
.stTabs [data-baseweb="tab-panel"] {
    padding-top: 20px;
}
.stExpander {
    border-radius: 10px;
}
.stExpander>div>div {
    border-radius: 10px;
    border: 1px solid #1DB954;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🎧 Aplicación de Música 🎧</h1>', unsafe_allow_html=True)

# Inicializar las dependencias
player_implementation = SpotifyPlayer()
history_implementation = SqlHistoryRepository()
logger_implementation = FileLogger()

# Inyectar las dependencias en el servicio de música (Inversión de Dependencias)
music_app = MusicService(player=player_implementation,
                         history_repo=history_implementation,
                         logger=logger_implementation)

tab1, tab2 = st.tabs(["Reproductor", "Historial y Logs"])

with tab1:
    st.subheader("Reproducir una canción")
    song_title = st.text_input("Ingresa el título de la canción:", "Bohemian Rhapsody")

    if st.button("Reproducir"):
        music_app.play_song(song_title)

with tab2:
    st.subheader("Historial de Reproducciones")
    history = music_app.get_playback_history()
    
    if history:
        st.success("Historial cargado. Aquí están tus últimas reproducciones:")
        for record in history:
            st.text(record)
    else:
        st.warning("Aún no has reproducido ninguna canción.")

    st.subheader("Logs de la Aplicación")
    if os.path.exists(logger_implementation.file_path):
        with open(logger_implementation.file_path, "r") as f:
            logs = f.read()
        st.text_area("Logs del Sistema", logs, height=300)
    else:
        st.info("El archivo de logs aún no se ha creado.")

    if st.button("Limpiar historial"):
        try:
            os.remove(history_implementation.db_name)
            st.success("Historial de reproducciones borrado.")
            st.rerun()
        except FileNotFoundError:
            st.warning("El historial ya estaba vacío.")

    if st.button("Limpiar logs"):
        try:
            os.remove(logger_implementation.file_path)
            st.success("Logs borrados.")
            st.rerun()
        except FileNotFoundError:
            st.warning("El archivo de logs no existe.")