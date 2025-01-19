import React, { useState, useEffect } from 'react';

function TimerComponent() {
  useEffect(() => {
    const timer = setTimeout(() => {
      console.log('Timer abgelaufen');
    }, 1000);

    return () => {
      clearTimeout(timer);
      console.log('Timer bereinigt');
    };
  }, []);

  return <div>Timer läuft...</div>;
}

function App() {
  const [showTimer, setShowTimer] = useState(true);

  return (
    <div>
      <button onClick={() => setShowTimer(false)}>Stop Timer</button>
      {showTimer && <TimerComponent />}
    </div>
  );
}

export default App;