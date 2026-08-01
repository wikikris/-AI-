<template>
  <div>
    <div class="hh">
      <h2>聊天记录</h2>
      <button @click="clearAll" v-if="items.length" class="btn-clear">清空全部</button>
    </div>
    <div v-if="items.length" class="hlist">
      <div v-for="g in items" :key="g.code" class="hgroup card">
        <div class="hg-top" @click="g.open=!g.open">
          <span class="hg-code">{{ g.code }}</span>
          <span class="muted" style="font-size:10px;margin-left:8px">{{ g.chats.length }} 个对话</span>
          <span class="hg-arrow">{{ g.open?'▾':'▸' }}</span>
        </div>
        <template v-if="g.open">
          <div v-for="(c,i) in g.chats" :key="i" class="hg-row" @click="go(g.code,c.mode,c.period)">
            <span :class="['hg-tag',c.mode==='followup'?'hg-tag-fup':'hg-tag-fqa']">{{ c.label }}</span>
            <span class="hg-preview">{{ c.preview }}</span>
            <span class="muted" style="font-size:10px">{{ c.count }} 条</span>
            <button class="hg-del" @click.stop="del(c.key)">×</button>
          </div>
        </template>
      </div>
    </div>
    <div v-else class="loading">暂无聊天记录，在合约详情页开始对话</div>
  </div>
</template>

<script>
export default {
  data(){return{items:[]}},
  mounted(){this.load()},
  methods:{
    load(){
      const groups={};
      for(let i=0;i<localStorage.length;i++){
        const key=localStorage.key(i);
        // chat_RB2610_r_1m or chat_RB2610_free
        const match=key.match(/^chat_(.+?)_(r_.+|free)$/);
        if(!match)continue;
        try{
          const msgs=JSON.parse(localStorage.getItem(key));
          if(!msgs.length)continue;
          const code=match[1];
          const suffix=match[2];
          const isFree=suffix==='free';
          const period=isFree?'':suffix.replace(/^r_/,'');
          const userMsgs=msgs.filter(m=>m.role==='user');
          const preview=userMsgs.length?userMsgs[userMsgs.length-1].content.slice(0,40):(msgs[msgs.length-1]?.content?.slice(0,40)||'');
          const label=isFree?'自由问答':`报告 · ${period}`;
          if(!groups[code])groups[code]={code,chats:[],open:false};
          groups[code].chats.push({key,mode:isFree?'free':'followup',period,label,preview,count:msgs.length});
        }catch(e){}
      }
      // Sort chats within each group by mode then period
      for(const code in groups){
        groups[code].chats.sort((a,b)=>{
          if(a.mode!==b.mode)return a.mode==='free'?1:-1;
          return a.period.localeCompare(b.period);
        });
      }
      this.items=Object.values(groups).sort((a,b)=>a.code.localeCompare(b.code));
    },
    go(code,mode,period){
      this.$router.push(`/contract/${code}`);
      try{localStorage.setItem('_activeChatMode',mode)}catch(e){}
      if(period)try{localStorage.setItem('_activeChatPeriod',period)}catch(e){}
    },
    del(key){
      localStorage.removeItem(key);
      this.load();
    },
    clearAll(){
      if(!confirm('确定清空所有聊天记录？'))return;
      const keys=[];
      for(let i=0;i<localStorage.length;i++){
        const k=localStorage.key(i);
        if(k.match(/^chat_/))keys.push(k);
      }
      keys.forEach(k=>localStorage.removeItem(k));
      this.items=[];
    }
  }
};
</script>

<style scoped>
.hh{display:flex;align-items:center;justify-content:space-between;margin-bottom:16px}
.hh h2{font-size:14px;color:var(--txt2)}
.btn-clear{font-size:11px;color:var(--txt3);padding:4px 10px}
.btn-clear:hover{color:var(--red)}
.hlist{display:flex;flex-direction:column;gap:6px}
.hgroup{padding:0 !important;overflow:hidden}
.hg-top{display:flex;align-items:center;gap:8px;padding:14px 18px;cursor:pointer;transition:background var(--transition);user-select:none}
.hg-top:hover{background:rgba(255,255,255,.02)}
.hg-code{font-size:15px;font-weight:700;color:var(--txt)}
.hg-arrow{margin-left:auto;font-size:14px;color:var(--txt4)}
.hg-row{display:flex;align-items:center;gap:8px;padding:10px 18px 10px 36px;cursor:pointer;border-top:1px solid var(--border-light);transition:background var(--transition)}
.hg-row:hover{background:rgba(255,255,255,.02)}
.hg-tag{font-size:10px;padding:2px 7px;border-radius:3px;font-weight:600;white-space:nowrap}
.hg-tag-fup{background:rgba(168,85,247,.12);color:var(--purple)}
.hg-tag-fqa{background:rgba(6,182,212,.12);color:var(--cyan)}
.hg-preview{flex:1;font-size:12px;color:var(--txt3);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.hg-del{background:none;border:none;color:var(--txt4);font-size:14px;cursor:pointer;padding:0 4px;line-height:1}
.hg-del:hover{color:var(--red)}
</style>
