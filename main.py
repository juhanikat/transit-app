from src.transit_app.network import Network
from src.transit_app.ui import UI

if __name__ == "__main__":
    ui = UI(Network())
    ui.start_ui()
