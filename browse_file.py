import tkinter as tk
from tkinter import filedialog


def browse_file():
    # Open the file explorer dialog
    file_path = filedialog.askopenfilename(
        title="Select a File",
        filetypes=(("Excel files", "*.xls;*.xlsx"), ("CSV files", "*.csv"), ("All files", "*.*"))
    )

    # Do something with the selected file path
    if file_path:
        label_path.config(text=f"Selected: {file_path}")
        # You can pass this 'file_path' variable to your analysis function here


# 1. Set up the main window
root = tk.Tk()
root.title("File Browser")
root.geometry("450x150")

# 2. Create the Browse Button
# The 'command' parameter links the button click to the browse_file function
browse_button = tk.Button(root, text="Browse for File...", command=browse_file)
browse_button.pack(pady=20)

# 3. Create a label to display the chosen file path
label_path = tk.Label(root, text="No file selected")
label_path.pack()

# 4. Run the application
root.mainloop()