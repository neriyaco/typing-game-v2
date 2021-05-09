from socket import AF_INET, SOCK_STREAM, socket, timeout, gethostbyname, gaierror
from tkinter.constants import TRUE
from .ClientManager import ClientManager
import tkinter.filedialog as tk_fd
import tkinter.messagebox as tk_mb
import tkinter.simpledialog as tk_sd
import tkinter as tk
from pathlib import Path
from . import Protocol
from threading import Thread
from . import WordAPI
import time


HERE = Path(__file__).parent.resolve()
BANNED_IPS_FILENAME = str(HERE / "IPs.ban")
BANNED_NAMES_FILENAME = str(HERE / "Names.ban")


class JoinServer:
    def __init__(self):
        self._ip = self._port = None
        self._socket = None
        self._running = False

    @property
    def ip(self):
        return self._ip

    @property
    def port(self):
        return self._port

    @property
    def running(self):
        return self._running

    def setup(self, ip: str, port: int):
        self._ip = ip
        self._port = port

    def init(self):
        if self._ip is None:
            raise ValueError("ip can not be None")
        if self._port is None:
            raise ValueError("port can not be None")
        self._socket = socket(AF_INET, SOCK_STREAM)
        self._socket.settimeout(1)
        try:
            self._socket.bind((self._ip, self._port))
        except OSError as e:
            tk_mb.showerror("Error", e.strerror)
            return False
        self._socket.listen(10)
        return True

    def start(self, app):
        if app.game_server.running:
            return tk_mb.showerror("Join Server Error", "Join Server can\'t run while Game Server is running.")
        if not self.init():
            return app.ui.log_error("Couldn\'t start Join Server")
        app.ui.log(f"Join Server started on {self.ip}:{self.port}")
        app.ui.get_menu("Join Server").entryconfig("Start", state=tk.DISABLED)
        app.ui.get_menu("Join Server").entryconfig("Close", state=tk.NORMAL)
        self._running = True
        Thread(target=self.accept_loop, args=[lambda c: Thread(target=app.game_server.on_client_join, args=(app, c)).start()]).start()

    def init_app(self, app):
        app.ui.create_menu_item("Join Server/Start", lambda: self.start(app))
        app.ui.create_menu_item("Join Server/Close", lambda: self.stop(app))
        app.ui.get_menu("Join Server").entryconfig("Close", state=tk.DISABLED)

    def accept(self):
        return self._socket.accept()

    def accept_loop(self, on_connect=None):
        if on_connect is None:
            def empty(*_, **__):
                ...

            on_connect = empty
        while self._running:
            try:
                result = self.accept()
            except timeout:
                continue
            except OSError as e:
                break
            if result:
                on_connect(result)

    def stop(self, app):
        self._running = False
        self._socket.close()
        app.ui.log("Join Server stopped")
        app.ui.get_menu("Join Server").entryconfig("Start", state=tk.NORMAL)
        app.ui.get_menu("Join Server").entryconfig("Close", state=tk.DISABLED)


class GameServer:
    def __init__(self):
        self.client_manager = ClientManager()
        self._app = None
        self._running = False
        self.commands = {
            1: self._set_nickname,
            3: self._handle_word
        }
        self.winner = None
        self.current_word = None
        self.current_round = None
        self.round_count = None
        Thread(target=self.refresh_loop).start()

    def refresh_loop(self):
        while True:
            self.client_manager.refresh_clients()
            time.sleep(5)

    def _set_nickname(self, player, nickname: str):
        self.client_manager.add_player(player, nickname)

    def _handle_word(self, player, word: str):
        if word != self.current_word:
            return
        if self.winner is None:
            self.winner = player.name

    @property
    def running(self):
        return self._running

    def load_ips_from_file(self, path, app=None):
        app = app if app else self._app
        if app:
            app.ui.log(f"Loading IPs from \"{path}\"...")
        try:
            with open(path) as banned_ips_src:
                banned_ips = banned_ips_src.readlines()
        except (FileNotFoundError, IOError):
            if app:
                app.ui.log_warning(f"Could not find file \"{path}\". No IPs loaded.")
            banned_ips = []
        for ip in banned_ips:
            try:
                ip = gethostbyname(ip)
                self.client_manager.banned_ips.append(ip)
            except gaierror:
                if app:
                    app.ui.log_warning(f"\"{ip}\" is not a valid IP. Skipping..")

    def load_names_from_file(self, path, app=None):
        app = app if app else self._app
        if app:
            app.ui.log(f"Loading names from \"{path}\"...")
        try:
            with open(path) as banned_names_src:
                banned_names = banned_names_src.readlines()
        except (FileNotFoundError, IOError):
            if app:
                app.ui.log_warning(f"Could not find file \"{path}\". No Names loaded.")
            banned_names = []
        self.client_manager.banned_names.extend(banned_names)

    def init_app(self, app):
        self._app = app
        app.ui.create_menu_item("Ban/Load/IPs", self.load_ips_list)
        app.ui.create_menu_item("Ban/Load/Nicknames", self.load_names_list)
        app.ui.create_menu_item("Ban/Save/IPs", self.save_ips_list)
        app.ui.create_menu_item("Ban/Save/Nicknames", self.save_names_list)
        app.ui.create_menu_item("Game/Start", lambda: self.start_game(app))
        app.ui.create_menu_item("Game/Pause", lambda: self.pause_game(app))
        app.ui.create_menu_item("Game/Resume", lambda: self.resume_game(app))
        app.ui.create_menu_item("Game/Stop", lambda: self.stop_game(app))
        app.ui.create_menu_separator("Game")
        app.ui.create_menu_item("Game/Settings", self.open_settings_window)

        app.ui.get_menu("Game").entryconfig("Pause", state=tk.DISABLED)
        app.ui.get_menu("Game").entryconfig("Resume", state=tk.DISABLED)
        app.ui.get_menu("Game").entryconfig("Stop", state=tk.DISABLED)

        self.load_ips_from_file(BANNED_IPS_FILENAME, app)
        self.load_names_from_file(BANNED_NAMES_FILENAME, app)

        self.client_manager.init_app(app)
        app.ui.command_callback = self.cmd

    def start_game(self, app):
        if app.join_server.running:
            if not tk_mb.askyesno("Game Server Error", "Game can\'t start while Join Server is running. \nClose Join Server now?"):
                return
            app.join_server.stop(app)
        app.ui.log_info("Starting game...")
        self._running = True
        app.ui.get_menu("Game").entryconfig("Start", state=tk.DISABLED)
        app.ui.get_menu("Game").entryconfig("Pause", state=tk.NORMAL)
        app.ui.get_menu("Game").entryconfig("Stop", state=tk.NORMAL)
        self.client_manager.refresh_clients()
        self.client_manager.validate_clients(app, True)
        Thread(target=self.game).start()

    def pause_game(self, app):
        app.ui.log_info("Game paused.")
        app.ui.get_menu("Game").entryconfig("Resume", state=tk.NORMAL)
        app.ui.get_menu("Game").entryconfig("Pause", state=tk.DISABLED)
        # self.client_manager.send_all(Protocol.MSG_PAUSE_GAME)

    def resume_game(self, app):
        app.ui.log_info("Game resumed")
        app.ui.get_menu("Game").entryconfig("Resume", state=tk.DISABLED)
        app.ui.get_menu("Game").entryconfig("Pause", state=tk.NORMAL)
        # self.client_manager.send_all(Protocol.MSG_RESUME_GAME)

    def stop_game(self, app):
        app.ui.log_info("Game terminated.")
        app.ui.get_menu("Game").entryconfig("Start", state=tk.NORMAL)
        app.ui.get_menu("Game").entryconfig("Resume", state=tk.DISABLED)
        app.ui.get_menu("Game").entryconfig("Pause", state=tk.DISABLED)
        app.ui.get_menu("Game").entryconfig("Stop", state=tk.DISABLED)
        self.stop()

    def load_ips_list(self):
        file_path = tk_fd.askopenfilename(
            title="Open Banned IPs File",
            filetypes=[
                ("Ban List", "*.ban"),
                ("All", "*.*")
            ]

        )
        self.load_ips_from_file(file_path)

    def load_names_list(self):
        file_path = tk_fd.askopenfilename(
            title="Open Banned Names File",
            filetypes=[
                ("Ban List", "*.ban"),
                ("All", "*.*")
            ]
        )
        self.load_names_from_file(file_path)

    def save_ips_list(self):
        file_path = tk_fd.asksaveasfilename(
            title="Save Banned IPs File",
            filetypes=[
                ("Ban List", "*.ban"),
                ("All", "*.*")
            ]
        )
        try:
            with open(file_path, "w") as out:
                out.writelines(self.client_manager.banned_ips)
        except FileNotFoundError:
            ...

    def save_names_list(self):
        file_path = tk_fd.asksaveasfilename(
            title="Save Banned Namess File",
            filetypes=[
                ("Ban List", "*.ban"),
                ("All", "*.*")
            ]
        )
        try:
            with open(file_path, "w") as out:
                out.writelines(self.client_manager.banned_names)
        except FileNotFoundError:
            ...

    def open_settings_window(self):
        ...

    def on_client_join(self, app, client_data):
        client = self.client_manager.add_client(app, client_data)
        if client:
            Thread(target=self.client_handler, args=(client, app)).start()

    def stop(self, run_join_server: bool = True):
        self._running = False
        if run_join_server:
            self._app.join_server.start(self._app)
        self.client_manager.foreach_player(lambda p: p.send_game_terminated())

    def request_handler(self, client, request, app):
        if not request:
            client.disconnect()
        player = client.player
        try:
            if request:
                cmd = self.commands[request.command]
                cmd(player, request.data)
        except KeyError:
            ...
        app.ui.log(f"[{client.address[0]}:{client.address[1]}] [{player.name}] Request \"{request}\".")

    def client_handler(self, client, app):
        while client.connected:
            self.request_handler(client, client.get(), app)

    def cmd(self, cmd: str):
        if not self.current_word:
            self._app.ui.log_error("Game not running")
        else:
            if cmd == self.current_word:
                self.winner = "[Hosting Server]"

    def game(self):
        # self.round_count = tk_sd.askinteger("Round Count", "How many rounds this game?")
        # print(self.round_count)
        try:
            self.round_count = 7
            words = WordAPI.get_words(self.round_count)
            round_winners = []
            self.client_manager.foreach_player(lambda p: p.send_game_started(self.round_count))
            time.sleep(0.5)
            for i, word in enumerate(words):
                if not self._running:
                    return
                self.winner = None
                self.current_word = word
                self.current_round = i
                self._app.ui.log_info(f"Round [{i}/{self.round_count}] \"{word}\"")
                self.client_manager.foreach_player(lambda p: p.send_word(word))
                while not self.winner:
                    time.sleep(0.5)
                round_winners.append(self.winner)
                self._app.ui.log_info(f"Winner [{i}/{self.round_count}] {self.winner}")
                self.client_manager.foreach_player(lambda p: p.round_end(self.winner))
            top_score = 0
            winners = []
            for player in self.client_manager.players:
                score = round_winners.count(player.name)
                if score > top_score:
                    top_score = score
                    winners.clear()
                    winners.append(player.name)
                elif score == top_score:
                    winners.append(player.name)
            time.sleep(0.5)
            self.client_manager.foreach_player(lambda p: p.match_end(",".join(winners)))
            self.winner = self.current_word = self.current_round = None
        except Exception as e:
            self._app.ui.log_error(e)
        self.stop_game(self._app)
