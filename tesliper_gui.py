from tkinter import *
from tkinter.ttk import *

root = Tk()
root.title("Tesliper")
n = Notebook(root)

f1 = Frame(n)
f2 = Frame(n)
f3 = Frame(n)

n.add(f1, text='One')
n.add(f2, text='Two')
n.add(f3, text='Tree')
Button(f1, text='Exit', command=root.destroy).pack(padx=100, pady=100)
n.pack()

root.mainloop()
