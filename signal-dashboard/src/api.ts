import axios from "axios";

const API = import.meta.env.VITE_API_URL || "http://localhost:8000";
export const getSignals = (date?: string) => {
  const url = date ? `${API}/signals?date=${date}` : `${API}/signals`;
  return axios.get(url);
};

export const checkDateExists = (date: string) =>
  axios.get(`${API}/signals/check-date/${date}`);

export const scrapeDate = (date: string, unlimited: boolean = false) => {
  const payload = unlimited
    ? { date: date, limit: null, use_streamlined: true }  // null = unlimited
    : { date: date, limit: 50, use_streamlined: true };   // default limit

  return axios.post(`${API}/scrape?sync=true`, payload);
};