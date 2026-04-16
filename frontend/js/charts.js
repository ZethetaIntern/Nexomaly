/* Chart.js wrappers */
Chart.defaults.color='#6b7f9e';
Chart.defaults.font.family="'Space Mono',monospace";
Chart.defaults.font.size=10;
const GRID='#1a2538';
let _trend=null,_dist=null;

function initTrendChart(id){
  const ctx=document.getElementById(id); if(!ctx)return;
  if(_trend){_trend.destroy();_trend=null;}
  _trend=new Chart(ctx,{
    type:'line',
    data:{labels:[],datasets:[
      {label:'High',  data:[],borderColor:'#ff3560',backgroundColor:'rgba(255,53,96,.07)',fill:true,tension:.4,borderWidth:1.5,pointRadius:0},
      {label:'Medium',data:[],borderColor:'#ffb020',backgroundColor:'rgba(255,176,32,.05)',fill:true,tension:.4,borderWidth:1.5,pointRadius:0},
      {label:'Low',   data:[],borderColor:'#00e080',backgroundColor:'rgba(0,224,128,.04)',fill:true,tension:.4,borderWidth:1.5,pointRadius:0},
    ]},
    options:{
      responsive:true,maintainAspectRatio:false,animation:{duration:350},
      interaction:{mode:'index',intersect:false},
      plugins:{
        legend:{display:true,position:'top',align:'end',labels:{boxWidth:7,boxHeight:7,padding:12,pointStyle:'circle',usePointStyle:true}},
        tooltip:{backgroundColor:'#0c1018',borderColor:'#1a2538',borderWidth:1}
      },
      scales:{x:{grid:{color:GRID},ticks:{maxTicksLimit:8,maxRotation:0}},
              y:{grid:{color:GRID},beginAtZero:true,ticks:{stepSize:1}}}
    }
  });
}

function updateTrendChart(data){
  if(!_trend)return;
  _trend.data.labels=data.map(d=>d.hour);
  _trend.data.datasets[0].data=data.map(d=>d.high);
  _trend.data.datasets[1].data=data.map(d=>d.medium);
  _trend.data.datasets[2].data=data.map(d=>d.low);
  _trend.update('none');
}

function initDistChart(id){
  const ctx=document.getElementById(id); if(!ctx)return;
  if(_dist){_dist.destroy();_dist=null;}
  _dist=new Chart(ctx,{
    type:'doughnut',
    data:{labels:['High','Medium','Low'],datasets:[{
      data:[0,0,0],
      backgroundColor:['rgba(255,53,96,.75)','rgba(255,176,32,.75)','rgba(0,224,128,.75)'],
      borderColor:['#ff3560','#ffb020','#00e080'],borderWidth:1,hoverOffset:3
    }]},
    options:{responsive:true,maintainAspectRatio:false,cutout:'65%',animation:{duration:350},
             plugins:{legend:{display:false},tooltip:{backgroundColor:'#0c1018',borderColor:'#1a2538',borderWidth:1}}}
  });
}

function updateDistChart(data){
  if(!_dist)return;
  _dist.data.datasets[0].data=[data.high||0,data.medium||0,data.low||0];
  _dist.update('none');
}

function renderMetricBars(containerId, metrics){
  const el=document.getElementById(containerId); if(!el)return;
  if(!metrics||!metrics.precision){
    el.innerHTML='<div class="empty" style="padding:20px"><div class="empty-title">No data yet</div></div>';
    return;
  }
  const bars=[
    {label:'Precision',    val:metrics.precision||0,    color:'var(--cyan)'},
    {label:'Recall',       val:metrics.recall||0,       color:'var(--green)'},
    {label:'F1 Score',     val:metrics.f1_score||0,     color:'var(--purple)'},
    {label:'Detection Rate',val:metrics.detection_rate||0,color:'var(--yellow)'},
    {label:'FP Rate',      val:metrics.fp_rate||0,      color:'var(--red)'},
    {label:'AUC-ROC',      val:metrics.auc_roc||0,      color:'var(--cyan)'},
  ];
  el.innerHTML=bars.map(b=>`
    <div class="metric-bar-row">
      <span class="metric-bar-label">${b.label}</span>
      <div class="metric-bar-track"><div class="metric-bar-fill" style="width:${(b.val*100).toFixed(1)}%;background:${b.color}"></div></div>
      <span class="metric-bar-val">${(b.val*100).toFixed(1)}%</span>
    </div>`).join('');
}

/* Gauge chart (SVG arc) */
function drawGauge(canvasId, value, color) {
  const el = document.getElementById(canvasId); if (!el) return;
  const pct  = Math.min(Math.max(value, 0), 100) / 100;
  const r    = 70, cx = 80, cy = 80;
  const start = Math.PI, end = 2 * Math.PI;
  const angle = start + pct * Math.PI;
  const x1 = cx + r * Math.cos(start),  y1 = cy + r * Math.sin(start);
  const x2 = cx + r * Math.cos(angle),  y2 = cy + r * Math.sin(angle);
  const large = pct > 0.5 ? 1 : 0;

  el.innerHTML = `
    <svg viewBox="0 0 160 90" xmlns="http://www.w3.org/2000/svg">
      <path d="M ${cx-r} ${cy} A ${r} ${r} 0 0 1 ${cx+r} ${cy}"
            stroke="#1a2538" stroke-width="10" fill="none" stroke-linecap="round"/>
      ${pct > 0 ? `<path d="M ${x1} ${y1} A ${r} ${r} 0 ${large} 1 ${x2} ${y2}"
            stroke="${color}" stroke-width="10" fill="none" stroke-linecap="round"/>` : ''}
    </svg>`;
}
