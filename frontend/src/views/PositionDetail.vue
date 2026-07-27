<template>
  <div>
    <div class="topbar">
      <button @click="$router.push('/')">←</button>
      <span class="title">{{ code }}</span>
      <span class="tag" v-if="variety">{{ variety }}</span>
      <div class="per-group">
        <button v-for="p in periods" :key="p.v" :class="{on:cur===p.v}" @click="sw(p.v)">{{ p.l }}</button>
      </div>
      <input type="date" v-model="d1" class="di"/><span class="muted">-</span><input type="date" v-model="d2" class="di"/>
      <button @click="ap">应用</button>
      <button class="primary" @click="analyze" :disabled="al">{{ al?"...":"分析" }}</button>
    </div>

    <div class="card" style="margin-top:14px"><div ref="c1" style="width:100%;height:360px"></div></div>
    <div class="grid-2" style="margin-top:14px">
      <div class="card"><h2>持仓走势</h2><div ref="c2" style="width:100%;height:300px"></div></div>
      <div class="card"><h2>机构净持仓</h2><div ref="c3" style="width:100%;height:300px"></div></div>
    </div>
    <div class="card" style="margin-top:14px"><h2>机构趋势</h2><div ref="c4" style="width:100%;height:300px"></div></div>

    <div class="card" style="margin-top:14px">
      <h2>分析报告<span class="muted" v-if="ap"> · {{ ap }}</span></h2>
      <div v-if="at" class="report">{{ at }}</div>
      <div v-else class="loading">点击分析按钮生成</div>
    </div>

    <div class="card" style="margin-top:14px" v-if="at">
      <h2>追问</h2>
      <div class="chatbox" ref="cb">
        <div v-for="(m,i) in ch" :key="i" :class="m.role==='user'?'cu':'ca'">{{ m.content }}</div>
        <div v-if="cl" class="ca muted">...</div>
      </div>
      <div class="ci"><input v-model="q" placeholder="基于报告继续追问..." @keyup.enter="cq"/><button @click="cq" :disabled="cl">发送</button></div>
    </div>

    <div class="card" style="margin-top:14px">
      <h2>机构明细<span class="muted"> · {{ md }}</span></h2>
      <div style="overflow-x:auto">
        <table v-if="ms.length"><thead><tr><th>#</th><th>机构</th><th>多头</th><th>日变</th><th>空头</th><th>日变</th><th>净持仓</th><th>期间净变</th></tr></thead>
          <tbody><tr v-for="(m,i) in ms" :key="m.member_name"><td class="muted">{{ i+1 }}</td><td>{{ m.member_name }}</td>
              <td>{{ fk(m.long_position) }}</td><td :class="m.long_change>0?'up':'down'">{{ fc(m.long_change) }}</td>
              <td>{{ fk(m.short_position) }}</td><td :class="m.short_change>0?'up':'down'">{{ fc(m.short_change) }}</td>
              <td :class="m.net_position>0?'up':'down'">{{ fk(m.net_position) }}</td><td :class="m.period_net_chg>0?'up':'down'">{{ fc(m.period_net_chg) }}</td></tr></tbody>
        </table><div v-else class="loading">暂无</div>
      </div>
    </div>
  </div>
</template>

<script>
import { getContractOI, getPositions, getMemberPositions, getMemberTrend, getAnalysis, triggerAnalysis, chatFollowup } from "../api";
import * as echarts from "echarts";

const cs = {tooltip:{trigger:"axis",confine:true,backgroundColor:"#171a24",borderColor:"#3a4050",textStyle:{color:"#e8ebf0",fontSize:12}},grid:{left:60,right:55,top:36,bottom:28},xAxis:{type:"category",axisLabel:{color:"#6b7080",fontSize:10},axisLine:{lineStyle:{color:"#252a35"}}},yAxis:[{type:"value",axisLabel:{color:"#6b7080",fontSize:10},splitLine:{lineStyle:{color:"#1e2230"}}},{type:"value",axisLabel:{color:"#6b7080",fontSize:10,formatter:v=>(v/10000).toFixed(0)+"万"},splitLine:{show:false}}]};

export default {
  props:["code"],
  data(){return{variety:"",cur:"1m",d1:"",d2:"",periods:[{v:"1w",l:"1周"},{v:"2w",l:"2周"},{v:"1m",l:"1月"},{v:"3m",l:"3月"}],oi:[],pos:[],ms:[],md:"",tr:{},at:null,ap:"",al:false,ch:[],q:"",cl:false}},
  mounted(){this._load()},
  beforeUnmount(){this._charts?.forEach(c=>c?.dispose())},
  methods:{
    fk(n){return n?(n/10000).toFixed(1)+"万":"-"},
    fc(n){return n?(n>0?"+":"")+Number(n).toLocaleString():"0"},
    _params(){return this.d1&&this.d2?{start_date:this.d1,end_date:this.d2}:{period:this.cur}},
    async sw(v){this.cur=v;this.d1=this.d2="";await this._load()},
    async ap(){if(this.d1&&this.d2){this.cur="";await this._load()}},
    async _load(){
      const p=this._params();
      try{const[oi,ps,ms,tr,an]=await Promise.all([getContractOI(this.code,p),getPositions(this.code,p),getMemberPositions(this.code,p),getMemberTrend(this.code,"",p),getAnalysis(this.code)]);
        this.oi=oi.data.data||[];this.pos=ps.data.data||[];this.variety=ps.data.variety||ms.data.variety||"";this.ms=ms.data.members||[];this.md=ms.data.date||"";this.tr=tr.data.members||{};this.at=an.data.content||null;this.ap=an.data.period||null;
        this.$nextTick(()=>{this._r1();this._r2();this._r3();this._r4()})}catch(e){console.error(e)}
    },
    _opt(s,data){return Object.assign({},{...cs,legend:{data:s.map(x=>x.name),textStyle:{color:"#6b7080",fontSize:11},top:0},xAxis:{...cs.xAxis,data},series:s})},
    _r1(){
      const d=this.oi.map(r=>r.date);if(!d.length)return;
      this._charts=this._charts||[];this._charts[0]?.dispose();this._charts[0]=echarts.init(this.$refs.c1);
      this._charts[0].setOption(this._opt([{name:"收盘价",type:"line",data:this.oi.map(r=>r.close),lineStyle:{color:"#f4b740",width:2},symbol:"none"},{name:"持仓量",type:"line",yAxisIndex:1,data:this.oi.map(r=>r.open_interest),lineStyle:{color:"#64b5f6",width:1.5},symbol:"none"},{name:"成交量",type:"bar",yAxisIndex:1,data:this.oi.map(r=>r.volume),itemStyle:{color:"rgba(100,181,246,.3)"}}],d));
    },
    _r2(){
      const d=this.pos.map(r=>r.date);if(!d.length)return;
      this._charts=this._charts||[];this._charts[1]?.dispose();this._charts[1]=echarts.init(this.$refs.c2);
      this._charts[1].setOption(this._opt([{name:"多头",type:"line",data:this.pos.map(r=>r.long_position),lineStyle:{color:"#ff5252",width:2},symbol:"none"},{name:"空头",type:"line",data:this.pos.map(r=>r.short_position),lineStyle:{color:"#4cd99b",width:2},symbol:"none"},{name:"净持仓",type:"bar",data:this.pos.map(r=>r.net_position),itemStyle:{color:p=>p.value>=0?"#ff5252":"#4cd99b"}}],d));
    },
    _r3(){
      if(!this.ms.length)return;
      const nl=this.ms.filter(m=>m.net_position>0).sort((a,b)=>b.net_position-a.net_position).slice(0,5);
      const ns=this.ms.filter(m=>m.net_position<0).sort((a,b)=>a.net_position-b.net_position).slice(0,5).reverse();
      const names=[...ns.map(m=>m.member_name),...nl.map(m=>m.member_name)];
      const vals=[...ns.map(m=>-m.short_position),...nl.map(m=>m.long_position)];
      const cols=[...ns.map(()=>"#4cd99b"),...nl.map(()=>"#ff5252")];
      const labs=[...ns.map(m=>"净空"+(-m.net_position).toLocaleString()),...nl.map(m=>"净多"+m.net_position.toLocaleString())];
      this._charts=this._charts||[];this._charts[2]?.dispose();this._charts[2]=echarts.init(this.$refs.c3);
      this._charts[2].setOption({tooltip:{...cs.tooltip,axisPointer:{type:"shadow"},formatter:p=>{const m=this.ms.find(x=>x.member_name===p[0].name);return m?`${m.member_name}<br/>多头:${m.long_position.toLocaleString()} (${m.long_change>0?'+':''}${m.long_change})<br/>空头:${m.short_position.toLocaleString()} (${m.short_change>0?'+':''}${m.short_change})<br/>净:${m.net_position.toLocaleString()}`:p[0].name}},grid:{left:90,right:10,top:6,bottom:20},xAxis:{type:"value",axisLabel:{color:"#6b7080",fontSize:10,formatter:v=>(Math.abs(v)/10000).toFixed(0)+"万"},splitLine:{lineStyle:{color:"#1e2230"}}},yAxis:{type:"category",data:names,axisLabel:{color:"#6b7080",fontSize:10}},series:[{type:"bar",data:vals,itemStyle:{color:p=>cols[p.dataIndex]},label:{show:true,position:"right",color:"#9ca0a8",fontSize:10,formatter:p=>labs[p.dataIndex]}}]});
    },
    _r4(){
      if(!Object.keys(this.tr).length)return;
      const all=new Set();const clrs=["#64b5f6","#ff5252","#4cd99b","#f4b740","#ab47bc","#ef5350","#26c6da","#9ccc65","#ff7043","#7e57c2"];
      const ss=Object.entries(this.tr).slice(0,12).map(([n,d],i)=>{d.forEach(x=>all.add(x.date));return{name:n,type:"line",data:d.map(x=>[x.date,x.net]),smooth:true,symbol:"none",lineStyle:{width:1.5},itemStyle:{color:clrs[i%clrs.length]}}});
      this._charts=this._charts||[];this._charts[3]?.dispose();this._charts[3]=echarts.init(this.$refs.c4);
      this._charts[3].setOption({tooltip:cs.tooltip,legend:{type:"scroll",bottom:0,textStyle:{color:"#6b7080",fontSize:10}},grid:{left:55,right:10,top:6,bottom:44},xAxis:{type:"category",data:[...all].sort(),axisLabel:{color:"#6b7080",fontSize:10}},yAxis:{type:"value",axisLabel:{color:"#6b7080",fontSize:10,formatter:v=>(v/10000).toFixed(0)+"万"},splitLine:{lineStyle:{color:"#1e2230"}}},series:ss});
    },
    async analyze(){this.al=true;const p=this._params(),pl={contract_code:this.code};if(p.period)pl.period=p.period;else{pl.start_date=p.start_date;pl.end_date=p.end_date}try{const r=await triggerAnalysis(pl);this.at=r.data.content;this.ap=r.data.period}catch(e){}this.al=false},
    async cq(){if(!this.q.trim())return;const m=this.q;this.ch.push({role:"user",content:m});this.q="";this.cl=true;this.$nextTick(()=>{const b=this.$refs.cb;if(b)b.scrollTop=b.scrollHeight});try{const r=await chatFollowup({contract_code:this.code,question:m,analysis_context:this.at||"",history:this.ch.slice(-10)});this.ch.push({role:"assistant",content:r.data.reply})}catch(e){}this.cl=false;this.$nextTick(()=>{const b=this.$refs.cb;if(b)b.scrollTop=b.scrollHeight})}
  }
};
</script>

<style scoped>
.topbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.title{font-size:15px;font-weight:700;color:var(--txt)}
.tag{font-size:10px;color:var(--txt3);background:#1e2230;padding:2px 8px;border-radius:4px;border:1px solid var(--border)}
.per-group{display:flex;border:1px solid var(--border);border-radius:5px;overflow:hidden}
.per-group button{border:none;border-radius:0;padding:5px 10px;font-size:11px}
.per-group button.on{background:var(--blue);color:#fff}
.di{padding:5px 8px;font-size:11px;width:118px}
.muted{color:var(--txt3)}
.report{white-space:pre-wrap;font-size:13px;line-height:1.85;color:var(--txt2);max-height:640px;overflow-y:auto}
.chatbox{max-height:260px;overflow-y:auto;margin-bottom:10px}
.cu{margin-bottom:8px;padding:7px 10px;background:#1e2230;border-radius:5px;font-size:12px;color:var(--txt)}
.ca{margin-bottom:8px;padding:7px 10px;font-size:12px;color:var(--txt2);line-height:1.6}
.ci{display:flex;gap:8px}.ci input{flex:1;padding:8px 10px}
</style>
