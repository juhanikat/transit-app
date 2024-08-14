# How to install

1. Install poetry [https://python-poetry.org/docs/#installation] and Python [https://www.python.org/downloads/] on your computer
2. Download this program by clicking the green Code button in the top right of the github page and selecting "Download ZIP"
3. Unzip the folder somewhere on your computer
4. Open terminal and navigate to the program folder (`cd location-of-the-folder`)
5. Enter `poetry install` if this is your first time using the program
6. Enter `poetry run python src/main.py`
7. Done!

# How to use

Start road drawing by clicking anywhere on the map, then click somewhere else to finish the road. Note that you can not start or end a road right next to an existing one. \
You can connect roads by clicking the blue points at either end of any road. \
Press middle mouse button (or C) to place a calculation point. Place another calculation point somewhere else to highlight the shortest path between them.

# Testing

Run ``poetry run pytest`.