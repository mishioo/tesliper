from .main import TesliperApp

def build():

    return TesliperApp()

def run():

    app = build()
    return app.mainloop()