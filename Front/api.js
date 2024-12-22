import axios from 'axios';

const API_URL = 'http://localhost:8000';

export const login = (email, password) =>
  axios.post(`${API_URL}/auth/login`, { email, password });

export const register = (email, password) =>
  axios.post(`${API_URL}/auth/register`, { email, password });

export const fetchPage = (id, token = null) =>
  axios.get(`${API_URL}/page/${id}`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
