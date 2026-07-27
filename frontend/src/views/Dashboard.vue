<template>
  <div>
    <div class="tb">
      <button class="primary" @click="doFetch" :disabled="fetching">
        {{ fetching?"采集中...":"采集数据" }}
      </button>
      <span class="mt">合约: {{ cDate||"-" }} | 机构: {{ mDate||"-" }} | 定时 16:30</span>
    </div>

    <div class="stat-grid" style="margin-top:16px" v-if="items.length">
      <div class="stat">
        <div class="sv">{{ items.length }}</div>
        <div class="sl">监控合约</div>
      </div>
      <div class="stat">
        <div class="sv">{{ cDate||"-" }}</div>
        <div class="sl">最新合约数据</div>
      </div>
      <div class="stat">
        <div class="sv">{{ mDate||"-" }}</div>
        <div class="sl">最新机构数据</div>
      </div>
      <div class="stat">
        <div class="sv">{{ analyzedCount }}/{{ items.length }}</div>
        <div class="sl">已有分析</div>
      </div>
    </div>

    <div class="grid-2" style="margin-top:16px">
      <div class="card">
        <h2>合约概览</h2>
        <div style="overflow-x:auto">
          <table v-if="items.length">
            <thead><tr>
              <th>合约</th><th>品种</th><th>日期</th><th>价格</th>
              <th>OI<br><span class="muted">(万手)</span></th>
              <th>日变</th><th>5日变</th>
            </tr></thead>
            <tbody>
              <tr v-for="p in items" :key="p.contract_code"
                @click="$router.push(`/contract/${p.contract_code}`)" style="cursor:pointer">
                <td><span class="code-link">{{ p.contract_code }}</span></td>
                <td class="muted">{{ p.variety }}</td>
                <td class="muted">{{ p.latest_date||"-" }}</td>
                <td>{{ p.close?p.close.toFixed(1):"-" }}</td>
                <td>{{ p.open_interest?(p.open_interest/10000).toFixed(1):"-" }}</td>
                <td>
                  <span :class="p.oi_change_daily>0?'tag-up':p.oi_change_daily<0?'tag-down':'tag-neutral'">
                    {{ fC(p.oi_change_daily) }}
                  </span>
                </td>
                <td>
                  <span :class="p.oi_change_5d>0?'tag-up':p.oi_change_5d<0?'tag-down':'tag-neutral'">
                    {{ fC(p.oi_change_5d) }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="loading">请先采集数据</div>
        </div>
      </div>

      <div class="card">
        <h2>分析摘要</h2>
        <div v-if="displayAnas.length" class="ana-list">
          <div v-for="a in displayAnas" :key="a.code" class="ana-item">
            <div class="ana-head">
              <router-link :to="`/contract/${a.code}`" class="ana-code">{{ a.code }}</router-link>
              <span class="muted" v-if="a.period" style="font-size:10px">{{ a.period }}</span>
              <span style="flex:1"></span>
              <template v-if="a.loading">
                <span class="muted" style="font-size:10px">...</span>
              </template>
              <template v-else>
                <button class="mini" @click="goAnalyze(a.code,'1w')">周</button>
                <button class="mini" @click="goAnalyze(a.code,'1m')">月</button>
              </template>
            </div>
            <div v-if="a.content" class="ana-text">{{ truncate(a.content,400) }}</div>
            <div v-else class="ana-empty">点击 周/月 生成分析</div>
          </div>
          <div v-if="anas.length>5" class="ana-more" @click="expanded=!expanded">
            {{ expanded?'收起':'展开全部 '+anas.length+' 条' }}
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
  data(){return{items:[],anas:[],fetching:false,cDate:null,mDate:null,expanded:false}},
  computed:{
    analyzedCount(){return this.anas.filter(a=>a.content).length},
    displayAnas(){return this.expanded?this.anas:this.anas.slice(0,5)}
  },
  async mounted(){await this.load()},
  methods:{
    fC(n){if(!n)return"0";return(n>0?"+":"")+Number(n).toLocaleString()},
    truncate(t,l){return t&&t.length>l?t.slice(0,l)+"...":t||""},
    async load(){
      try{
        const[ov,d,dt]=await Promise.all([getOverview(),getDashboard(),getLatestFetchDate()]);
        this.items=ov.data.data||[];
        this.cDate=dt.data.latest_contract_date;
        this.mDate=dt.data.latest_member_date;
        for(const it of this.items){
          try{
            const r=await getAnalysis(it.contract_code);
            this.anas.push({code:it.contract_code,content:r.data.content||null,period:r.data.period||null,loading:false})
          }catch{this.anas.push({code:it.contract_code,content:null,loading:false})}
        }
      }catch(e){}
    },
    async doFetch(){
      this.fetching=true;
      try{await triggerFetch(null,true);this.items=[];this.anas=[];await this.load()}catch{}
      this.fetching=false
    },
    async goAnalyze(code,period){
      const it=this.anas.find(a=>a.code===code);if(it)it.loading=true;
      try{
        const r=await triggerAnalysis({contract_code:code,period});
        if(it){it.content=r.data.content;it.period=r.data.period}
      }catch{}
      if(it)it.loading=false
    }
  }
};
</script>

<style scoped>
.tb{display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.mt{font-size:11px;color:var(--txt3)}
.stat{position:relative;overflow:hidden}
.stat::before{content:'';position:absolute;top:0;left:0;width:3px;height:100%;border-radius:3px 0 0 3px}
.stat:nth-child(1)::before{background:var(--blue)}
.stat:nth-child(2)::before{background:var(--green)}
.stat:nth-child(3)::before{background:var(--purple)}
.stat:nth-child(4)::before{background:var(--gold)}
.code-link{color:var(--blue);font-weight:600;transition:color var(--transition)}
.code-link:hover{color:#6aade0}
.mini{padding:3px 8px;font-size:10px}
.ana-list{display:flex;flex-direction:column;gap:5px}
.ana-item{
  background:var(--bg-elevated);border:1px solid var(--border-light);border-left:2px solid var(--blue);
  border-radius:0 var(--radius-sm) var(--radius-sm) 0;padding:12px 14px;transition:all var(--transition);
}
.ana-item:nth-child(5n+2){border-left-color:var(--purple)}
.ana-item:nth-child(5n+3){border-left-color:var(--cyan)}
.ana-item:nth-child(5n+4){border-left-color:var(--gold)}
.ana-item:nth-child(5n+5){border-left-color:var(--green)}
.ana-item:hover{border-color:var(--txt4);border-left-width:3px}
.ana-head{display:flex;align-items:center;gap:8px;margin-bottom:6px}
.ana-code{color:var(--blue);font-weight:600;font-size:12px;text-decoration:none}
.ana-code:hover{text-decoration:underline}
.ana-text{
  font-size:11px;color:var(--txt2);line-height:1.7;max-height:160px;
  overflow-y:auto;white-space:pre-wrap;
}
.ana-empty{font-size:11px;color:var(--txt3);padding:4px 0}
.ana-more{font-size:11px;color:var(--blue);text-align:center;padding:8px;cursor:pointer;transition:color var(--transition)}
.ana-more:hover{color:#6aade0}
</style>
