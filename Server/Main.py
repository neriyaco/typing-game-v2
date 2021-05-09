from Server.ServerUI import ServerUI
from Server.Server import JoinServer, GameServer
from Server import Protocol


class App:
    def __init__(self):
        self.ui: ServerUI = ServerUI()
        self.ui.log("UI Init")
        self.ui.on_quit = self.quit
        self.ui.log("Opening Servers...")
        self.join_server: JoinServer = JoinServer()
        self.game_server: GameServer = GameServer()
        self.ui.log("Done")

        self.ui.log("Initializing Apps")
        self.ui.create_menu_item("File/Exit", self.ui.quit)
        self.ui.init_app(self)
        self.join_server.init_app(self)
        self.game_server.init_app(self)

        self.ui.log("Done")

    def run(self):
        self.join_server.setup("0.0.0.0", 3741)
        self.join_server.start(self)
        self.ui.mainloop()

    def quit(self):
        # self.game_server.client_manager.send_all(Protocol.MSG_SERVER_QUIT)
        self.game_server.client_manager.foreach_client(lambda c: c.disconnect())
        self.join_server.stop(self)
        self.game_server.stop(False)


if __name__ == '__main__':
    app = App()
    app.run()
