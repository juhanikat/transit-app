from network import Network
from ui import UI

if __name__ == "__main__":
    ui = UI(Network())
    ui.start_ui()
