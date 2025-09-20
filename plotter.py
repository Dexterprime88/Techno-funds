import matplotlib.pyplot as plt
import os

def create_oi_plot(processed_data, expiry_date, underlying_value):
    """
    Creates a plot of the open interest for calls and puts.
    Saves the plot to a file and returns the file path.
    """
    if not processed_data:
        return None

    strikes = [item['strike'] for item in processed_data]
    call_oi = [item['call_oi'] for item in processed_data]
    put_oi = [item['put_oi'] for item in processed_data]

    plt.figure(figsize=(12, 6))
    plt.plot(strikes, call_oi, label='Call OI', color='red', marker='o')
    plt.plot(strikes, put_oi, label='Put OI', color='green', marker='o')

    # Add a vertical line for the underlying value
    plt.axvline(x=underlying_value, color='blue', linestyle='--', label=f'Underlying: {underlying_value:.2f}')

    plt.xlabel('Strike Price')
    plt.ylabel('Open Interest')
    plt.title(f'Nifty Open Interest for {expiry_date}')
    plt.legend()
    plt.grid(True)

    # Ensure the plot directory exists
    plot_dir = 'plots'
    if not os.path.exists(plot_dir):
        os.makedirs(plot_dir)

    # Save the plot to a file
    plot_path = os.path.join(plot_dir, 'oi_plot.png')
    plt.savefig(plot_path)
    plt.close()  # Close the plot to free up memory

    return plot_path

if __name__ == '__main__':
    # Test the plotting function with some sample data
    sample_data = [
        {'strike': 25200, 'call_oi': 34102, 'put_oi': 117241},
        {'strike': 25250, 'call_oi': 21805, 'put_oi': 79832},
        {'strike': 25300, 'call_oi': 85169, 'put_oi': 169243},
        {'strike': 25350, 'call_oi': 85938, 'put_oi': 73099},
        {'strike': 25400, 'call_oi': 205268, 'put_oi': 72074},
    ]
    sample_expiry = '23-Sep-2025'
    sample_underlying = 25327.05

    plot_file = create_oi_plot(sample_data, sample_expiry, sample_underlying)

    if plot_file:
        print(f"Plot created and saved to: {plot_file}")
        # To verify, we could check if the file exists
        if os.path.exists(plot_file):
            print("File verification successful.")
        else:
            print("File verification failed.")
    else:
        print("Failed to create plot.")
