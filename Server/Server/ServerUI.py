from tkinter import *


__version__ = "1.0.0"

WIDGET_CONFIG = {
    "selectbackground": "black",
    "selectforeground": "white",
    "background": "white",
    "foreground": "black"
}

MENU_CONFIG = {
    "activebackground": "black"
}

TAG_ERROR = "error_msg"
TAG_WARNING = "warning_msg"
TAG_INFO = "info_msg"


FONT = "Courier New"
FONT_SIZE = 16


CONSOLE_CONFIG = {
    "font_normal": (FONT, FONT_SIZE),
    "font_bold": (FONT, FONT_SIZE, "bold"),
    "color_info": "#076e05",
    "color_warning": "#d67c15",
    "color_error": "#bf0b0b"
}


class ObjectListbox(Listbox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._objects = []

    def insert(self, index, *elements):
        idx = self.index(index)
        self._objects[idx:idx] = elements
        super().insert(index, elements)

    def delete(self, first, last=None):
        first_idx = self.index(first)
        if not last:
            self._objects.pop(first_idx)
        super().delete(first, last)

    def get(self, first, last=None):
        first_idx = self.index(first)
        if not last:
            return self._objects[first_idx]
        last_idx = self.index(last)
        return self._objects[first_idx:last_idx]

    def refresh(self):
        selection = self.curselection()
        self.delete(0, END)
        for obj in self._objects:
            super().insert(END, obj)
        if selection:
            self.selection_set(*selection)


class MenuManager(Menu):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, **MENU_CONFIG)
        self._sub_menus = {}

    def get_menu(self, name: str):
        if name not in self._sub_menus:
            menu = MenuManager(tearoff=False)
            self._sub_menus[name] = menu
            self.add_cascade(label=name, menu=menu)
        return self._sub_menus[name]

    def get_all(self):
        return self._sub_menus


class ServerUI(Tk):
    def __init__(self):
        super().__init__()

        self.wm_title("Typing Game Server")

        self._main_menu = MenuManager(self, tearoff=False)

        self.configure(menu=self._main_menu)

        self._main_frame = Frame(self)

        self._console = Text(self._main_frame)

        self._console.configure(state=DISABLED)
        self._console.pack_configure(side=RIGHT, fill=BOTH, expand=True)

        self.player_list = ObjectListbox(self._main_frame, width=50)
        self.player_list.pack_configure(side=RIGHT, fill=Y, expand=False)

        self._player_list_context_menu = MenuManager(self.player_list, tearoff=False)

        self._main_frame.pack_configure(side=TOP, fill=BOTH, expand=True)

        self._command_line = Entry(self)
        self._command_line.pack_configure(side=TOP, fill=X)
        self._command_line.bind("<Return>", lambda _: self.execute_command(self._command_line.get()))

        self.bind("<FocusIn>", lambda _=None: self._command_line.focus_set())

        self.command_callback = lambda _: None
        self.player_info_callback = lambda _: None
        self.on_quit = lambda: None

        self.player_list.bind("<Double-Button-1>", lambda _: self.player_info_callback(self.get_selected_player()))
        self.player_list.bind("<Button-3>", lambda _: self._player_list_context_menu.post(*self.winfo_pointerxy()))

        self.apply_theme(WIDGET_CONFIG, MENU_CONFIG, CONSOLE_CONFIG)

        self.wm_protocol("WM_DELETE_WINDOW", self.quit)

        self._app = None

        self.after(500, self.refresh)

    def init_app(self, app):
        self._app = app

    def refresh(self):
        self.player_list.refresh()
        self.after(500, self.refresh)

    def quit(self):
        self.on_quit()
        super().quit()

    def write(self, msg: str, tag: str):
        self._console.configure(state=NORMAL)
        start = self._console.index(INSERT)
        self._console.insert(END, msg)
        end = self._console.index(INSERT)
        self._console.tag_add(tag, start, end)
        self._console.see(END)
        self._console.configure(state=DISABLED)

    def _log(self, *values, sep: str = " ", end: str = "\n", tag):
        self.write(sep.join(map(str, values)) + end, tag)

    def log(self, *values, sep: str = " ", end: str = "\n"):
        self._log(*values, sep=sep, end=end, tag="")

    def log_info(self, *values, sep: str = " ", end: str = "\n"):
        self._log(*values, sep=sep, end=end, tag=TAG_INFO)

    def log_warning(self, *values, sep: str = " ", end: str = "\n"):
        self._log(*values, sep=sep, end=end, tag=TAG_WARNING)

    def log_error(self, *values, sep: str = " ", end: str = "\n"):
        self._log(*values, sep=sep, end=end, tag=TAG_ERROR)

    def execute_command(self, command):
        self.command_callback(command)
        self._command_line.delete(0, END)

    def add_player(self, player):
        self.player_list.insert(END, player)

    def remove_player_by_index(self, index: int):
        self.player_list.delete(index)

    def remove_player_by_name(self, name: str):
        length = self.player_list.index(END)
        for i in range(length):
            if str(self.player_list.get(i)) == name:
                self.player_list.delete(i)
                return

    def get_selected_player(self):
        try:
            return self.player_list.get(self.player_list.curselection())
        except TclError:
            return None

    def get_menu(self, menu: str):
        parts = menu.split("/")
        menu = self._main_menu
        if len(parts) < 1:
            return menu
        for item in parts:
            if not item:
                continue
            menu = menu.get_menu(item)
        return menu

    def create_menu_item(self, menu_item: str, command):
        parts = menu_item.split("/")
        menu_item = parts[-1]
        menu = self.get_menu("/".join(parts[:-1]))
        menu.add_command(label=menu_item, command=command)

    def create_menu_separator(self, menu: str):
        menu = self.get_menu(menu)
        menu.add_separator()

    def get_player_menu(self, menu: str):
        parts = menu.split("/")
        menu = self._player_list_context_menu
        if len(parts) < 1:
            return menu
        for item in parts:
            if not item:
                continue
            menu = menu.get_menu(item)
        return menu

    def create_player_menu_item(self, menu_item: str, command):
        parts = menu_item.split("/")
        menu_item = parts[-1]
        menu = self.get_player_menu("/".join(parts[:-1]))
        menu.add_command(label=menu_item, command=command)

    def create_player_menu_separator(self, menu: str):
        menu = self.get_player_menu(menu)
        menu.add_separator()

    def apply_theme(self, widget_config, menu_config, console_config):
        # widgets
        self._console.configure(widget_config)
        self._command_line.configure(widget_config)
        self.player_list.configure(widget_config)

        # menus
        self._main_menu.configure(menu_config)
        self._player_list_context_menu.configure(menu_config)

        # console
        self._console.configure(font=console_config["font_normal"])
        self._console.tag_configure(TAG_INFO, foreground=console_config["color_info"], font=console_config["font_bold"])
        self._console.tag_configure(TAG_WARNING, foreground=console_config["color_warning"], font=console_config["font_bold"])
        self._console.tag_configure(TAG_ERROR, foreground=console_config["color_error"], font=console_config["font_bold"])


if __name__ == '__main__':
    app = ServerUI()
    app.mainloop()
