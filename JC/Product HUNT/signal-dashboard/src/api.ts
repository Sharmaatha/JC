import axios from "axios";

const API = "http://localhost:8000";

export const getSignals = (date?: string) => {
  const url = date ? `${API}/signals?date=${date}` : `${API}/signals`;
  return axios.get(url);
};

export const scoreProduct = (id: number) =>
  axios.post(`${API}/score/${id}`);

export const checkDateExists = (date: string) =>
  axios.get(`${API}/signals/check-date/${date}`);

export const scrapeDate = (date: string) => {
  const [year, month, day] = date.split("-");
  const formattedDate = `${day}-${month}-${year}`;
  return axios.post(`${API}/scrape`, { date: formattedDate, limit: 3 });
};
