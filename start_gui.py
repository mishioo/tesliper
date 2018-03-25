import tkinter as tk
from tesliper import gui_main as gui

if __name__ == '__main__':
    
    root = tk.Tk()
    root.title("Tesliper")
    n = gui.TslrNotebook(root)
    n.logger.info(
        'Welcome to Tesliper:\n'
        'Theoretical Spectroscopist Little Helper!')

    root.mainloop()
