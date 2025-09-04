import streamlit as st
import datetime
import os
import sqlite3
import sqlalchemy
from abc import ABC, abstractmethod
from typing import List
from sqlalchemy import create_engine, text
from urllib.parse import urlparse

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
        st.warning("Oops, el servicio de Spotify no está disponible en este momento.")

class LocalMusicPlayer(IMusicPlayer):
    """Nueva implementación que reproduce un archivo de audio local."""
    def play(self, song_title: str):
        st.info(f"Reproduciendo: **{song_title}** desde un archivo de audio local...")
        # Simular la reproducción con un archivo de audio de ejemplo.
        st.audio("https://cdn.pixabay.com/audio/2023/12/16/audio_f5f5492d3b.mp3", format="audio/mp3", start_time=0, loop=False)

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
    """
    Implementación concreta para un repositorio de historial basado en SQLite.
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
        st.success("Historial de reproducción guardado.")

    def get_history(self) -> List[str]:
        cursor = self.conn.cursor()
        cursor.execute("SELECT song_title, timestamp FROM history ORDER BY timestamp DESC")
        rows = cursor.fetchall()
        return [f"'{row[0]}' - {row[1]}" for row in rows]

class MySqlHistoryRepository(IHistoryRepository):
    """Implementación concreta para un repositorio de historial basado en MySQL."""
    def __init__(self, url: str):
        self.engine = None
        self.conn = None
        try:
            # Parsear la URL para manejar credenciales con caracteres especiales
            parsed_url = urlparse(url)
            # Reconstruir la URL con el driver pymysql y un formato seguro
            db_url_safe = f"mysql+pymysql://{parsed_url.username}:{parsed_url.password}@{parsed_url.hostname}:{parsed_url.port}{parsed_url.path}"
            
            # Crear engine con SQLAlchemy a partir de la URL
            self.engine = create_engine(db_url_safe)
            self.conn = self.engine.connect()
            self._create_table()
            st.success("Conexión a MySQL exitosa.")
        except Exception as err:
            st.error(f"Error al conectar a MySQL: {err}")

    def _create_table(self):
        """
        Crea la tabla de historial si no existe.
        No la borra para mantener los datos.
        """
        if not self.conn:
            st.error("No se pudo crear la tabla: no hay conexión a la base de datos.")
            return

        query = text("""
            CREATE TABLE IF NOT EXISTS `history` (
                `id` INT AUTO_INCREMENT PRIMARY KEY,
                `song_title` VARCHAR(255) NOT NULL,
                `timestamp` DATETIME NOT NULL
            )
        """)
        try:
            self.conn.execute(query)
            self.conn.commit()
            st.success("Tabla 'history' creada exitosamente o ya existía.")
        except Exception as err:
            st.error(f"Error al crear la tabla: {err}")

    def delete_table(self, table_name: str):
        """Método para eliminar una tabla de la base de datos."""
        if not self.conn:
            st.error("No se pudo eliminar la tabla: no hay conexión a la base de datos.")
            return

        query = text(f"DROP TABLE IF EXISTS `{table_name}`")
        try:
            self.conn.execute(query)
            self.conn.commit()
            st.success(f"Tabla '{table_name}' eliminada exitosamente.")
        except Exception as err:
            st.error(f"Error al eliminar la tabla: {err}")
    
    def save_playback(self, song_title: str):
        if not self.conn:
            st.error("No se pudo guardar el historial: no hay conexión a la base de datos.")
            return

        timestamp = datetime.datetime.now()
        query = text("INSERT INTO history (song_title, timestamp) VALUES (:title, :ts)")
        try:
            self.conn.execute(query, {"title": song_title, "ts": timestamp})
            self.conn.commit()
            st.success("Historial de reproducción guardado en MySQL.")
        except Exception as err:
            st.error(f"Error al guardar el historial: {err}")

    def get_history(self) -> List[str]:
        if not self.conn:
            return []

        query = text("SELECT song_title, timestamp FROM history ORDER BY timestamp DESC")
        try:
            result = self.conn.execute(query)
            # Utiliza un enfoque más seguro para obtener los valores de la fila
            rows = []
            for row in result.all():
                song_title = row.song_title
                timestamp = row.timestamp
                rows.append(f"'{song_title}' - {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
            return rows
        except Exception as err:
            st.error(f"Error al obtener el historial: {err}")
            return []

#
# 3. Abstracción del Logger (Logger)
#
class ILogger(ABC):
    """Interfaz para un servicio de registro de logs."""
    @abstractmethod
    def log(self, message: str):
        pass

class FileLogger(ILogger):
    """Implementación concreta para registrar logs en un archivo de texto."""
    def __init__(self, file_path="app_logs.txt"):
        self.file_path = file_path
        if not os.path.exists(self.file_path):
            with open(self.file_path, 'w') as f:
                f.write(f"--- Log de la Aplicación de Música ---\n")

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

st.markdown('<h1 class="main-header">🎵 Aplicación de Música 🎵</h1>', unsafe_allow_html=True)

# Inicializar las dependencias
logger_implementation = FileLogger()

st.sidebar.title("Configuración")
use_mysql = st.sidebar.checkbox("Usar MySQL en lugar de SQLite", value=False)
player_selection = st.sidebar.radio(
    "Selecciona el Reproductor",
    ("Local", "Spotify (no disponible)")
)

if use_mysql:
    db_url = st.secrets["db_credentials"]["url"]
    history_implementation = MySqlHistoryRepository(url=db_url)
else:
    history_implementation = SqlHistoryRepository()

# Seleccionar la implementación del reproductor en función de la elección del usuario
if player_selection == "Local":
    player_implementation = LocalMusicPlayer()
else:
    player_implementation = SpotifyPlayer()


# Crear la instancia de MusicService para usar en las pestañas
music_app = MusicService(player=player_implementation,
                         history_repo=history_implementation,
                         logger=logger_implementation)


tab1, tab2, tab3 = st.tabs(["Reproductor", "Historial y Logs", "Administrador de DB"])

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

with tab3:
    st.subheader("Eliminar la tabla 'history'")
    st.warning("¡ADVERTENCIA! Esta acción borrará permanentemente todos los datos de historial de canciones.")
    if st.button("Eliminar Tabla 'history'"):
        music_app.history_repo.delete_table("history")
