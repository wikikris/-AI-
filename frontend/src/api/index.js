import axios from "axios";

const api = axios.create({ baseURL: "/api", timeout: 60000 });

export function getContracts() { return api.get("/contracts"); }
export function getDashboard() { return api.get("/dashboard"); }
export function getOverview() { return api.get("/overview"); }

export function getContractOI(code, params = {}) {
  return api.get(`/contracts/${code}/oi`, { params: { period: "3m", ...params } });
}
export function getPositions(code, params = {}) {
  return api.get(`/positions/${code}`, { params: { period: "1m", ...params } });
}
export function getMemberPositions(code, params = {}) {
  return api.get(`/positions/${code}/members`, { params: { period: "1m", ...params } });
}
export function getMemberTrend(code, memberNames = "", params = {}) {
  return api.get(`/positions/${code}/member-trend`, { params: { member_names: memberNames, period: "1m", ...params } });
}
export function triggerFetch(targetDate, includeMembers = true) {
  return api.post("/fetch", { target_date: targetDate, include_members: includeMembers });
}
export function triggerAnalysis({ contract_code, period, start_date, end_date, days }) {
  return api.post("/analysis/generate", { contract_code, period, start_date, end_date, days });
}
export function getAnalysis(code) { return api.get(`/analysis/${code}`); }
export function chatFollowup(data) { return api.post("/analysis/chat", data); }
export function getLatestFetchDate() { return api.get("/fetch/latest-date"); }

// Config
export function getConfig() { return api.get("/config"); }
export function updateContracts(contracts) { return api.put("/config/contracts", { contracts }); }
export function updateAI(aiConfig) { return api.put("/config/ai", aiConfig); }
