import { createRouter, createWebHistory } from "vue-router";
import Dashboard from "../views/Dashboard.vue";
import PositionDetail from "../views/PositionDetail.vue";
import Settings from "../views/Settings.vue";
import ChatHistory from "../views/ChatHistory.vue";

const routes = [
  { path: "/", name: "Dashboard", component: Dashboard },
  { path: "/contract/:code", name: "PositionDetail", component: PositionDetail, props: true },
  { path: "/settings", name: "Settings", component: Settings },
  { path: "/history", name: "ChatHistory", component: ChatHistory },
];

export default createRouter({
  history: createWebHistory(),
  routes,
});
