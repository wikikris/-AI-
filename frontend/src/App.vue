<template>
  <div id="app-root">
    <header class="app-header">
      <router-link to="/" class="logo">Futures PA</router-link>
      <router-link to="/" class="nav">仪表盘</router-link>
      <router-link to="/settings" class="nav nav-right">设置</router-link>
    </header>
    <main class="app-main"><router-view /></main>
  </div>
</template>

<style scoped>
.app-header{background:#11141b;border-bottom:1px solid #252a35;height:42px;display:flex;align-items:center;padding:0 18px;gap:22px}
.logo{font-size:13px;font-weight:700;color:var(--txt3);text-decoration:none;letter-spacing:.5px}
.nav{font-size:12px;color:var(--txt3);text-decoration:none}
.nav:hover,.nav.router-link-exact-active{color:var(--txt2)}
.nav-right{margin-left:auto}
.app-main{padding:20px;max-width:1620px;margin:0 auto}
</style>
