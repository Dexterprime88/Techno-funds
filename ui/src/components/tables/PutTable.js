import React from 'react';

const PutTable = ({ data }) => {
  return (
    <div>
      <h2>Puts</h2>
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
          {data && data.map((put) => (
            <tr key={put.strike}>
              <td>{put.strike}</td>
              <td>{put.oi}</td>
              <td>{put.oi_change}</td>
              <td>{put.delta}</td>
              <td>{put.ltp}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default PutTable;
