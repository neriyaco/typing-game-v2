import tkinter as tk
from . import Protocol
from .Message import Message
from socket import timeout
from threading import Thread
from . import WordAPI
import time
from json import dumps


ERROR = -1
OK = 0
ASK_NICKNAME = 1
GAME_STARTED = 2
WORD = 3
ROUND_END = 4
MATCH_END = 5


ENCODING = "utf-8"


class Client:
    def __init__(self, client_id, sock, address):
        self.id = client_id
        self._socket = sock
        self.address = address
        self.player = None
        self.on_disconnect = lambda _: None
        self._connected = True

    @property
    def connected(self):
        return self._connected

    def disconnect(self):
        try:
            self._socket.close()
        except (timeout, ConnectionError, OSError):
            ...
        self._connected = False
        self.on_disconnect(self)

    def send(self, msg):
        if not self._connected:
            return
        data = (msg.to_json()).encode(ENCODING) # + b"XPO.NETWORKING.BUFFER.END_BYTE"
        print(data)
        try:
            self._socket.send(data)
        except (timeout, ConnectionError, OSError):
            self.disconnect()

    def get(self):
        if not self._connected:
            return None
        try:
            data = self._socket.recv(4096)
        except (timeout, ConnectionError, OSError):
            self.disconnect()
            return None
        print(f"[{self.address[0]}:{self.address[1]}] {data}")
        result = Message.from_json(data.decode(ENCODING))
        print(result)
        return result


class Player:
    def __init__(self, name, client):
        self.name = name
        self.client = client
        self.stats = {}

    def kick(self):
        self.send_error(Protocol.MSG_PLAYER_KICKED_BY_ADMIN, "You got kicked from the server by the admin.")

    def ban_name(self):
        self.send_error(Protocol.MSG_NICKNAME_IS_BANNED, "")

    def ban_ip(self):
        self.send_error(Protocol.MSG_IP_IS_BANNED, "")

    def send_error(self, error, message):
        self.client.send(Message(ERROR, f"{error}:{message}"))

    def send_ok(self, message):
        self.client.send(Message(OK, message))

    def ask_nickname(self):
        self.client.send(Message(ASK_NICKNAME, "Please choose a nickname."))

    def send_game_started(self, num_words):
        self.client.send(Message(GAME_STARTED, str(num_words)))

    def send_word(self, word):
        self.client.send(Message(WORD, f"{word}"))

    def round_end(self, winner):
        self.client.send(Message(ROUND_END, winner))

    def match_end(self, winner):
        self.client.send(Message(MATCH_END, winner))

    def send_game_terminated(self):
        self.send_error(Protocol.MSG_GAME_TERMINATED, "The game terminated")

    def __repr__(self):
        if not self.name:
            return f"Unnamed Player [{self.client.address[0]}:{self.client.address[1]}]"
        else:
            return self.name


class ClientManager:
    def __init__(self):
        self._clients = []
        self.banned_ips = []
        self.banned_names = []

    @property
    def players(self):
        players = []
        for c in self._clients:
            players.append(c.player)
        return players

    def init_app(self, app):
        app.ui.player_list.bind("<<ListboxSelect>>", lambda *_: self.on_select_player(app))

        app.ui.create_player_menu_item("Details", lambda: self.show_player_info(app.ui.get_selected_player()))
        app.ui.create_player_menu_item("Action/Kick", lambda: self.kick_player(app.ui.get_selected_player()))
        app.ui.create_player_menu_item("Action/Ban/By Name", lambda: self.ban_player_name(app.ui.get_selected_player()))
        app.ui.create_player_menu_item("Action/Ban/By IP", lambda: self.ban_player_ip(app.ui.get_selected_player()))

        app.ui.create_menu_item("Client/Details", lambda: self.show_player_info(app.ui.get_selected_player()))
        app.ui.create_menu_item("Client/Kick", lambda: self.kick_player(app.ui.get_selected_player()))
        app.ui.create_menu_item("Client/Ban/By Name", lambda: self.ban_player_name(app.ui.get_selected_player()))
        app.ui.create_menu_item("Client/Ban/By IP", lambda: self.ban_player_ip(app.ui.get_selected_player()))

        app.ui.create_menu_separator("Ban")
        app.ui.create_menu_item("Ban/Show Banned IPs", self.show_banned_ips)
        app.ui.create_menu_item("Ban/Show Banned Names", self.show_banned_names)

        app.ui.player_info_callback = self.show_player_info

        self.on_select_player(app)

    def show_banned_ips(self):
        window = tk.Toplevel()
        window.wm_title("Banned IPs")
        ip_list = tk.Listbox(window, selectbackground="black", selectforeground="white", fg="black")
        ip_list.pack_configure(side=tk.TOP, fill=tk.BOTH, expand=True)
        for ip in self.banned_ips:
            ip_list.insert(tk.END, ip)

        def remove_ip_ban(*_):
            try:
                self.remove_ip_ban(ip_list.selection_get())
                ip_list.delete(ip_list.curselection())
            except tk.TclError:
                ...
        ip_list.bind("<Delete>", remove_ip_ban)

    def show_banned_names(self):
        window = tk.Toplevel()
        window.wm_title("Banned Names")
        name_list = tk.Listbox(window, selectbackground="black", selectforeground="white", fg="black")
        name_list.pack_configure(side=tk.TOP, fill=tk.BOTH, expand=True)
        for name in self.banned_names:
            name_list.insert(tk.END, name)

        def remove_name_ban(*_):
            try:
                self.remove_name_ban(name_list.selection_get())
                name_list.delete(name_list.curselection())
            except tk.TclError:
                ...

        name_list.bind("<Delete>", remove_name_ban)

    def show_player_info(self, player):
        ...

    def kick_player(self, player):
        player.kick()
        player.client.disconnect()

    def ban_player_name(self, player):
        self.kick_player(player)
        self.banned_names.append(player.name)

    def ban_player_ip(self, player):
        self.kick_player(player)
        self.banned_ips.append(player.client.address[0])

    def is_ip_banned(self, ip):
        return ip in self.banned_ips

    def is_name_banned(self, name):
        return name in self.banned_names

    def remove_ip_ban(self, ip):
        self.banned_ips.remove(ip)

    def remove_name_ban(self, name):
        self.banned_names.remove(name)

    def add_client(self, app, client_data):
        client, address = client_data
        ip, port = address
        app.ui.log(f"[{ip}:{port}] Incoming connection")
        client_obj = Client(len(self._clients), client, address)
        client_obj.on_disconnect = lambda c: self.on_client_disconnect(c, app)
        if self.is_ip_banned(ip):
            app.ui.log(f"[{ip}:{port}] IP \"{ip}\" is banned.")
            client_obj.send(Message(ERROR, f"{Protocol.MSG_IP_IS_BANNED}:Your IP is banned."))
            client_obj.disconnect()
        else:
            client_obj.player = Player(None, client_obj)
            app.ui.add_player(client_obj.player)
            self._clients.append(client_obj)
            client_obj.player.ask_nickname()
            return client_obj

    def find_player_index(self, name):
        for i, client in enumerate(self._clients):
            if str(client.player) == name:
                return i

    def on_client_disconnect(self, client, app):
        player = client.player
        if player is not None:
            app.ui.remove_player_by_name(str(player))
            idx = self.find_player_index(str(player))
            if idx:
                self._clients.pop(idx)
            app.ui.log_info(f"{client.player} left!")
        if not len(self._clients):
            app.game_server.stop_game()
            app.join_server.start()

    def on_select_player(self, app):
        selected = app.ui.get_selected_player()
        if not selected:
            state = tk.DISABLED
        else:
            state = tk.NORMAL
        app.ui.get_menu("Client").entryconfig("Details", state=state)
        app.ui.get_menu("Client").entryconfig("Kick", state=state)
        app.ui.get_menu("Client").entryconfig("Ban", state=state)

        app.ui.get_player_menu("").entryconfig("Details", state=state)
        app.ui.get_player_menu("").entryconfig("Action", state=state)

    # def send_all(self, msg: str):
    #     """
    #     msg is a string but it can formatted for each player.
    #     ie "Hello, {PLAYER_NAME}! "
    #
    #     available formats:
    #     PLAYER_NAME,
    #     PLAYER_IP
    #
    #     :param msg: the message to send
    #     """
    #     for client in self._clients:
    #         if client:
    #             client.send(msg.format_map({"PLAYER_NAME": client.player.name, "PLAYER_IP": client.address[0]}))

    def validate_clients(self, app, auto_kick=True):
        new_clients = []
        if auto_kick:
            for client in self._clients:
                if not client.player.name:
                    client.disconnect()
                else:
                    new_clients.append(client)
        else:
            for client in self._clients:
                if not client.player.name:
                    client.player.ask_nickname()

    def add_player(self, player, name):
        if self.find_player_index(name):
            player.send_error(Protocol.MSG_NICKNAME_ALREADY_TAKEN, f"The nickname \'{name}\' was already taken")
        elif name in self.banned_names:
            player.send_error(Protocol.MSG_NICKNAME_IS_BANNED, f"The nickname \'{name}\' is banned.")
        elif not name.isalnum():
            player.send_error(Protocol.MSG_NICKNAME_NOT_VALID, f"Invalid nickname (only characters and number s allowed)")
        else:
            if player.name:
                player.send_error(Protocol.MSG_PLAYER_ALREADY_HAS_NAME, "")
            else:
                player.name = name

    # def client_join(self, app, client_obj):
    #     ip, port = client_obj.address
    #     self._waiting_confirmation.append(client_obj)
    #     client_obj.send(Protocol.MSG_ASK_CLIENT_FOR_NICKNAME)
    #     nickname = Protocol.get_nickname(client_obj.get())
    #     result = False
    #     if self.is_name_banned(nickname):
    #         app.ui.log(f"[{ip}:{port}] Name \"{nickname}\" is banned.")
    #         client_obj.send(Protocol.MSG_NICKNAME_IS_BANNED)
    #     elif self.find_player(nickname) is not None:
    #         client_obj.send(Protocol.MSG_NICKNAME_ALREADY_TAKEN)
    #         app.ui.log(f"[{ip}:{port}] Client tried to join with a name taken.")
    #     elif not nickname.strip():
    #         client_obj.send(Protocol.MSG_NICKNAME_NOT_VALID)
    #         app.ui.log(f"[{ip}:{port}] Client tried to join with a an invalid name.")
    #     else:
    #         client_obj.player = Player(nickname, client_obj)
    #         self._clients.append(client_obj)
    #         client_obj.send(Protocol.MSG_WELCOME_TO_GAME)
    #         app.ui.add_player(client_obj.player.name)
    #         app.ui.log_info(f"[{ip}:{port}] {client_obj.player.name} joined!")
    #         result = True
    #     return result

    def refresh_clients(self):
        for player in self.players:
            player.send_ok("REFRESH")

    def foreach_player(self, func):
        for client in self._clients:
            func(client.player)

    def foreach_client(self, func):
        for client in self._clients:
            func(client)

    def handle_all_once(self, handler, *args, **kwargs):
        handler = handler if handler else lambda *_: None

        def handle_client(handler_, client_, *args_, **kwargs_):
            handler_(client_, client_.get(), *args_, **kwargs_)

        for client in self._clients:
            Thread(target=handle_client, args=(client, client.get(), *args), kwargs=kwargs).start()

    def handle_all_forever(self, handler, *args, **kwargs):
        handler = handler if handler else lambda *_: None

        def handle_client(handler_, client_, *args_, **kwargs_):
            while not handler_(client_, client_.get(), *args_, **kwargs_):
                ...

        for client in self._clients:
            Thread(target=handle_client, args=(handler, client, *args), kwargs=kwargs).start()
