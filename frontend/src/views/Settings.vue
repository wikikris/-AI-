<template>
  <div class="sp">
    <div class="card">
      <h2>关注合约</h2>
      <div class="ar">
        <input ref="ci" v-model="nc" placeholder="合约代码, 如 RB2610" class="cin" @keyup.enter="add" />
        <input v-model="nv" placeholder="品种名 (可留空)" class="vin" @keyup.enter="add" />
        <button class="primary" @click="add">添加</button>
      </div>
      <div class="cg" v-if="cs.length">
        <div class="ct" v-for="(c,i) in cs" :key="c.code">
          <span class="ctc">{{ c.code }}</span>
          <span class="ctv">{{ c.variety||"自动识别" }}</span>
          <button class="ctx" @click="rm(i)">×</button>
        </div>
      </div>
      <div class="empty" v-else>尚未添加合约</div>
      <div style="margin-top:10px">
        <button class="primary" @click="sc" :disabled="sv">{{ sv?"保存中...":"保存" }}</button>
        <span class="ok" v-if="sd">已保存</span>
      </div>
    </div>

    <div class="card" style="margin-top:14px">
      <h2>AI 配置</h2>
      <div class="fld"><label>API Key</label><input v-model="ai.api_key" type="password" placeholder="sk-..."/></div>
      <div class="fld"><label>接口地址</label><input v-model="ai.base_url" placeholder="https://api.openai.com/v1"/></div>
      <div class="fld"><label>模型</label><input v-model="ai.model" placeholder="gpt-4o-mini"/></div>
      <div style="margin-top:10px">
        <button class="primary" @click="sa" :disabled="sva">{{ sva?"保存中...":"保存" }}</button>
        <span class="ok" v-if="sda">已保存</span>
      </div>
    </div>
  </div>
</template>

<script>
import { getConfig, updateContracts, updateAI } from "../api";
export default {
  data(){return{cs:[],nc:"",nv:"",ai:{api_key:"",base_url:"https://api.openai.com/v1",model:"gpt-4o-mini"},sv:false,sd:false,sva:false,sda:false}},
  async mounted(){try{const r=await getConfig();this.cs=r.data.contracts||[];if(r.data.ai){this.ai.api_key=r.data.ai.api_key||"";this.ai.base_url=r.data.ai.base_url||"";this.ai.model=r.data.ai.model||""}}catch(e){}},
  methods:{
    add(){const c=this.nc.trim().toUpperCase();if(!c||this.cs.find(x=>x.code===c))return;this.cs.push({code:c,variety:this.nv.trim(),exchange:""});this.nc="";this.nv="";this.sd=false;this.$refs.ci?.focus()},
    rm(i){this.cs.splice(i,1);this.sd=false},
    async sc(){this.sv=true;try{await updateContracts(this.cs);this.sd=true;setTimeout(()=>this.sd=false,2000)}catch{}this.sv=false},
    async sa(){this.sva=true;try{await updateAI(this.ai);this.sda=true;setTimeout(()=>this.sda=false,2000)}catch{}this.sva=false}
  }
};
</script>

<style scoped>
.sp{max-width:800px}
.ar{display:flex;gap:8px;margin-bottom:12px}
.cin{width:170px;padding:8px 10px;font-weight:600;text-transform:uppercase}
.vin{width:180px;padding:8px 10px}
.cg{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:6px;margin-bottom:8px}
.ct{display:flex;align-items:center;gap:8px;background:#11141b;border:1px solid var(--border);border-radius:5px;padding:8px 10px}
.ctc{font-weight:600;color:var(--blue);font-size:13px}
.ctv{font-size:11px;color:var(--txt3)}
.ctx{margin-left:auto;background:none;border:none;color:var(--txt3);font-size:16px;cursor:pointer;padding:0 3px}
.ctx:hover{color:var(--red)}
.empty{color:var(--txt3);padding:20px 0;text-align:center;font-size:12px}
.fld{margin-bottom:12px}
.fld label{display:block;font-size:11px;color:var(--txt3);margin-bottom:4px}
.fld input{width:100%;padding:8px 10px}
.ok{color:var(--green);font-size:11px;margin-left:8px}
</style>
