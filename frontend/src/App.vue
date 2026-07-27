<template>
  <div id="app-root">
    <header class="app-header">
      <router-link to="/" class="logo">Futures PA</router-link>
      <nav class="nav-links">
        <router-link to="/" class="nav-item">仪表盘</router-link>
        <router-link to="/settings" class="nav-item">设置</router-link>
      </nav>
      <span class="status-dot" title="服务运行中"></span>
    </header>
    <main class="app-main"><router-view /></main>
  </div>
</template>

<style scoped>
.app-header{
  background:var(--bg-card);border-bottom:1px solid var(--border);
  height:44px;display:flex;align-items:center;padding:0 20px;gap:24px;
  position:sticky;top:0;z-index:100;backdrop-filter:blur(8px);
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
.nav-item:hover{color:var(--txt2);background:var(--bg-elevated)}
.nav-item.router-link-exact-active{color:var(--txt);background:var(--bg-elevated)}
.status-dot{
  margin-left:auto;width:7px;height:7px;border-radius:50%;
  background:var(--green);opacity:.8;animation:pulse 2s infinite;
}
@keyframes pulse{0%,100%{opacity:.8}50%{opacity:.4}}
.app-main{padding:20px;max-width:1500px;margin:0 auto}
</style>
