import { useRef, useState } from "react";
import { createWebSocket } from "../services/websocketService";

export function useWebSocket(url, deviceUid, getPayload) {
  const wsRef = useRef(null);
  const connectingRef = useRef(false);
  const sendTimerRef = useRef(null);

  const [connected, setConnected] = useState(false);

  const connect = () => {
    if (connectingRef.current) return;

    connectingRef.current = true;

    const ws = createWebSocket(url, {
      onOpen: () => {
        wsRef.current = ws;
        setConnected(true);
        connectingRef.current = false;

        startSendLoop();
      },

      onClose: () => {
        setConnected(false);
        connectingRef.current = false;
      },

      onError: () => {
        connectingRef.current = false;
      },
    });
  };

  const disconnect = () => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }

    if (sendTimerRef.current) {
      clearInterval(sendTimerRef.current);
      sendTimerRef.current = null;
    }

    setConnected(false);
  };

  const startSendLoop = () => {
    if (sendTimerRef.current) return;

    sendTimerRef.current = setInterval(() => {
      const ws = wsRef.current;

      if (!ws || ws.readyState !== WebSocket.OPEN) return;

      ws.send(JSON.stringify(getPayload()));
    }, 60);
  };

  return {
    connect,
    disconnect,
    connected,
  };
}