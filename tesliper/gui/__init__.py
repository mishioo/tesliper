from tesliper.gui.main import TesliperApp

def build():
    import tkinter as tk
    root = tk.Tk()
    root.title("Tesliper")
    app = TesliperApp(root)
    app.logger.info(
        'Welcome to Tesliper:\n'
        'Theoretical Spectroscopist Little Helper!'
    )
    return root

def run():

    root = build()
    return root.mainloop()