import pandas as pd
import numpy as np
import os
import math
import contextlib
import io
import tkinter as tk
from tkinter import filedialog, scrolledtext
from PIL import ImageGrab  # Required for screenshots
import ctypes


def log_msg(txt_widget, msg):
    """Helper function to print text into the GUI text box instead of the console."""
    txt_widget.insert(tk.END, msg + "\n")
    txt_widget.see(tk.END)  # Auto-scroll to the bottom
    txt_widget.update()


def capture_screen(txt_widget, output_path):
    """Captures a screenshot of the entire Tkinter window, including the title bar."""
    window = txt_widget.winfo_toplevel()
    window.update_idletasks()  # Ensure all window geometry is fully loaded

    # winfo_x() and winfo_y() get the outer edges of the window (including title bar)
    x = window.winfo_x()
    y = window.winfo_y()

    # Calculate how thick the title bar and borders are
    left_border_thickness = window.winfo_rootx() - x
    title_bar_height = window.winfo_rooty() - y

    # Calculate the bottom-right corner based on the inner width plus the outer borders
    x1 = window.winfo_rootx() + window.winfo_width() + left_border_thickness

    # The bottom border is usually the same thickness as the left border
    y1 = window.winfo_rooty() + window.winfo_height() + left_border_thickness

    try:
        # Take screenshot using the new, wider outer bounds
        screenshot = ImageGrab.grab(bbox=(x, y, x1, y1))
        img_path = output_path.replace('.csv', '.png')
        screenshot.save(img_path)
        log_msg(txt_widget, f"Screenshot saved to:\n-> {img_path}\n")
    except Exception as e:
        log_msg(txt_widget, f"[!] Failed to save screenshot: {e}\n")

def run_analysis(file_path, txt_widget):
    """The core math and pandas analysis, updated to output to the GUI."""
    # Define the constants provided for all orders
    a_ex, b_ex = 0.15, 0.0075  # Exclusive Order
    a_sp, b_sp = 0.25, 0.0075  # Special Order
    a_o1, b_o1 = 0.50, 0.0130  # Order 1
    a_o2, b_o2 = 1.00, 0.0230  # Order 2

    log_msg(txt_widget, f"Loading file: {os.path.basename(file_path)}...")

    try:
        # Check if it's an Excel file or CSV
        _, file_extension = os.path.splitext(file_path)

        if file_extension.lower() in ['.xls', '.xlsx']:
            # Safely absorb the 'xlrd' OLE2 warnings into RAM
            with contextlib.redirect_stdout(io.StringIO()):
                summary_df = pd.read_excel(file_path, nrows=15, header=None)
                df = pd.read_excel(file_path, skiprows=24)

            # Find the row with 'Standard Deviation'
            std_row = summary_df[summary_df[0] == 'Standard Deviation']
            if not std_row.empty:
                val = std_row.iloc[0, 1]
                if pd.isna(val) and summary_df.shape[1] > 2:
                    val = std_row.iloc[0, 2]
                report_std = float(val)
            else:
                report_std = None

            # Find the row with 'Arithmetic Mean'
            mean_row = summary_df[summary_df[0] == 'Arithmetic Mean']
            if not mean_row.empty:
                val = mean_row.iloc[0, 1]
                if pd.isna(val) and summary_df.shape[1] > 2:
                    val = mean_row.iloc[0, 2]
                report_mean = float(val)
            else:
                report_mean = None

        else:
            # EXTRACT FROM CSV REPORT SUMMARY
            summary_df = pd.read_csv(file_path, nrows=15, header=None, on_bad_lines='skip')

            std_row = summary_df[summary_df[0] == 'Standard Deviation']
            report_std = float(std_row.iloc[0, 2]) if not std_row.empty else None

            mean_row = summary_df[summary_df[0] == 'Arithmetic Mean']
            report_mean = float(mean_row.iloc[0, 2]) if not mean_row.empty else None

            # EXTRACT FROM CSV DATA TABLE
            df = pd.read_csv(file_path, skiprows=24, on_bad_lines='skip')

        # =========================================================
        # PRE-CALCULATE THE GLOBAL 95% CONFIDENCE LEVEL & AVERAGES
        # =========================================================
        if report_std is not None and report_mean is not None:
            confidence_95 = abs(report_mean) + (1.96 * report_std)
        else:
            confidence_95 = None

        z1_avg = df['Z 1'].mean()
        z2_avg = df['Z 2'].mean()
        overall_avg = (z1_avg + z2_avg) / 2

        tvu_exclusive = math.sqrt((a_ex ** 2) + ((b_ex * overall_avg) ** 2))
        tvu_special = math.sqrt((a_sp ** 2) + ((b_sp * overall_avg) ** 2))
        tvu_order1 = math.sqrt((a_o1 ** 2) + ((b_o1 * overall_avg) ** 2))
        tvu_order2 = math.sqrt((a_o2 ** 2) + ((b_o2 * overall_avg) ** 2))

        # Determine Global Achieved Order
        if confidence_95 is not None:
            if confidence_95 < tvu_exclusive:
                achieved_order = "Exclusive Order"
            elif confidence_95 < tvu_special:
                achieved_order = "Special Order"
            elif confidence_95 < tvu_order1:
                achieved_order = "Order 1"
            elif confidence_95 < tvu_order2:
                achieved_order = "Order 2"
            else:
                achieved_order = "Fails Order 2 Standards"
        else:
            achieved_order = "Unknown (Standard Deviation or Mean missing)"

        # =========================================================
        # CALCULATE TVU PER LINE (ROW) AND EVALUATE ACHIEVED ORDER
        # =========================================================
        df['Average Depth'] = (df['Z 1'] + df['Z 2']) / 2

        df['TVU Exclusive'] = np.sqrt(a_ex ** 2 + (b_ex * df['Average Depth']) ** 2)
        df['TVU Special'] = np.sqrt(a_sp ** 2 + (b_sp * df['Average Depth']) ** 2)
        df['TVU Order 1'] = np.sqrt(a_o1 ** 2 + (b_o1 * df['Average Depth']) ** 2)
        df['TVU Order 2'] = np.sqrt(a_o2 ** 2 + (b_o2 * df['Average Depth']) ** 2)

        if confidence_95 is not None:
            conditions = [
                confidence_95 < df['TVU Exclusive'],
                confidence_95 < df['TVU Special'],
                confidence_95 < df['TVU Order 1'],
                confidence_95 < df['TVU Order 2']
            ]
            choices = ['Exclusive Order', 'Special Order', 'Order 1', 'Order 2']
            df['Achieved Order'] = np.select(conditions, choices, default='Fails Order 2 Standards')
        else:
            df['Achieved Order'] = 'Unknown (Std or Mean missing)'

        # =========================================================
        # EXPORT TO CSV (GLOBAL RESULTS HEADER + PER LINE DATA)
        # =========================================================
        raw_name = os.path.basename(file_path)
        name_no_ext = os.path.splitext(raw_name)[0]
        name_no_ext = name_no_ext.replace('.xls', '').replace('.xlsx', '')
        clean_name = name_no_ext.split(' - ')[0]

        output_filename = f"{clean_name}_TVU_Per_Line_Results.csv"
        output_path = os.path.join(os.path.dirname(file_path), output_filename)

        with open(output_path, 'w', newline='') as f:
            f.write("--- RESULTS ---\n")
            f.write(f"Report Summary 'Arithmetic Mean',{report_mean if report_mean is not None else 'Not Found'}\n")
            f.write(f"Report Summary 'Standard Deviation',{report_std if report_std is not None else 'Not Found'}\n")
            f.write(f"95% Confidence Level,{confidence_95 if confidence_95 is not None else 'Not Found'}\n")
            f.write(f"Average Depth,{overall_avg:.4f}\n")
            f.write(f"TVU Limit (Exclusive Order),{tvu_exclusive:.6f}\n")
            f.write(f"TVU Limit (Special Order),{tvu_special:.6f}\n")
            f.write(f"TVU Limit (Order 1),{tvu_order1:.6f}\n")
            f.write(f"TVU Limit (Order 2),{tvu_order2:.6f}\n")
            f.write(f"ACHIEVED NSHS SURVEY STANDARD,{achieved_order.upper()}\n\n")
            f.write("--- PER LINE RESULTS ---\n")

        df.to_csv(output_path, mode='a', index=False)

        # =========================================================
        # DISPLAY THE GLOBAL RESULTS TO THE GUI
        # =========================================================
        log_msg(txt_widget, "\n" + "=" * 55)
        log_msg(txt_widget, "                 FINAL EXTRACTED VALUES")
        log_msg(txt_widget, "=" * 55)

        if report_std is not None and report_mean is not None:
            log_msg(txt_widget, f"Report Summary 'Arithmetic Mean':    {report_mean:.6f}")
            log_msg(txt_widget, f"Report Summary 'Standard Deviation': {report_std:.6f}")
            log_msg(txt_widget, f"95% Confidence Level (|Mean| + Std * 1.96): {confidence_95:.6f}")
        else:
            log_msg(txt_widget, "Report Summary 'Arithmetic Mean':    Not Found")
            log_msg(txt_widget, "Report Summary 'Standard Deviation': Not Found")
            log_msg(txt_widget, "95% Confidence Level:                Not Found")

        log_msg(txt_widget, "-" * 55)
        log_msg(txt_widget, f"Average Depth:        {overall_avg:.4f}")
        log_msg(txt_widget, "-" * 55)
        log_msg(txt_widget, f"TVU Limit (Exclusive Order):        {tvu_exclusive:.6f}")
        log_msg(txt_widget, f"TVU Limit (Special Order):          {tvu_special:.6f}")
        log_msg(txt_widget, f"TVU Limit (Order 1):                {tvu_order1:.6f}")
        log_msg(txt_widget, f"TVU Limit (Order 2):                {tvu_order2:.6f}")
        log_msg(txt_widget, "=" * 55)

        # 1. Create a custom style tag for the text box
        txt_widget.tag_configure("result_style", foreground="red", font=("Consolas", 14, "bold"))

        # 2. Insert the normal text first
        txt_widget.insert(tk.END, "ACHIEVED NSHS SURVEY STANDARD:      ")

        # 3. Insert the achieved_order variable and apply the "result_style" tag to it
        txt_widget.insert(tk.END, f"{achieved_order.upper()}\n", "result_style")

        # 4. Auto-scroll and update (doing manually what log_msg normally does)
        txt_widget.see(tk.END)
        txt_widget.update()

        # 1. Create a custom style tag for the success message
        # Change '12' to whatever size you want, and you can add a color like 'green' or 'blue'
        txt_widget.tag_configure("success_style", font=("Consolas", 10))

        # 2. Insert the success text using the new tag
        success_text = f"\nSUCCESS: Results saved to:\n-> {os.path.dirname(file_path)}\\{output_filename}\n"
        txt_widget.insert(tk.END, success_text, "success_style")

        # 3. Auto-scroll and update the window
        txt_widget.see(tk.END)
        txt_widget.update()

        # Schedule the screenshot to run 500 milliseconds later.
        # This tiny delay ensures the red/bold text has fully rendered on screen first!
        txt_widget.after(500, lambda: capture_screen(txt_widget, output_path))

    except Exception as e:
        log_msg(txt_widget, f"\n[!] AN ERROR OCCURRED:\n{e}\n")

def browse_file(txt_widget):
    """Opens the file explorer and triggers the analysis."""
    file_path = filedialog.askopenfilename(
        title="Select Hypack CrossCheck File",
        filetypes=(("Excel files", "*.xls;*.xlsx"), ("CSV files", "*.csv"), ("All files", "*.*"))
    )

    if file_path:
        txt_widget.delete(1.0, tk.END)  # Clear previous results
        log_msg(txt_widget, f"File selected: {file_path}\n")
        run_analysis(file_path, txt_widget)


def main():
    """Sets up the Tkinter graphical interface."""
    # --- ADD THESE 4 LINES HERE ---

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass  # Just in case it's run on an older version of Windows
    # ------------------------------
    root = tk.Tk()
    root.title("SB Overall NSHS Survey Order Analysis - by LCDR M. ESTROPIA")
    root.geometry("700x850")

    # Title Label
    title_label = tk.Label(root, text="SB Hypack CrossCheck Analyzer", font=("Arial", 14, "bold"))
    title_label.pack(pady=10)

    # Instructions
    instruction_label = tk.Label(root, text="Click below to select a .xls or .csv file generated by Hypack.",
                                 font=("Arial", 10))
    instruction_label.pack(pady=5)

    # Scrolled Text Box (This replaces the terminal/console output)
    txt_output = scrolledtext.ScrolledText(root, width=85, height=30, font=("Consolas", 10))

    # Browse Button (Passes the text box to the browse function)
    browse_btn = tk.Button(root, text="Browse File & Run Analysis", font=("Arial", 11, "bold"),
                           command=lambda: browse_file(txt_output))
    browse_btn.pack(pady=10)

    # Pack the text box last so it sits below the button
    txt_output.pack(padx=15, pady=10)

    # Add a welcome message to the text box
    log_msg(txt_output, "Ready to process files. Waiting for file selection...\n")

    # Version
    version_text = ("Version 2-09102026: Added Absolute Arithmetic Mean to the Confidence Level (95%)"
                    "\nAdded GUI for easy file selection."
                    "\nSaves screen shot and .csv of the result.")
    version_label = tk.Label(root, text=version_text, font=("Arial", 8), justify="left")
    version_label.pack(pady=3)

    # Start the GUI event loop
    root.mainloop()

if __name__ == "__main__":
    main()
