from .main import TesliperApp


def build():
    return TesliperApp()


def run(app=None):
    app = build() if app is None else app
    return app.mainloop()
