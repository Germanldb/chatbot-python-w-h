import { useState, useEffect } from 'react';
import axios from 'axios';

const API = `${process.env.REACT_APP_BACKEND_URL}/api`;

export const useWhatsAppConnection = () => {
  const [qrCode, setQrCode] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [status, setStatus] = useState('disconnected');
  const [loading, setLoading] = useState(true);

  const checkStatus = async () => {
    try {
      const response = await axios.get(`${API}/whatsapp/status`);
      setIsConnected(response.data.connected);
      setStatus(response.data.status);
      return response.data.connected;
    } catch (error) {
      console.error('Error checking status:', error);
      setStatus('error');
      return false;
    }
  };

  const fetchQR = async () => {
    try {
      const response = await axios.get(`${API}/whatsapp/qr`);
      if (response.data.qr) {
        setQrCode(response.data.qr);
      } else {
        setQrCode(null);
      }
    } catch (error) {
      console.error('Error fetching QR:', error);
    }
  };

  useEffect(() => {
    const pollStatus = async () => {
      setLoading(true);
      const connected = await checkStatus();
      
      if (!connected) {
        await fetchQR();
      } else {
        setQrCode(null);
      }
      
      setLoading(false);
    };

    pollStatus();
    const interval = setInterval(pollStatus, 5000);

    return () => clearInterval(interval);
  }, []);

  return { qrCode, isConnected, status, loading, checkStatus };
};

export const useDashboardStats = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const response = await axios.get(`${API}/dashboard/stats`);
        setStats(response.data);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 10000);

    return () => clearInterval(interval);
  }, []);

  return { stats, loading, error };
};

export const useConversations = () => {
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchConversations = async () => {
    try {
      const response = await axios.get(`${API}/conversations`);
      setConversations(response.data.conversations);
      setError(null);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConversations();
    const interval = setInterval(fetchConversations, 5000);

    return () => clearInterval(interval);
  }, []);

  return { conversations, loading, error, refetch: fetchConversations };
};

export const useConversation = (phoneNumber) => {
  const [conversation, setConversation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!phoneNumber) return;

    const fetchConversation = async () => {
      try {
        const response = await axios.get(`${API}/conversations/${phoneNumber}`);
        setConversation(response.data);
        setError(null);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchConversation();
    const interval = setInterval(fetchConversation, 3000);

    return () => clearInterval(interval);
  }, [phoneNumber]);

  return { conversation, loading, error };
};