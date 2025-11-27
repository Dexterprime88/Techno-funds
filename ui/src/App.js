import React, { useState, useEffect } from 'react';
import OIChart from './components/charts/OIChart';
import DeltaOIChart from './components/charts/DeltaOIChart';
import PutTable from './components/tables/PutTable';
import CallTable from './components/tables/CallTable';
import BiasTable from './components/tables/BiasTable';
import { setCredentials, getOptionChain } from './services/api';

function App() {
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [requestToken, setRequestToken] = useState('');
  const [accessToken, setAccessToken] = useState('');
  const [instrument, setInstrument] = useState('NIFTY');
  const [callData, setCallData] = useState([]);
  const [putData, setPutData] = useState([]);

  const fetchOptionChain = async () => {
    const data = await getOptionChain(instrument);
    setCallData(data.calls);
    setPutData(data.puts);
  };

  useEffect(() => {
    fetchOptionChain();
    const interval = setInterval(fetchOptionChain, 1000); // Poll every second
    return () => clearInterval(interval);
  }, [instrument]);

  const handleSetCredentials = async () => {
    await setCredentials({
      api_key: apiKey,
      api_secret: apiSecret,
      request_token: requestToken,
      access_token: accessToken,
    });
  };

  return (
    <div className="App">
      <h1>Nifty/BankNifty Live OI & Delta-OI Dashboard</h1>
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
        <input
          type="text"
          placeholder="Request Token"
          value={requestToken}
          onChange={(e) => setRequestToken(e.target.value)}
        />
        <input
          type="text"
          placeholder="Access Token"
          value={accessToken}
          onChange={(e) => setAccessToken(e.target.value)}
        />
        <button onClick={handleSetCredentials}>Set Credentials</button>
      </div>
      <div className="controls">
        <select value={instrument} onChange={(e) => setInstrument(e.target.value)}>
          <option value="NIFTY">NIFTY</option>
          <option value="BANKNIFTY">BANKNIFTY</option>
        </select>
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
