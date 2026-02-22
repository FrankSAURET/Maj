import tkinter as tk

root = tk.Tk()

img = tk.PhotoImage(file="../assets/upgradable.png")  # PNG transparent

canvas = tk.Canvas(root, width=200, height=200, bg="#333333")
canvas.pack()

canvas.create_image(100, 100, image=img)

root.mainloop()
