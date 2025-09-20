import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk
from nse_fetcher import NSEFetcher
from data_processor import DataProcessor
from plotter import create_oi_plot
import os

class OIPlotterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Nifty Open Interest Plotter")
        self.geometry("800x600")

        self.fetcher = NSEFetcher()

        self.create_widgets()

    def create_widgets(self):
        # Frame for controls
        control_frame = ttk.Frame(self, padding="10")
        control_frame.pack(side="top", fill="x")

        # Expiry selection
        ttk.Label(control_frame, text="Expiry:").pack(side="left", padx=5)
        self.expiry_var = tk.StringVar(value="weekly")
        ttk.Radiobutton(control_frame, text="Weekly", variable=self.expiry_var, value="weekly").pack(side="left")
        ttk.Radiobutton(control_frame, text="Monthly", variable=self.expiry_var, value="monthly").pack(side="left")

        # Number of strikes
        ttk.Label(control_frame, text="Strikes around ATM:").pack(side="left", padx=5)
        self.strikes_var = tk.StringVar(value="10")
        ttk.Entry(control_frame, textvariable=self.strikes_var, width=5).pack(side="left")

        # ITM only
        self.itm_var = tk.BooleanVar()
        ttk.Checkbutton(control_frame, text="ITM Only", variable=self.itm_var).pack(side="left", padx=5)

        # Generate button
        ttk.Button(control_frame, text="Generate Plot", command=self.generate_plot).pack(side="left", padx=5)

        # Canvas for plot
        self.plot_canvas = tk.Canvas(self, bg="white")
        self.plot_canvas.pack(side="bottom", fill="both", expand=True)

    def generate_plot(self):
        try:
            # Fetch data
            raw_data = self.fetcher.fetch_option_chain('NIFTY')
            if not raw_data:
                messagebox.showerror("Error", "Failed to fetch data from NSE.")
                return

            processor = DataProcessor(raw_data)

            # Get expiry date
            expiry_type = self.expiry_var.get()
            if expiry_type == "weekly":
                expiry_date = processor.get_current_week_expiry()
            else:
                expiry_date = processor.get_current_month_expiry()

            if not expiry_date:
                messagebox.showerror("Error", "Could not determine expiry date.")
                return

            # Get other parameters
            num_strikes = int(self.strikes_var.get())
            itm_only = self.itm_var.get()

            # Process data
            processed_data = processor.get_processed_option_chain(
                expiry_date, num_strikes=num_strikes, itm_only=itm_only
            )

            if not processed_data:
                messagebox.showinfo("Info", "No data to plot for the selected criteria.")
                return

            # Create plot
            underlying_value = processor.get_underlying_value()
            plot_path = create_oi_plot(processed_data, expiry_date, underlying_value)

            if plot_path and os.path.exists(plot_path):
                self.display_plot(plot_path)
            else:
                messagebox.showerror("Error", "Failed to create plot.")

        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def display_plot(self, plot_path):
        # Clear previous plot
        self.plot_canvas.delete("all")

        # Open and display the new plot
        img = Image.open(plot_path)
        # Resize image to fit canvas while maintaining aspect ratio
        canvas_width = self.plot_canvas.winfo_width()
        canvas_height = self.plot_canvas.winfo_height()

        if canvas_width < 10 or canvas_height < 10: # Canvas not yet rendered
            self.after(100, lambda: self.display_plot(plot_path))
            return

        img_ratio = img.width / img.height
        canvas_ratio = canvas_width / canvas_height

        if img_ratio > canvas_ratio:
            new_width = canvas_width
            new_height = int(new_width / img_ratio)
        else:
            new_height = canvas_height
            new_width = int(new_height * img_ratio)

        resized_img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        self.plot_image = ImageTk.PhotoImage(resized_img)
        self.plot_canvas.create_image(canvas_width/2, canvas_height/2, image=self.plot_image)


if __name__ == "__main__":
    app = OIPlotterApp()
    app.mainloop()
