import React from 'react';

const CallTable = ({ data }) => {
  return (
    <div>
      <h2>Calls</h2>
      <table>
        <thead>
          <tr>
            <th>Strike</th>
            <th>OI</th>
            <th>OI Change</th>
            <th>Delta</th>
            <th>LTP</th>
          </tr>
        </thead>
        <tbody>
          {data && data.map((call) => (
            <tr key={call.strike}>
              <td>{call.strike}</td>
              <td>{call.oi}</td>
              <td>{call.oi_change}</td>
              <td>{call.delta}</td>
              <td>{call.ltp}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default CallTable;
