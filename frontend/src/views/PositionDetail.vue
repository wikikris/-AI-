<template>
  <div>
    <div class="topbar">
      <button class="back-btn" @click="$router.push('/')">← 返回</button>
      <span class="title">{{ code }}</span>
      <span class="tag" v-if="variety">{{ variety }}</span>
      <span style="flex:1"></span>
      <div class="per-group">
        <button v-for="p in periods" :key="p.v" :class="{on:cur===p.v}" @click="sw(p.v)">{{ p.l }}</button>
      </div>
      <input type="date" v-model="d1" class="di"/>
      <span class="muted">—</span>
      <input type="date" v-model="d2" class="di"/>
      <button @click="ap">应用</button>
      <button class="primary" @click="analyze" :disabled="al">{{ al?"分析中...":"AI 分析" }}</button>
    </div>

    <div class="card" style="margin-top:16px">
      <h2>K线图</h2>
      <div ref="c1" style="width:100%;height:400px"></div>
      <div class="price-strip" v-if="oi.length">
        <div class="ps-item">
          <span class="ps-label">收盘</span>
          <span class="ps-val">{{ latest.close.toFixed(1) }}</span>
        </div>
        <div class="ps-item" :class="chg>=0?'ps-up':'ps-down'">
          <span class="ps-label">涨跌</span>
          <span :class="['ps-val',chg>=0?'up':'down']">{{ chg>=0?'+':'' }}{{ chg.toFixed(1) }} ({{ chgPct>=0?'+':'' }}{{ chgPct.toFixed(2) }}%)</span>
        </div>
        <div class="ps-item">
          <span class="ps-label">最高</span>
          <span class="ps-val">{{ latest.high.toFixed(1) }}</span>
        </div>
        <div class="ps-item">
          <span class="ps-label">最低</span>
          <span class="ps-val">{{ latest.low.toFixed(1) }}</span>
        </div>
        <div class="ps-item">
          <span class="ps-label">成交量</span>
          <span class="ps-val">{{ fmtVol(latest.volume) }}</span>
        </div>
        <div class="ps-item">
          <span class="ps-label">持仓量</span>
          <span class="ps-val">{{ (latest.open_interest/10000).toFixed(2) }}万</span>
        </div>
        <div class="ps-item" :class="oiChg>=0?'ps-up':'ps-down'">
          <span class="ps-label">日增仓</span>
          <span :class="['ps-val',oiChg>=0?'up':'down']">{{ oiChg>=0?'+':'' }}{{ fmtVol(Math.abs(oiChg)) }}</span>
        </div>
      </div>
    </div>

    <div class="grid-2" style="margin-top:16px">
      <div class="card">
        <h2>持仓走势</h2>
        <div ref="c2" style="width:100%;height:280px"></div>
      </div>
      <div class="card">
        <h2>机构净持仓</h2>
        <div ref="c3" style="width:100%;height:280px"></div>
      </div>
    </div>

    <div class="card" style="margin-top:16px">
      <h2>机构趋势</h2>
      <div ref="c4" style="width:100%;height:280px"></div>
    </div>

    <div class="card" style="margin-top:16px">
      <h2>分析报告<span class="muted" v-if="ap"> · {{ ap }}</span></h2>
      <div v-if="at" class="report">{{ at }}</div>
      <div v-else class="loading">点击上方 "AI 分析" 按钮生成报告</div>
      <div v-if="at" class="chat-section">
        <div class="chat-header">追问分析</div>
        <div class="chatbox" ref="cb">
          <div v-for="(m,i) in ch" :key="i" :class="['msg', m.role==='user'?'msg-you':'msg-ai']">
            <span class="msg-label">{{ m.role==='user'?'你':'AI' }}</span>
            <div class="msg-body">{{ m.content }}</div>
          </div>
          <div v-if="cl" class="msg msg-ai"><span class="msg-label">AI</span><div class="msg-body typing-dots"><span></span><span></span><span></span></div></div>
        </div>
        <div class="ci">
          <input v-model="q" placeholder="基于报告继续追问..." @keyup.enter="cq"/>
          <button @click="cq" :disabled="cl">发送</button>
        </div>
      </div>
    </div>

    <div class="card" style="margin-top:16px">
      <h2>机构明细<span class="muted"> · {{ md }}</span></h2>
      <div style="overflow-x:auto">
        <table v-if="ms.length">
          <thead><tr><th>#</th><th>机构</th><th>多头</th><th>日变</th><th>空头</th><th>日变</th><th>净持仓</th><th>期间净变</th></tr></thead>
          <tbody>
            <tr v-for="(m,i) in ms" :key="m.member_name">
              <td class="muted">{{ i+1 }}</td>
              <td>{{ m.member_name }}</td>
              <td>{{ fk(m.long_position) }}</td>
              <td :class="m.long_change>0?'up':'down'">{{ fc(m.long_change) }}</td>
              <td>{{ fk(m.short_position) }}</td>
              <td :class="m.short_change>0?'up':'down'">{{ fc(m.short_change) }}</td>
              <td :class="m.net_position>0?'up':'down'">{{ fk(m.net_position) }}</td>
              <td :class="m.period_net_chg>0?'up':'down'">{{ fc(m.period_net_chg) }}</td>
            </tr>
          </tbody>
        </table>
        <div v-else class="loading">暂无</div>
      </div>
    </div>
  </div>
</template>

<script>
import { getContractOI, getPositions, getMemberPositions, getMemberTrend, getAnalysis, triggerAnalysis, chatFollowup } from "../api";
import * as echarts from "echarts";

const cs = {tooltip:{trigger:"axis",confine:true,backgroundColor:"#171a24",borderColor:"#3a4050",textStyle:{color:"#e8ebf0",fontSize:12}},grid:{left:60,right:55,top:36,bottom:28},xAxis:{type:"category",axisLabel:{color:"#6b7080",fontSize:10},axisLine:{lineStyle:{color:"#252a35"}}},yAxis:[{type:"value",scale:true,axisLabel:{color:"#6b7080",fontSize:10},splitLine:{lineStyle:{color:"#1e2230"}}},{type:"value",axisLabel:{color:"#6b7080",fontSize:10,formatter:v=>(v/10000).toFixed(0)+"万"},splitLine:{show:false}}]};

export default {
  props:["code"],
  data(){return{variety:"",cur:"1m",d1:"",d2:"",periods:[{v:"1w",l:"1周"},{v:"2w",l:"2周"},{v:"1m",l:"1月"},{v:"3m",l:"3月"}],oi:[],pos:[],ms:[],md:"",tr:{},at:null,ap:"",al:false,ch:[],q:"",cl:false}},
  computed:{
    latest(){return this.oi.length?{close:this.oi[this.oi.length-1].close,high:this.oi[this.oi.length-1].high,low:this.oi[this.oi.length-1].low,open_interest:this.oi[this.oi.length-1].open_interest,volume:this.oi[this.oi.length-1].volume}:{close:0,high:0,low:0,open_interest:0,volume:0}},
    chg(){const l=this.oi.length;if(l<2)return 0;return this.oi[l-1].close-this.oi[l-2].close},
    chgPct(){const l=this.oi.length;if(l<2||this.oi[l-2].close===0)return 0;return(this.oi[l-1].close-this.oi[l-2].close)/this.oi[l-2].close*100},
    oiChg(){const l=this.oi.length;if(l<2)return 0;return this.oi[l-1].open_interest-this.oi[l-2].open_interest}
  },
  mounted(){this._load()},
  beforeUnmount(){this._charts?.forEach(c=>c?.dispose())},
  methods:{
    fk(n){return n?(n/10000).toFixed(1)+"万":"-"},
    fc(n){return n?(n>0?"+":"")+Number(n).toLocaleString():"0"},
    fmtVol(n){if(!n)return"0";return n>=10000?(n/10000).toFixed(1)+"万":Number(n).toLocaleString()},
    _params(){return this.d1&&this.d2?{start_date:this.d1,end_date:this.d2}:{period:this.cur}},
    _oiParams(){
      const p=this._params();
      if(p.period){
        const pad={ '1w':'1m', '2w':'3m', '1m':'6m', '3m':'1y' };
        return { period: pad[p.period] || '6m' };
      }
      if(p.start_date&&p.end_date){
        const s=new Date(p.start_date);s.setDate(s.getDate()-40);
        return { start_date: s.toISOString().slice(0,10), end_date: p.end_date };
      }
      return p;
    },
    async sw(v){this.cur=v;this.d1=this.d2="";await this._load()},
    async ap(){if(this.d1&&this.d2){this.cur="";await this._load()}},
    async _load(){
      const p=this._params(), op=this._oiParams();
      try{const[oi,ps,ms,tr,an]=await Promise.all([getContractOI(this.code,op),getPositions(this.code,p),getMemberPositions(this.code,p),getMemberTrend(this.code,"",p),getAnalysis(this.code)]);
        this.oi=oi.data.data||[];this.pos=ps.data.data||[];this.variety=ps.data.variety||ms.data.variety||"";this.ms=ms.data.members||[];this.md=ms.data.date||"";this.tr=tr.data.members||{};this.at=an.data.content||null;this.ap=an.data.period||null;
        this.$nextTick(()=>{this._r1();this._r2();this._r3();this._r4()})}catch(e){console.error(e)}
    },
    _opt(s,data){return Object.assign({},{...cs,legend:{data:s.map(x=>x.name),textStyle:{color:"#6b7080",fontSize:11},top:0},xAxis:{...cs.xAxis,data},series:s})},
    _r1(){
      const d=this.oi.map(r=>r.date);if(!d.length)return;
      const ohlc=this.oi.map(r=>[r.open,r.close,r.low,r.high]);
      const vols=this.oi.map(r=>r.volume);
      const ois=this.oi.map(r=>r.open_interest);
      const ma=(p,n)=>{const r=[];for(let i=0;i<p.length;i++){if(i<n-1){r.push(null);continue}let s=0;for(let j=0;j<n;j++)s+=p[i-j][1];r.push(+(s/n).toFixed(2))}return r};
      const up=(i)=>ohlc[i]&&ohlc[i][1]>=ohlc[i][0];
      this._charts=this._charts||[];this._charts[0]?.dispose();this._charts[0]=echarts.init(this.$refs.c1);
      this._charts[0].setOption({
        tooltip:{trigger:"axis",axisPointer:{type:"cross"},backgroundColor:"#12171d",borderColor:"#1e293b",padding:12,textStyle:{color:"#e2e8f0",fontSize:12},
          formatter:ps=>{
            if(!ps||!ps.length)return'';
            let h=`<div style="font-weight:600;margin-bottom:6px;font-size:12px;color:#94a3b8">${ps[0].axisValue}</div>`;
            const k=ps.find(p=>p.seriesName==='K线');
            if(k&&k.data){
              const up=k.data[1]>=k.data[0];
              const c=up?'#f43f5e':'#22c55e';
              h+=`<div style="font-size:13px;line-height:1.9"><span style="color:${c};font-weight:700">${k.data[1]}</span>`;
              h+=`<span style="color:${up?'#f43f5e':'#22c55e'};margin-left:6px;font-size:11px">${up?'+':''}${(k.data[1]-k.data[0]).toFixed(1)} (${(k.data[0]?((k.data[1]-k.data[0])/k.data[0]*100):0).toFixed(2)}%)</span></div>`;
              h+=`<table style="font-size:11px;line-height:1.6;margin-top:2px"><tr><td style="color:#64748b;padding-right:10px">开</td><td>${k.data[0]}</td><td style="color:#64748b;padding-left:10px;padding-right:10px">高</td><td>${k.data[2]}</td></tr>`;
              h+=`<tr><td style="color:#64748b">低</td><td>${k.data[3]}</td><td style="color:#64748b;padding-left:10px">幅</td><td>${((k.data[2]-k.data[3])/k.data[3]*100).toFixed(2)}%</td></tr></table>`;
            }
            for(const p of ps){
              if(p.seriesName==='K线'||p.seriesName==='持仓量'||p.value==null||p.value===undefined)continue;
              if(p.seriesName==='成交量')h+=`<div style="margin-top:4px;font-size:11px;color:#94a3b8">量 ${p.value>=10000?(p.value/10000).toFixed(1)+'万':p.value}</div>`;
            }
            return h;
          }
        },
        axisPointer:{link:[{xAxisIndex:"all"}]},
        legend:{data:["K线","MA5","MA10","MA20","持仓量","成交量"],textStyle:{color:"#6b7080",fontSize:11},top:0},
        // 25px reserved at bottom for the dataZoom slider, 6px gap between grids
        // 400px total height: 25 (slider) + 15 (second grid ~18%) + 6 (gap) + 280 (first grid ~60%) + 36 (top) + 38 (bottom padding)
        grid:[{left:60,right:55,top:34,height:"60%"},{left:60,right:55,top:"80%",height:"15%"}],
        dataZoom:[{type:"inside",xAxisIndex:[0,1],start:this.cur?65:0,end:100}],
        xAxis:[
          {type:"category",data:d,axisLabel:{color:"#6b7080",fontSize:10},axisLine:{lineStyle:{color:"#252a35"}},gridIndex:0},
          {type:"category",data:d,axisLabel:{show:false},axisTick:{show:false},axisLine:{lineStyle:{color:"#252a35"}},gridIndex:1}
        ],
        yAxis:[
          {type:"value",gridIndex:0,axisLabel:{color:"#6b7080",fontSize:10},splitLine:{lineStyle:{color:"#1e2230"}},scale:true},
          {type:"value",gridIndex:1,axisLabel:{color:"#6b7080",fontSize:10,formatter:v=>(v/10000).toFixed(0)+"万"},splitLine:{show:false}},
          {type:"value",gridIndex:0,axisLabel:{show:false},splitLine:{show:false},scale:true}
        ],
        series:[
          {name:"K线",type:"candlestick",data:ohlc,xAxisIndex:0,yAxisIndex:0,itemStyle:{color:"#ff5252",color0:"#4cd99b",borderColor:"#ff5252",borderColor0:"#4cd99b"}},
          {name:"MA5",type:"line",data:ma(ohlc,5),xAxisIndex:0,yAxisIndex:0,symbol:"none",lineStyle:{color:"#f4b740",width:1}},
          {name:"MA10",type:"line",data:ma(ohlc,10),xAxisIndex:0,yAxisIndex:0,symbol:"none",lineStyle:{color:"#ab47bc",width:1}},
          {name:"MA20",type:"line",data:ma(ohlc,20),xAxisIndex:0,yAxisIndex:0,symbol:"none",lineStyle:{color:"#64b5f6",width:1}},
          {name:"持仓量",type:"line",data:ois,xAxisIndex:0,yAxisIndex:2,symbol:"none",lineStyle:{color:"#7dd3fc",width:1.2,type:"dashed"}},
          {name:"成交量",type:"bar",data:vols,xAxisIndex:1,yAxisIndex:1,itemStyle:{color:p=>up(p.dataIndex)?"#ff5252":"#4cd99b"}}
        ]
      });
    },
    _r2(){
      const d=this.pos.map(r=>r.date);if(!d.length)return;
      this._charts=this._charts||[];this._charts[1]?.dispose();this._charts[1]=echarts.init(this.$refs.c2);
      this._charts[1].setOption(this._opt([
        {name:"多头",type:"line",data:this.pos.map(r=>r.long_position),lineStyle:{color:"#f43f5e",width:1.8},symbol:"none",areaStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:"rgba(244,63,94,.12)"},{offset:1,color:"rgba(244,63,94,0)"}])}},
        {name:"空头",type:"line",data:this.pos.map(r=>r.short_position),lineStyle:{color:"#22c55e",width:1.8},symbol:"none",areaStyle:{color:new echarts.graphic.LinearGradient(0,0,0,1,[{offset:0,color:"rgba(34,197,94,.12)"},{offset:1,color:"rgba(34,197,94,0)"}])}},
        {name:"净持仓",type:"bar",data:this.pos.map(r=>r.net_position),itemStyle:{color:p=>p.value>=0?"#f43f5e":"#22c55e"}}
      ],d));
    },
    _r3(){
      if(!this.ms.length)return;
      const nl=this.ms.filter(m=>m.net_position>0).sort((a,b)=>b.net_position-a.net_position).slice(0,5);
      const ns=this.ms.filter(m=>m.net_position<0).sort((a,b)=>a.net_position-b.net_position).slice(0,5).reverse();
      const names=[...ns.map(m=>m.member_name),...nl.map(m=>m.member_name)];
      const vals=[...ns.map(m=>-m.short_position),...nl.map(m=>m.long_position)];
      const cols=[...ns.map(()=>"#22c55e"),...nl.map(()=>"#f43f5e")];
      const labs=[...ns.map(m=>"净空"+(-m.net_position).toLocaleString()),...nl.map(m=>"净多"+m.net_position.toLocaleString())];
      this._charts=this._charts||[];this._charts[2]?.dispose();this._charts[2]=echarts.init(this.$refs.c3);
      this._charts[2].setOption({
        tooltip:{...cs.tooltip,axisPointer:{type:"shadow"},formatter:p=>{const m=this.ms.find(x=>x.member_name===p[0].name);return m?`${m.member_name}<br/>多头:${m.long_position.toLocaleString()} (${m.long_change>0?'+':''}${m.long_change})<br/>空头:${m.short_position.toLocaleString()} (${m.short_change>0?'+':''}${m.short_change})<br/>净:${m.net_position.toLocaleString()}`:p[0].name}},
        grid:{left:90,right:10,top:6,bottom:20},
        xAxis:{type:"value",axisLabel:{color:"#6b7080",fontSize:10,formatter:v=>(Math.abs(v)/10000).toFixed(0)+"万"},splitLine:{lineStyle:{color:"#1e2230"}}},
        yAxis:{type:"category",data:names,axisLabel:{color:"#6b7080",fontSize:10}},
        series:[{type:"bar",data:vals,itemStyle:{color:p=>cols[p.dataIndex],borderRadius:[0,3,3,0]},label:{show:true,position:"right",color:"#9ca0a8",fontSize:10,formatter:p=>labs[p.dataIndex]},barMaxWidth:20}]
      });
    },
    _r4(){
      if(!Object.keys(this.tr).length)return;
      const all=new Set();const clrs=["#3b82f6","#f43f5e","#22c55e","#eab308","#a855f7","#06b6d4","#f97316","#84cc16","#ec4899","#8b5cf6"];
      const ss=Object.entries(this.tr).slice(0,12).map(([n,d],i)=>{d.forEach(x=>all.add(x.date));return{name:n,type:"line",data:d.map(x=>[x.date,x.net]),smooth:true,symbol:"none",lineStyle:{width:2},itemStyle:{color:clrs[i%clrs.length]}}});
      this._charts=this._charts||[];this._charts[3]?.dispose();this._charts[3]=echarts.init(this.$refs.c4);
      this._charts[3].setOption({
        tooltip:cs.tooltip,
        legend:{type:"scroll",bottom:0,textStyle:{color:"#6b7080",fontSize:10}},
        grid:{left:55,right:10,top:6,bottom:44},
        xAxis:{type:"category",data:[...all].sort(),axisLabel:{color:"#6b7080",fontSize:10}},
        yAxis:{type:"value",axisLabel:{color:"#6b7080",fontSize:10,formatter:v=>(v/10000).toFixed(0)+"万"},splitLine:{lineStyle:{color:"#1e2230"}}},
        series:ss
      });
    },
    async analyze(){this.al=true;const p=this._params(),pl={contract_code:this.code};if(p.period)pl.period=p.period;else{pl.start_date=p.start_date;pl.end_date=p.end_date}try{const r=await triggerAnalysis(pl);this.at=r.data.content;this.ap=r.data.period}catch(e){}this.al=false},
    async cq(){if(!this.q.trim())return;const m=this.q;this.ch.push({role:"user",content:m});this.q="";this.cl=true;this.$nextTick(()=>{const b=this.$refs.cb;if(b)b.scrollTop=b.scrollHeight});try{const r=await chatFollowup({contract_code:this.code,question:m,analysis_context:this.at||"",history:this.ch.slice(-10)});this.ch.push({role:"assistant",content:r.data.reply})}catch(e){}this.cl=false;this.$nextTick(()=>{const b=this.$refs.cb;if(b)b.scrollTop=b.scrollHeight})}
  }
};
</script>

<style scoped>
.topbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.back-btn{font-size:12px;color:var(--txt3);padding:6px 12px;border-radius:var(--radius-sm)}
.back-btn:hover{color:var(--txt)}
.title{font-size:16px;font-weight:700;color:var(--txt);letter-spacing:-.3px}
.tag{font-size:10px;color:var(--txt3);background:var(--bg-elevated);padding:3px 10px;border-radius:var(--radius-sm);border:1px solid var(--border);font-weight:500}
.per-group{display:flex;border:1px solid var(--border);border-radius:var(--radius-sm);overflow:hidden}
.per-group button{border:none;border-radius:0;padding:5px 12px;font-size:11px}
.per-group button:not(:last-child){border-right:1px solid var(--border)}
.per-group button.on{background:var(--blue);color:#fff;border-color:var(--blue)}
.di{padding:6px 10px;font-size:11px;width:126px;background:var(--bg);color:var(--txt);border:1px solid var(--border);border-radius:var(--radius-sm)}
.muted{color:var(--txt3)}

.price-strip{display:flex;gap:1px;margin-top:14px;padding-top:14px;border-top:1px solid var(--border-light);overflow-x:auto}
.ps-item{flex:1;min-width:100px;text-align:center;padding:8px 12px;background:var(--bg-elevated);border-radius:var(--radius-sm);transition:all var(--transition)}
.ps-item:hover{background:var(--bg-card-hover)}
.ps-up{background:rgba(244,63,94,.08);border:1px solid rgba(244,63,94,.18)}
.ps-down{background:rgba(34,197,94,.08);border:1px solid rgba(34,197,94,.18)}
.ps-label{display:block;font-size:10px;color:var(--txt3);margin-bottom:4px}
.ps-val{display:block;font-size:14px;font-weight:700;color:var(--txt);font-variant-numeric:tabular-nums}

.report{white-space:pre-wrap;font-size:13px;line-height:1.85;color:var(--txt2);max-height:640px;overflow-y:auto}

.chat-section{margin-top:18px;padding-top:14px;border-top:1px solid var(--border-light)}
.chat-header{font-size:11px;font-weight:600;color:var(--txt3);margin-bottom:12px;text-transform:uppercase;letter-spacing:.4px}
.chatbox{max-height:300px;overflow-y:auto;padding-right:4px}
.msg{display:flex;gap:10px;margin-bottom:14px}
.msg-you{flex-direction:row-reverse}
.msg-label{font-size:10px;font-weight:600;color:var(--txt4);min-width:22px;padding-top:8px;text-align:center;flex-shrink:0}
.msg-you .msg-label{color:var(--blue)}
.msg-body{max-width:78%;padding:9px 14px;border-radius:var(--radius);font-size:12px;line-height:1.65;word-break:break-word}
.msg-ai .msg-body{background:var(--bg-elevated);color:var(--txt2);border:1px solid var(--border-light)}
.msg-you .msg-body{background:rgba(59,130,246,.1);color:var(--txt);border:1px solid rgba(59,130,246,.18)}
.typing-dots{display:flex;gap:5px;align-items:center;padding:11px 16px}
.typing-dots span{width:5px;height:5px;border-radius:50%;background:var(--txt4);animation:dot-bounce 1.4s ease-in-out infinite}
.typing-dots span:nth-child(2){animation-delay:.2s}
.typing-dots span:nth-child(3){animation-delay:.4s}
@keyframes dot-bounce{0%,80%,100%{opacity:.3;transform:scale(.7)}40%{opacity:1;transform:scale(1)}}
.ci{display:flex;gap:8px}
.ci input{flex:1;padding:9px 12px}
</style>
