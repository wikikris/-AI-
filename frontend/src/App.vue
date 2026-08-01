<template>
  <div id="app-root">
    <header class="app-header">
      <router-link to="/" class="logo">Futures PA</router-link>
      <nav class="nav-links">
        <router-link to="/" class="nav-item">仪表盘</router-link>
        <router-link to="/history" class="nav-item">聊天</router-link>
        <router-link to="/settings" class="nav-item">设置</router-link>
      </nav>
      <span class="status-dot" title="服务运行中"></span>
    </header>
    <main class="app-main"><router-view /></main>
  </div>
</template>

<style scoped>
.app-header{
  position:relative;
  background:rgba(12,16,22,.72);
  backdrop-filter:blur(28px) saturate(160%);
  -webkit-backdrop-filter:blur(28px) saturate(160%);
  border-bottom:1px solid var(--border);
  height:48px;display:flex;align-items:center;padding:0 20px;gap:24px;
  position:sticky;top:0;z-index:100;
  box-shadow:
    0 1px 0 rgba(255,255,255,.04) inset,
    0 4px 30px rgba(0,0,0,.35);
}
/* 顶栏顶部镜面高光 */
.app-header::before{
  content:'';position:absolute;top:0;left:5%;right:5%;height:1px;
  background:linear-gradient(90deg,transparent,rgba(255,255,255,.2),rgba(255,255,255,.08),transparent);
  pointer-events:none;
}
.logo{
  font-size:13px;font-weight:700;color:var(--txt2);text-decoration:none;
  letter-spacing:.4px;transition:color var(--transition);
}
.logo:hover{color:var(--txt)}
.nav-links{display:flex;gap:4px}
.nav-item{
  font-size:12px;font-weight:500;color:var(--txt3);text-decoration:none;
  padding:4px 12px;border-radius:var(--radius-sm);transition:all var(--transition);
}
.nav-item:hover{color:var(--txt2);background:rgba(255,255,255,.05)}
.nav-item.router-link-exact-active{color:var(--txt);background:rgba(255,255,255,.07)}
.status-dot{
  margin-left:auto;width:6px;height:6px;border-radius:50%;
  background:var(--green);
  box-shadow:0 0 10px rgba(34,197,94,.6),0 0 4px rgba(34,197,94,.3);
  animation:pulse 2.5s ease-in-out infinite;
}
@keyframes pulse{
  0%,100%{opacity:.85;box-shadow:0 0 10px rgba(34,197,94,.6)}
  50%{opacity:.35;box-shadow:0 0 4px rgba(34,197,94,.2)}
}
.app-main{padding:20px;max-width:1500px;margin:0 auto}
</style>
