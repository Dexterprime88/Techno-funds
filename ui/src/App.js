import React, { useState, useEffect } from 'react';
import OIChart from './components/charts/OIChart';
import DeltaOIChart from './components/charts/DeltaOIChart';
import PutTable from './components/tables/PutTable';
import CallTable from './components/tables/CallTable';
import BiasTable from './components/tables/BiasTable';
import { generateAccessToken, getOptionChain } from './services/api';

function App() {
  const [apiKey, setApiKey] =useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [requestToken, setRequestToken] = useState('');
  const [accessToken, setAccessToken] = useState('');
  const [instrument, setInstrument] = useState('NIFTY');
  const [callData, setCallData] = useState([]);
  const [putData, setPutData] = useState([]);
  const [livePrice, setLivePrice] = useState(0);
  const [errorMessage, setErrorMessage] = useState('');

  const fetchOptionChain = async () => {
    try {
      const data = await getOptionChain(instrument);
      setCallData(data.calls || []);
      setPutData(data.puts || []);
      setLivePrice(data.live_price || 0);
    } catch (error) {
      console.error("Failed to fetch option chain:", error);
      setErrorMessage("Could not fetch live data. Please ensure your credentials are correct and you have a stable connection.");
    }
  };

  useEffect(() => {
    if (accessToken) {
        const interval = setInterval(fetchOptionChain, 60000); // Poll every minute
        return () => clearInterval(interval);
    }
  }, [accessToken, instrument]);

  const handleKiteLogin = () => {
      if (!apiKey) {
          setErrorMessage("Please enter your API Key before logging in.");
          return;
      }
      setErrorMessage("");
      const kiteLoginURL = `https://kite.trade/connect/login?v=3&api_key=${apiKey}`;
      window.open(kiteLoginURL, '_blank');
  };

  const handleGenerateToken = async () => {
    if (!apiKey || !apiSecret || !requestToken) {
      setErrorMessage("Please fill in the API Key, API Secret, and Request Token.");
      return;
    }
    setErrorMessage('');
    try {
      const data = await generateAccessToken(apiKey, apiSecret, requestToken);
      setAccessToken(data.access_token);
      // Immediately fetch live data now that we are authenticated
      fetchOptionChain();
    } catch (error) {
      setErrorMessage(error.message);
    }
  };

  return (
    <div className="App">
      <h1>Nifty/BankNifty Live OI & Delta-OI Dashboard</h1>

      {errorMessage && <p style={{color: 'red'}}>{errorMessage}</p>}

      <div className="settings">
        <h2>API Settings</h2>
        <input
          type="text"
          placeholder="API Key"
          value={apiKey}
          onChange={(e) => setApiKey(e.target.value)}
        />
        <input
          type="text"
          placeholder="API Secret"
          value={apiSecret}
          onChange={(e) => setApiSecret(e.target.value)}
        />

        <button onClick={handleKiteLogin}>Step 1: Login with Kite</button>

        <input
          type="text"
          placeholder="Step 2: Paste Request Token here"
          value={requestToken}
          onChange={(e) => setRequestToken(e.target.value)}
        />

        <button onClick={handleGenerateToken}>Step 3: Generate Access Token</button>

        <input
          type="text"
          placeholder="Access Token (auto-generated)"
          value={accessToken}
          readOnly
        />
      </div>

      <div className="controls">
        <select value={instrument} onChange={(e) => setInstrument(e.target.value)}>
          <option value="NIFTY">NIFTY</option>
          <option value="BANKNIFTY">BANKNIFTY</option>
        </select>
        <h3>Live Price: {livePrice}</h3>
      </div>

      <div className="main-panel">
        <OIChart />
        <DeltaOIChart />
        <CallTable data={callData} />
        <PutTable data={putData} />
        <BiasTable />
      </div>
    </div>
  );
}

export default App;
