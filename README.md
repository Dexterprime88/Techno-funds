# Techno-funds
Regarding Strategy in Stock market

## How to Run the Application

1.  **Start the Backend:** Open a terminal, navigate to the project root, and run:
    ```bash
    pip install -r requirements.txt
    uvicorn main:app --host 0.0.0.0 --port 8001
    ```
2.  **Start the Frontend:** Open a *second* terminal, navigate to the `ui` directory, and run:
    ```bash
    cd ui
    npm install
    npm start
    ```
3.  Your browser should open to `http://localhost:3000`.

## How to Log In (Daily)

You must generate a new Access Token each day.

1.  **Enter API Credentials:** In the application, fill in your **API Key** and **API Secret**.
2.  **Login with Kite:** Click the **"Step 1: Login with Kite"** button. This will open the official Zerodha Kite login page in a new tab.
3.  **Authorize and Get Request Token:** Log in with your trading credentials. After you succeed, you will be redirected to a new URL. Copy the `request_token` value from the end of that URL.
4.  **Generate Access Token:** Come back to the application tab. Paste the copied `request_token` into the **"Step 2: Paste Request Token here"** input box.
5.  Click the **"Step 3: Generate Access Token"** button. The "Access Token" field should now be filled in, and the application will start fetching data.

**Note:** The current implementation uses in-memory storage for API credentials, which is not secure and is intended for development purposes only. For a production environment, you should use a more secure method for storing and managing credentials, such as a database or a dedicated secrets management service.
