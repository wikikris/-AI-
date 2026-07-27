<template>
  <div>
    <div class="tb">
      <button class="primary" @click="doFetch" :disabled="fetching">{{ fetching?"采集中...":"采集数据" }}</button>
      <span class="mt">合约OI: {{ cDate||"-" }} | 机构: {{ mDate||"-" }} | 定时 16:30</span>
    </div>

    <div class="grid-2" style="margin-top:14px">
      <div class="card">
        <h2>合约概览</h2>
        <table v-if="items.length">
          <thead><tr><th>合约</th><th>品种</th><th>日期</th><th>价格</th><th>OI(万)</th><th>日变</th><th>5日变</th></tr></thead>
          <tbody>
            <tr v-for="p in items" :key="p.contract_code" @click="$router.push(`/contract/${p.contract_code}`)" style="cursor:pointer">
              <td><span style="color:var(--blue);font-weight:600">{{ p.contract_code }}</span></td>
              <td class="muted">{{ p.variety }}</td>
              <td class="muted">{{ p.latest_date||"-" }}</td>
              <td>{{ p.close?p.close.toFixed(1):"-" }}</td>
              <td>{{ p.open_interest?(p.open_interest/10000).toFixed(1):"-" }}</td>
              <td><span :class="p.oi_change_daily>0?'tag-up':p.oi_change_daily<0?'tag-down':'tag-neutral'">{{ fC(p.oi_change_daily) }}</span></td>
              <td><span :class="p.oi_change_5d>0?'tag-up':p.oi_change_5d<0?'tag-down':'tag-neutral'">{{ fC(p.oi_change_5d) }}</span></td>
            </tr>
          </tbody>
        </table>
        <div v-else class="loading">请先采集数据</div>
      </div>

      <div class="card">
        <h2>分析摘要</h2>
        <div v-if="anas.length">
          <div v-for="a in anas" :key="a.code" style="margin-bottom:16px">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:5px">
              <router-link :to="`/contract/${a.code}`" style="color:var(--blue);font-weight:600;font-size:12px;text-decoration:none">{{ a.code }}</router-link>
              <span class="muted" v-if="a.period" style="font-size:10px">{{ a.period }}</span>
              <span style="flex:1"></span>
              <template v-if="a.loading"><span class="muted" style="font-size:10px">...</span></template>
              <template v-else>
                <button class="mini" @click="goAnalyze(a.code,'1w')">周</button>
                <button class="mini" @click="goAnalyze(a.code,'1m')">月</button>
              </template>
            </div>
            <div v-if="a.content" style="font-size:12px;color:var(--txt2);line-height:1.7;max-height:200px;overflow-y:auto;white-space:pre-wrap">{{ truncate(a.content,420) }}</div>
            <div v-else class="loading" style="padding:8px;font-size:11px">点击周/月生成分析</div>
          </div>
        </div>
        <div v-else class="loading">生成分析中...</div>
      </div>
    </div>
  </div>
</template>

<script>
import { getOverview, getDashboard, triggerFetch, getAnalysis, triggerAnalysis, getLatestFetchDate } from "../api";

export default {
  data(){return{items:[],anas:[],fetching:false,cDate:null,mDate:null}},
  async mounted(){await this.load()},
  methods:{
    fC(n){if(!n)return"0";return(n>0?"+":"")+Number(n).toLocaleString()},
    truncate(t,l){return t&&t.length>l?t.slice(0,l)+"...":t||""},
    async load(){
      try{const[ov,d,dt]=await Promise.all([getOverview(),getDashboard(),getLatestFetchDate()]);this.items=ov.data.data||[];this.cDate=dt.data.latest_contract_date;this.mDate=dt.data.latest_member_date;
        for(const it of this.items){try{const r=await getAnalysis(it.contract_code);this.anas.push({code:it.contract_code,content:r.data.content||null,period:r.data.period||null,loading:false})}catch{this.anas.push({code:it.contract_code,content:null,loading:false})}}}catch(e){}},
    async doFetch(){this.fetching=true;try{await triggerFetch(null,true);this.items=[];this.anas=[];await this.load()}catch{}this.fetching=false},
    async goAnalyze(code,period){const it=this.anas.find(a=>a.code===code);if(it)it.loading=true;try{const r=await triggerAnalysis({contract_code:code,period});if(it){it.content=r.data.content;it.period=r.data.period}}catch{}if(it)it.loading=false}
  }
};
</script>

<style scoped>
.tb{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.mt{font-size:11px;color:var(--txt3)}
.mini{padding:2px 7px;font-size:10px}
</style>
