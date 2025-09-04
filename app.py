import streamlit as st
import datetime
import os
import sqlite3
import mysql.connector
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
        st.warning("Nota: La reproducci\u00F3n real de m\u00FAsica con la API de Spotify requiere el SDK de reproducci\u00F3n web, lo que es m\u00E1s complejo de implementar en un solo archivo de Streamlit.")

class LocalMusicPlayer(IMusicPlayer):
    """Nueva implementaci\u00F3n que reproduce un archivo de audio local."""
    def play(self, song_title: str):
        st.info(f"Reproduciendo: **{song_title}** desde un archivo de audio local...")
        # Simular la reproducci\u00F3n con un archivo de audio de ejemplo.
        st.audio("https://cdn.pixabay.com/audio/2023/12/16/audio_f5f5492d3b.mp3", format="audio/mp3", start_time=0, loop=False)

#
# 2. Abstracci\u00F3n del Repositorio de Historial (History Repository)
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
    """
    Implementaci\u00F3n concreta para un repositorio de historial basado en SQLite.
    (Mantenido como referencia, ya que es la implementaci\u00F3n original).
    """
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
        st.success("Historial de reproducci\u00F3n guardado.")

    def get_history(self) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT song_title, timestamp FROM history ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        return [f"'{row[0]}' - {row[1]}" for row in rows]

class MySqlHistoryRepository(IHistoryRepository):
    """Implementaci\u00F3n concreta para un repositorio de historial basado en MySQL."""
    def __init__(self, host, user, password, database):
        try:
            self.conn = mysql.connector.connect(
                host=host,
                user=user,
                password=password,
                database=database
            )
            st.success("Conexi\u00F3n a MySQL exitosa.")
            self._create_table()
        except mysql.connector.Error as err:
            st.error(f"Error al conectar a MySQL: {err}")
            self.conn = None

    def _create_table(self):
        if self.conn:
            cursor = self.conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    song_title VARCHAR(255) NOT NULL,
                    timestamp DATETIME NOT NULL
                )
            """)
            self.conn.commit()

    def save_playback(self, song_title: str):
        if self.conn:
            cursor = self.conn.cursor()
            timestamp = datetime.datetime.now()
            cursor.execute("INSERT INTO history (song_title, timestamp) VALUES (%s, %s)", (song_title, timestamp))
            self.conn.commit()
            st.success("Historial de reproducci\u00F3n guardado en MySQL.")
        else:
            st.error("No se pudo guardar el historial: no hay conexi\u00F3n a la base de datos.")

    def get_history(self) -> List[str]:
        if self.conn:
            cursor = self.conn.cursor()
            cursor.execute("SELECT song_title, timestamp FROM history ORDER BY timestamp DESC")
            rows = cursor.fetchall()
            return [f"'{row[0]}' - {row[1].strftime('%Y-%m-%d %H:%M:%S')}" for row in rows]
        return []

#
# 3. Abstracci\u00F3n del Logger (Logger)
#
class ILogger(ABC):
    """Interfaz para un servicio de registro de logs."""
    @abstractmethod
    def log(self, message: str):
        pass

class FileLogger(ILogger):
    """Implementaci\u00F3n concreta para registrar logs en un archivo de texto."""
    def __init__(self, file_path="app_logs.txt"):
        self.file_path = file_path
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                f.write("--- Log de la Aplicaci\u00F3n de M\u00FAsica ---\n")

    def log(self, message: str):
        with open(self.file_path, "a") as f:
            f.write(f"[{datetime.datetime.now()}] {message}\n")
        st.info(f"Log guardado en '{self.file_path}'")

#
# M\u00F3dulos de Alto Nivel
#
class MusicService:
    """M\u00F3dulo de alto nivel que depende de abstracciones, no de implementaciones."""
    def __init__(self, player: IMusicPlayer, history_repo: IHistoryRepository, logger: ILogger):
        self.player = player
        self.history_repo = history_repo
        self.logger = logger

    def play_song(self, song_title: str):
        try:
            self.logger.log(f"Iniciando la reproducci\u00F3n de la canci\u00F3n: {song_title}")
            self.player.play(song_title)
            self.history_repo.save_playback(song_title)
            self.logger.log(f"Reproducci\u00F3n de '{song_title}' completada y registrada.")
        except Exception as e:
            self.logger.log(f"Error al reproducir la canci\u00F3n: {e}")
            st.error(f"Ocurri\u00F3 un error: {e}")

    def get_playback_history(self) -> List[str]:
        return self.history_repo.get_history()

#
# Configuraci\u00F3n e Interfaz de Streamlit
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

st.markdown('<h1 class="main-header">\ud83c\udfa7 Aplicaci\u00F3n de M\u00FAsica \ud83c\udfa7</h1>', unsafe_allow_html=True)

# Inicializar las dependencias
player_implementation = LocalMusicPlayer()
logger_implementation = FileLogger()

# Aquí puedes elegir qué implementación de repositorio usar
use_mysql = st.sidebar.checkbox("Usar MySQL en lugar de SQLite", value=False)

if use_mysql:
    # Lee las credenciales de los secretos de Streamlit
    host = st.secrets["db_credentials"]["host"]
    user = st.secrets["db_credentials"]["user"]
    password = st.secrets["db_credentials"]["password"]
    database = st.secrets["db_credentials"]["database"]
    
    history_implementation = MySqlHistoryRepository(host=host, user=user, password=password, database=database)
else:
    history_implementation = SqlHistoryRepository()
    
# Inyectar las dependencias en el servicio de m\u00FAsica (Inversi\u00F3n de Dependencias)
music_app = MusicService(player=player_implementation,
                         history_repo=history_implementation,
                         logger=logger_implementation)

tab1, tab2 = st.tabs(["Reproductor", "Historial y Logs"])

with tab1:
    st.subheader("Reproducir una canci\u00F3n")
    song_title = st.text_input("Ingresa el t\u00EDtulo de la canci\u00F3n:", "Bohemian Rhapsody")

    if st.button("Reproducir"):
        music_app.play_song(song_title)

with tab2:
    st.subheader("Historial de Reproducciones")
    history = music_app.get_playback_history()
    
    if history:
        st.success("Historial cargado. Aqu\u00ED est\u00E1n tus \u00FAltimas reproducciones:")
        for record in history:
            st.text(record)
    else:
        st.warning("A\u00FAn no has reproducido ninguna canci\u00F3n.")

    st.subheader("Logs de la Aplicaci\u00F3n")
    if os.path.exists(logger_implementation.file_path):
        with open(logger_implementation.file_path, "r") as f:
            logs = f.read()
        st.text_area("Logs del Sistema", logs, height=300)
    else:
        st.info("El archivo de logs a\u00FAn no se ha creado.")

    if st.button("Limpiar historial"):
        try:
            if isinstance(history_implementation, SqlHistoryRepository):
                os.remove(history_implementation.db_name)
                st.success("Historial de reproducciones borrado.")
                st.rerun()
            else:
                st.error("No se puede borrar el historial de MySQL desde la aplicaci\u00F3n.")
        except FileNotFoundError:
            st.warning("El historial ya estaba vac\u00EDo.")

    if st.button("Limpiar logs"):
        try:
            os.remove(logger_implementation.file_path)
            st.success("Logs borrados.")
            st.rerun()
        except FileNotFoundError:
            st.warning("El archivo de logs no existe.")
