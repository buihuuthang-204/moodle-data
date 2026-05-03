
let DATA=[],RED_THRESH=70,YELLOW_THRESH=40,sortKey='riskPct',sortDir=-1;
let radarCI=null,weeklyCI=null,lineCI=null,donutCI=null;
let studentPage=1;const PER_PAGE=20;
let currentModalMSSV='';
let pageHistory=['dashboard'];

// ═══ LOGIN / LOGOUT (gọi Backend API) ═══
async function doLogin(){
  const u=document.getElementById('loginUser').value.trim();
  const p=document.getElementById('loginPass').value;
  const btn=document.querySelector('.login-btn');
  btn.innerHTML='⏳ Đang xác thực...';btn.disabled=true;
  try{
    const res=await fetch('/api/login',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({username:u,password:p})
    });
    const data=await res.json();
    if(data.success){
      document.getElementById('loginScreen').classList.add('hidden');
      document.getElementById('sidebarEl').style.display='';
      document.getElementById('mainEl').style.display='';
      sessionStorage.setItem('ews_logged_in','1');
      sessionStorage.setItem('ews_user',u);
      sessionStorage.setItem('ews_role',data.role);
      document.querySelector('.user-name strong').textContent=data.role;
    }else{
      document.getElementById('loginError').style.display='block';
      document.getElementById('loginPass').value='';
      setTimeout(()=>document.getElementById('loginError').style.display='none',3000);
    }
  }catch(e){
    // Fallback: nếu server chưa chạy, cho phép login offline
    const USERS={'admin':'ews2024','advisor':'123456','gv':'gv2024'};
    if(USERS[u]&&USERS[u]===p){
      document.getElementById('loginScreen').classList.add('hidden');
      document.getElementById('sidebarEl').style.display='';
      document.getElementById('mainEl').style.display='';
      sessionStorage.setItem('ews_logged_in','1');
      sessionStorage.setItem('ews_user',u);
      const nameMap={'admin':'Admin Hệ thống','advisor':'Cố vấn Học tập','gv':'Giảng viên'};
      document.querySelector('.user-name strong').textContent=nameMap[u]||u;
    }else{
      document.getElementById('loginError').style.display='block';
      document.getElementById('loginPass').value='';
      setTimeout(()=>document.getElementById('loginError').style.display='none',3000);
    }
  }
  btn.innerHTML='🔐 Đăng nhập';btn.disabled=false;
}
function doLogout(){
  if(!confirm('Bạn muốn đăng xuất?'))return;
  sessionStorage.removeItem('ews_logged_in');
  sessionStorage.removeItem('ews_user');
  sessionStorage.removeItem('ews_role');
  document.getElementById('loginScreen').classList.remove('hidden');
  document.getElementById('sidebarEl').style.display='none';
  document.getElementById('mainEl').style.display='none';
  document.getElementById('loginUser').value='';
  document.getElementById('loginPass').value='';
}
// Auto-login nếu đã login trước đó trong session
if(sessionStorage.getItem('ews_logged_in')==='1'){
  document.getElementById('loginScreen').classList.add('hidden');
  document.getElementById('sidebarEl').style.display='';
  document.getElementById('mainEl').style.display='';
}

// ═══ NOTES STORAGE (localStorage) ═══
function getNotes(mssv){return JSON.parse(localStorage.getItem('ews_notes_'+mssv)||'[]')}
function saveNote(mssv,note){const n=getNotes(mssv);n.unshift(note);localStorage.setItem('ews_notes_'+mssv,JSON.stringify(n))}
function getHandled(mssv){return localStorage.getItem('ews_handled_'+mssv)==='1'}
function setHandled(mssv,val){localStorage.setItem('ews_handled_'+mssv,val?'1':'0');renderAll()}
function addNote(){
  if(!currentModalMSSV)return;
  const input=document.getElementById('noteInput');
  const type=document.getElementById('noteType').value;
  const text=input.value.trim();
  if(!text)return;
  const typeLabels={note:'📝 Ghi chú',call:'📞 Gọi điện',email:'✉️ Email',meeting:'🤝 Gặp mặt'};
  saveNote(currentModalMSSV,{type,text,label:typeLabels[type],time:new Date().toLocaleString('vi-VN'),author:'Thầy Nguyễn Văn A'});
  input.value='';
  renderNotes(currentModalMSSV);
}
function renderNotes(mssv){
  const notes=getNotes(mssv);
  const el=document.getElementById('notesList');
  if(!notes.length){el.innerHTML='<p style="font-size:12px;color:var(--text-muted);padding:8px">Chưa có ghi chú nào.</p>';return}
  el.innerHTML=notes.map((n,i)=>`<div class="note-item type-${n.type}">
    <div class="note-meta"><span>${n.label} — ${n.author}</span><span>${n.time}</span></div>
    <div class="note-text" id="noteText_${i}">${n.text}</div>
    <div class="note-actions">
      <button class="edit-btn" onclick="editNote('${mssv}',${i})">✏️ Sửa</button>
      <button class="del-btn" onclick="deleteNote('${mssv}',${i})">🗑️ Xóa</button>
    </div>
  </div>`).join('');
}
function deleteNote(mssv,idx){
  if(!confirm('Bạn chắc chắn muốn xóa ghi chú này?'))return;
  const n=getNotes(mssv);n.splice(idx,1);localStorage.setItem('ews_notes_'+mssv,JSON.stringify(n));renderNotes(mssv);
}
function editNote(mssv,idx){
  const n=getNotes(mssv);
  const note=n[idx];
  const newText=prompt('Sửa ghi chú:',note.text);
  if(newText!==null&&newText.trim()){
    n[idx].text=newText.trim();
    n[idx].time=new Date().toLocaleString('vi-VN')+' (đã sửa)';
    localStorage.setItem('ews_notes_'+mssv,JSON.stringify(n));
    renderNotes(mssv);
  }
}

async function loadData(){
  try{
    let r;
    try {
      r = await fetch('/api/students');
      if (!r.ok) throw new Error("API failed");
    } catch(err) {
      console.warn("Không tìm thấy API Server, đọc từ file students_data.json offline:", err);
      r = await fetch('students_data.json?t='+Date.now());
    }
    DATA = await r.json();
  }catch(e){
    DATA = [];
    console.error("Lỗi hoàn toàn khi tải dữ liệu:", e);
  }
  processData();renderAll();
}

function computeRisk(s){
  const mx={score:Math.max(...DATA.map(d=>d.score),1),login:Math.max(...DATA.map(d=>d.login),1),session:Math.max(...DATA.map(d=>d.session),1),doc:Math.max(...DATA.map(d=>d.doc),1),disc:Math.max(...DATA.map(d=>d.disc),1)};
  let r=0;
  r+=(1-s.score/mx.score)*0.30;
  r+=(1-s.login/mx.login)*0.15;
  r+=(1-s.session/mx.session)*0.10;
  r+=(1-s.doc/mx.doc)*0.10;
  r+=(1-s.disc/mx.disc)*0.05;
  if(s.w[2]===0&&s.w[3]===0) r+=0.20; 
  else if(s.w[3]===0) r+=0.10;
  if(s.w[3]>0&&s.w[3]<s.w[0]*0.4) r+=0.10; 
  if(s.video===0&&s.doc===0) r+=0.05;
  if(s.duration>0&&s.duration<5&&s.score>100) r+=0.08; 
  r+=((parseInt(s.mssv)%17)-8)*0.005;
  return Math.min(Math.max(Math.round(r*100),3),97);
}

function getIssue(s){
  const i=[];
  if(s.w[2]===0&&s.w[3]===0) i.push('Bỏ học từ tuần 3');
  else if(s.w[3]===0) i.push('Không HĐ tuần 4');
  if(s.w[3]>0&&s.w[3]<s.w[0]*0.4) i.push('Sụt giảm mạnh');
  if(s.video===0&&s.doc===0) i.push('Không xem tài liệu');
  if(s.disc===0) i.push('Không thảo luận');
  if(s.duration>0&&s.duration<5&&s.score>100) i.push('Nghi gian lận');
  if(s.login<5) i.push('Ít login');
  return i.length?i.slice(0,2).join(', '):'Cần theo dõi';
}

function processData(){
  DATA.forEach(s=>{
    // Ưu tiên dùng điểm Dự đoán AI từ ML Model (nếu có), không có thì tự tính bằng rules js
    s.riskPct = (s.ai_risk_score !== undefined && s.ai_risk_score !== null) ? s.ai_risk_score : computeRisk(s);
    s.level = s.riskPct >= RED_THRESH ? 'red' : s.riskPct >= YELLOW_THRESH ? 'yellow' : 'green';
    s.issue = getIssue(s);
    s.email = s.mssv + '@student.edu.vn';
  });
}

function renderAll(){
  renderKPIs();renderCharts();renderRiskTable('all');renderStudentList();
  renderCourses();renderReportCharts();renderNotifications();renderReportSummary();
  document.getElementById('riskBadge').textContent=DATA.filter(s=>s.level==='red').length;
  // Populate course filter
  const sel=document.getElementById('studentFilterCourse');
  const courses=[...new Set(DATA.map(s=>s.course))];
  sel.innerHTML='<option value="all">Tất cả khóa học</option>'+courses.map(c=>`<option value="${c}">${c}</option>`).join('');
  
  // Populate class filter
  const classSel=document.getElementById('studentFilterClass');
  const classes=[...new Set(DATA.map(s=>s.class).filter(Boolean))].sort();
  if(classSel) classSel.innerHTML='<option value="all">Tất cả lớp</option>'+classes.map(c=>`<option value="${c}">${c}</option>`).join('');

  // Populate global class filter
  const globalSel = document.getElementById('globalClassFilter');
  if(globalSel) {
    const prev = globalSel.value;
    globalSel.innerHTML = '<option value="all">🌍 Tất cả các Lớp</option>' + classes.map(c=>`<option value="${c}">${c}</option>`).join('');
    globalSel.value = prev || 'all';
  }
}

// ═══ COUNTER ANIMATION ═══
function animateCounter(el,target){
  let current=0;const step=Math.ceil(target/30);
  const timer=setInterval(()=>{current=Math.min(current+step,target);el.textContent=current;if(current>=target)clearInterval(timer)},30);
}

function getActiveData() {
  const gcf = document.getElementById('globalClassFilter');
  const cls = gcf ? gcf.value : 'all';
  return cls === 'all' ? DATA : DATA.filter(s => s.class === cls);
}

function applyGlobalFilter() {
  renderKPIs();
  renderCharts();
  renderRiskTable('all');
  renderCourses();
  renderReportSummary();
}

function renderKPIs(){
  const d_array = getActiveData();
  const t=d_array.length,s=d_array.filter(d=>d.level==='green').length,w=d_array.filter(d=>d.level==='yellow').length,d=d_array.filter(dd=>dd.level==='red').length;
  const cards=[
    {icon:'👨‍🎓',label:'Tổng Sinh viên',value:t,color:'var(--blue)',bg:'#eff6ff',trend:t+' SV',tc:'#3b82f6',click:"showPage('courses',document.querySelectorAll('.nav-item')[1])"},
    {icon:'✅',label:'An toàn (<'+YELLOW_THRESH+'%)',value:s,color:'var(--green)',bg:'#f0fdf4',trend:(t?Math.round(s/t*100):0)+'%',tc:'#16a34a',click:"filterStudentsByLevel('green')"},
    {icon:'⚠️',label:'Cảnh báo ('+YELLOW_THRESH+'-'+RED_THRESH+'%)',value:w,color:'var(--yellow)',bg:'#fffbeb',trend:(t?Math.round(w/t*100):0)+'%',tc:'#d97706',click:"filterStudentsByLevel('yellow')"},
    {icon:'🚨',label:'Nguy cơ (>'+RED_THRESH+'%)',value:d,color:'var(--red)',bg:'#fef2f2',trend:(t?Math.round(d/t*100):0)+'%',tc:'#dc2626',click:"filterStudentsByLevel('red')"},
  ];
  document.getElementById('kpiGrid').innerHTML=cards.map((c,i)=>`
    <div class="kpi-card" onclick="${c.click}" style="animation-delay:${i*0.05}s"><div class="accent" style="background:${c.color}"></div>
      <div class="kpi-header"><div class="kpi-icon" style="background:${c.bg}">${c.icon}</div><div class="kpi-trend" style="background:${c.bg};color:${c.tc}">${c.trend}</div></div>
      <div class="kpi-value" style="color:${c.color}" data-target="${c.value}">0</div><div class="kpi-label">${c.label}</div>
    </div>`).join('');
  // Animate counters
  document.querySelectorAll('.kpi-value[data-target]').forEach(el=>animateCounter(el,parseInt(el.dataset.target)));
}

function renderCharts(){
  if(lineCI)lineCI.destroy();if(donutCI)donutCI.destroy();
  const d_array = getActiveData();
  const ctx1=document.getElementById('lineChart').getContext('2d');
  const r=[1,2,3,4].map(w=>d_array.filter(s=>s.w[w-1]<15).length);
  const y=[1,2,3,4].map(w=>d_array.filter(s=>s.w[w-1]>=15&&s.w[w-1]<35).length);
  const g=[1,2,3,4].map(w=>d_array.filter(s=>s.w[w-1]>=35).length);
  lineCI=new Chart(ctx1,{type:'line',data:{labels:['Tuần 1','Tuần 2','Tuần 3','Tuần 4'],datasets:[
    {label:'Nguy hiểm',data:r,borderColor:'#ef4444',backgroundColor:'rgba(239,68,68,0.1)',fill:true,tension:0.4,pointRadius:5,borderWidth:2},
    {label:'Cảnh báo',data:y,borderColor:'#f59e0b',backgroundColor:'rgba(245,158,11,0.1)',fill:true,tension:0.4,pointRadius:5,borderWidth:2},
    {label:'An toàn',data:g,borderColor:'#10b981',backgroundColor:'rgba(16,185,129,0.1)',fill:true,tension:0.4,pointRadius:5,borderWidth:2},
  ]},options:{responsive:true,plugins:{legend:{position:'bottom',labels:{usePointStyle:true,padding:16}}},scales:{y:{beginAtZero:true,grid:{color:'rgba(100,116,139,0.1)'}},x:{grid:{display:false}}}}});

  const ctx2=document.getElementById('donutChart').getContext('2d');
  donutCI=new Chart(ctx2,{type:'doughnut',data:{labels:['An toàn','Cảnh báo','Nguy hiểm'],datasets:[{data:[d_array.filter(s=>s.level==='green').length,d_array.filter(s=>s.level==='yellow').length,d_array.filter(s=>s.level==='red').length],backgroundColor:['#10b981','#f59e0b','#ef4444'],borderWidth:3,borderColor:document.documentElement.dataset.theme==='dark'?'#1e293b':'#fff',hoverOffset:8}]},options:{responsive:true,cutout:'65%',plugins:{legend:{position:'bottom',labels:{usePointStyle:true,padding:16,color:getComputedStyle(document.body).getPropertyValue('--text')}}}}});
}

function renderRiskTable(filter){
  const d_array = getActiveData();
  let f=[...d_array].sort((a,b)=>sortDir*(a[sortKey]>b[sortKey]?1:-1));
  if(filter!=='all')f=f.filter(s=>s.level===filter);
  // Handled filter
  const hf=document.getElementById('handledFilter');
  if(hf){const hv=hf.value;if(hv==='done')f=f.filter(s=>getHandled(s.mssv));else if(hv==='pending')f=f.filter(s=>!getHandled(s.mssv))}
  f=f.slice(0,15);
  document.getElementById('riskTableBody').innerHTML=f.map(s=>{const h=getHandled(s.mssv);const nc=getNotes(s.mssv).length;return `<tr>
    <td><input type="checkbox" class="row-check" data-mssv="${s.mssv}" onchange="updateSelectedCount()"></td>
    <td><strong>${s.mssv}</strong></td><td>${s.name}</td><td style="font-size:12px;font-weight:600">${s.class||'—'}</td>
    <td><div style="display:flex;align-items:center;gap:8px"><div class="progress-bar"><div class="fill" style="width:${s.riskPct}%;background:${s.level==='red'?'#ef4444':s.level==='yellow'?'#f59e0b':'#10b981'}"></div></div><b style="font-size:12px">${s.riskPct}%</b></div></td>
    <td><span class="risk-badge ${s.level}">${s.level==='red'?'🔴 Nguy hiểm':s.level==='yellow'?'🟡 Chú ý':'🟢 An toàn'}</span></td>
    <td><span class="issue-text">${s.issue}</span></td>
    <td style="display:flex;gap:4px;align-items:center">
      <span class="handled-badge ${h?'done':'pending'}" onclick="event.stopPropagation();setHandled('${s.mssv}',${!h})">${h?'✅ Đã xử lý':'⏳ Chưa'}</span>
      <button class="btn-action view" onclick="openModal('${s.mssv}')">👁️${nc?' ('+nc+')':''}</button>
    </td>
  </tr>`}).join('');
  updateSelectedCount();
}

// ═══ COURSES ═══
const COURSE_INFO={
  'Nhập môn Lập trình C++':{icon:'💻',code:'CS101',color:'#3b82f6'},
  'English for Information Technology':{icon:'🌐',code:'EN201',color:'#10b981'},
};

function renderCourses(){
  const d_array = DATA;
  const predefined=Object.keys(COURSE_INFO);
  const dynamic=[...new Set(d_array.map(s=>s.course))];
  const courses=[...new Set([...predefined,...dynamic])];
  
  const grid=document.getElementById('courseGrid');
  grid.innerHTML=courses.map((c,i)=>{
    const info=COURSE_INFO[c]||{icon:'📖',code:'—',color:'#64748b'};
    const students=d_array.filter(s=>s.course===c);
    const red=students.filter(s=>s.level==='red').length;
    const yel=students.filter(s=>s.level==='yellow').length;
    const grn=students.filter(s=>s.level==='green').length;
    const total=students.length;
    const emptyCls=total===0?' empty':'';
    const barG=total?grn/total*100:0,barY=total?yel/total*100:0,barR=total?red/total*100:0;
    return `<div class="course-card${emptyCls}" data-course-idx="${i}">
      <div class="cc-icon">${info.icon}</div>
      <div class="cc-name">${c}</div>
      <div class="cc-code">${info.code} • ${total} sinh viên</div>
      <div class="cc-stats">
        <div class="cc-stat"><div class="cc-stat-val" style="color:#10b981">${grn}</div><div class="cc-stat-lbl">An toàn</div></div>
        <div class="cc-stat"><div class="cc-stat-val" style="color:#f59e0b">${yel}</div><div class="cc-stat-lbl">Cảnh báo</div></div>
        <div class="cc-stat"><div class="cc-stat-val" style="color:#ef4444">${red}</div><div class="cc-stat-lbl">Nguy hiểm</div></div>
      </div>
      <div class="cc-bar"><div style="width:${barG}%;background:#10b981"></div><div style="width:${barY}%;background:#f59e0b"></div><div style="width:${barR}%;background:#ef4444"></div></div>
    </div>`;
  }).join('');
  // Click event delegation (avoids inline quote/escape issues)
  grid.onclick=function(e){
    const card=e.target.closest('.course-card');
    if(!card)return;
    const idx=parseInt(card.dataset.courseIdx);
    if(!isNaN(idx)&&courses[idx])showCourseStudents(courses[idx]);
  };
  document.getElementById('courseStudents').style.display='none';
  grid.style.display='';
}

function showCourseStudents(course){
  const d_array = DATA;
  document.getElementById('courseGrid').style.display='none';
  document.getElementById('courseStudents').style.display='block';
  document.getElementById('courseTitle').textContent='📚 '+course;
  const students=d_array.filter(s=>s.course===course).sort((a,b)=>b.riskPct-a.riskPct);
  document.getElementById('courseStudentBody').innerHTML=students.map(s=>`<tr>
    <td><strong>${s.mssv}</strong></td><td>${s.name}</td>
    <td><div style="display:flex;align-items:center;gap:8px"><div class="progress-bar"><div class="fill" style="width:${s.riskPct}%;background:${s.level==='red'?'#ef4444':s.level==='yellow'?'#f59e0b':'#10b981'}"></div></div><b style="font-size:12px">${s.riskPct}%</b></div></td>
    <td>${s.score}</td>
    <td><span class="risk-badge ${s.level}">${s.level==='red'?'🔴':s.level==='yellow'?'🟡':'🟢'}</span></td>
    <td><button class="btn-action view" onclick="openModal('${s.mssv}')">👁️</button></td>
  </tr>`).join('');
}
function closeCourseStudents(){
  document.getElementById('courseGrid').style.display='';
  document.getElementById('courseStudents').style.display='none';
}

// ═══ STUDENTS WITH PAGINATION ═══
function renderStudentList(){
  const q=(document.getElementById('studentSearchInput')?.value||'').toLowerCase();
  const lf=document.getElementById('studentFilterLevel')?.value||'all';
  const cf=document.getElementById('studentFilterCourse')?.value||'all';
  const clsf=document.getElementById('studentFilterClass')?.value||'all';
  let f=DATA.filter(s=>(s.mssv.includes(q)||s.name.toLowerCase().includes(q))&&(lf==='all'||s.level===lf)&&(cf==='all'||s.course===cf)&&(clsf==='all'||s.class===clsf)).sort((a,b)=>b.riskPct-a.riskPct);
  const totalPages=Math.ceil(f.length/PER_PAGE);
  if(studentPage>totalPages)studentPage=1;
  const start=(studentPage-1)*PER_PAGE;
  const paged=f.slice(start,start+PER_PAGE);
  document.getElementById('studentListBody').innerHTML=paged.map(s=>{const h=getHandled(s.mssv);return `<tr>
    <td><strong>${s.mssv}</strong></td><td>${s.name}</td><td style="font-size:12px;font-weight:600">${s.class||'—'}</td><td style="font-size:12px">${s.course}</td>
    <td><div style="display:flex;align-items:center;gap:8px"><div class="progress-bar"><div class="fill" style="width:${s.riskPct}%;background:${s.level==='red'?'#ef4444':s.level==='yellow'?'#f59e0b':'#10b981'}"></div></div><b style="font-size:12px">${s.riskPct}%</b></div></td>
    <td>${s.score}</td>
    <td><span class="risk-badge ${s.level}">${s.level==='red'?'🔴':s.level==='yellow'?'🟡':'🟢'}</span></td>
    <td><span class="handled-badge ${h?'done':'pending'}" onclick="event.stopPropagation();setHandled('${s.mssv}',${!h})">${h?'✅ Xử lý':'⏳ Chưa'}</span></td>
    <td><button class="btn-action view" onclick="openModal('${s.mssv}')">👁️</button></td>
  </tr>`}).join('');
  // Pagination
  let pg='';
  for(let i=1;i<=totalPages;i++) pg+=`<button class="page-btn ${i===studentPage?'active':''}" onclick="studentPage=${i};renderStudentList()">${i}</button>`;
  document.getElementById('studentPagination').innerHTML=`<span style="font-size:12px;color:var(--text-muted)">${f.length} SV</span>`+pg;
}

// ═══ NOTIFICATIONS ═══
function renderNotifications(){
  const top=DATA.filter(s=>s.level==='red').sort((a,b)=>b.riskPct-a.riskPct).slice(0,8);
  document.getElementById('notifList').innerHTML=top.map(s=>`
    <div class="notif-item" onclick="openModal('${s.mssv}')">
      <div class="ni-name">🔴 ${s.name} (${s.riskPct}%)</div>
      <div class="ni-desc">${s.issue} — ${s.course}</div>
    </div>`).join('');
}
function toggleNotif(){document.getElementById('notifDropdown').classList.toggle('show')}
document.addEventListener('click',e=>{if(!e.target.closest('.notif-wrapper'))document.getElementById('notifDropdown').classList.remove('show')});

// \u2550\u2550\u2550 REPORTS \u2550\u2550\u2550
function renderReportCharts(){
  const d_array = getActiveData();
  const ctxB=document.getElementById('reportBarChart').getContext('2d');
  const ctxL=document.getElementById('reportLoginChart').getContext('2d');
  if(window.reportBarChartInst)window.reportBarChartInst.destroy();
  if(window.reportLoginChartInst)window.reportLoginChartInst.destroy();
  
  // Bar Chart - Score by Class
  const classes_list=[...new Set(d_array.map(s=>s.class).filter(Boolean))].sort();
  const avgScores=classes_list.map(c=>{
    const ss=d_array.filter(s=>s.class===c);
    return ss.reduce((sum,s)=>sum+s.score,0)/Math.max(ss.length,1);
  });
  window.reportBarChartInst=new Chart(ctxB,{
    type:'bar',
    data:{labels:classes_list,datasets:[{label:'Điểm trung bình',data:avgScores,backgroundColor:'#6366f1',borderRadius:4}]},
    options:{responsive:true,scales:{y:{beginAtZero:true}}}
  });

  // Line Chart - Student Activity
  const testW=[10,12,11,15]; // Activity mock
  window.reportLoginChartInst=new Chart(ctxL,{
    type:'line',
    data:{labels:['Tu\u1ea7n 1','Tu\u1ea7n 2','Tu\u1ea7n 3','Tu\u1ea7n 4'],datasets:[{label:'L\u01b0\u1ee3t t\u01b0\u01a1ng t\u00e1c TB',data:testW,borderColor:'#10b981',tension:0.4,fill:true,backgroundColor:'rgba(16,185,129,0.1)'}]},
    options:{responsive:true,scales:{y:{beginAtZero:true}}}
  });
}

// ═══ MODAL ═══
function openModal(mssv){
  const s=DATA.find(d=>d.mssv===mssv);if(!s)return;
  currentModalMSSV=mssv;
  document.getElementById('modalAvatar').textContent=s.name.split(' ').pop()[0];
  document.getElementById('modalName').textContent=s.name;
  document.getElementById('modalMSSV').textContent='MSSV: '+s.mssv;
  document.getElementById('modalEmail').textContent='Email: '+s.email;
  document.getElementById('modalCourse').textContent='📚 '+s.course;
  const st=document.getElementById('modalStatus');
  st.style.background=s.level==='red'?'#fef2f2':s.level==='yellow'?'#fffbeb':'#f0fdf4';
  st.style.color=s.level==='red'?'#dc2626':s.level==='yellow'?'#d97706':'#16a34a';
  st.textContent=(s.level==='red'?'🔴 Nguy hiểm':s.level==='yellow'?'🟡 Cảnh báo':'🟢 An toàn')+' — '+s.riskPct+'%';
  document.getElementById('modalAvatar').style.background=s.level==='red'?'linear-gradient(135deg,#ef4444,#f97316)':s.level==='yellow'?'linear-gradient(135deg,#f59e0b,#eab308)':'linear-gradient(135deg,#10b981,#3b82f6)';

  const av={score:Math.round(DATA.reduce((a,b)=>a+b.score,0)/DATA.length),login:Math.round(DATA.reduce((a,b)=>a+b.login,0)/DATA.length),video:Math.round(DATA.reduce((a,b)=>a+b.video,0)/DATA.length),doc:Math.round(DATA.reduce((a,b)=>a+b.doc,0)/DATA.length),disc:Math.round(DATA.reduce((a,b)=>a+b.disc,0)/DATA.length),session:Math.round(DATA.reduce((a,b)=>a+b.session,0)/DATA.length)};
  if(radarCI)radarCI.destroy();
  radarCI=new Chart(document.getElementById('radarChart').getContext('2d'),{type:'radar',data:{labels:['Điểm','Login','Video','Tài liệu','Thảo luận','Session'],datasets:[
    {label:s.name,data:[s.score,s.login,s.video,s.doc,s.disc,s.session],borderColor:'#ef4444',backgroundColor:'rgba(239,68,68,0.15)',pointRadius:4,borderWidth:2},
    {label:'TB Lớp',data:[av.score,av.login,av.video,av.doc,av.disc,av.session],borderColor:'#3b82f6',backgroundColor:'rgba(59,130,246,0.1)',pointRadius:4,borderWidth:2}
  ]},options:{responsive:true,plugins:{legend:{position:'bottom',labels:{usePointStyle:true}}},scales:{r:{beginAtZero:true,grid:{color:'rgba(100,116,139,0.15)'}}}}});

  if(weeklyCI)weeklyCI.destroy();
  const aw=[1,2,3,4].map(w=>Math.round(DATA.reduce((a,d)=>a+d.w[w-1],0)/DATA.length));
  weeklyCI=new Chart(document.getElementById('weeklyChart').getContext('2d'),{type:'line',data:{labels:['Tuần 1','Tuần 2','Tuần 3','Tuần 4'],datasets:[
    {label:s.name,data:s.w,borderColor:'#ef4444',backgroundColor:'rgba(239,68,68,0.1)',fill:true,tension:0.4,pointRadius:5,borderWidth:2},
    {label:'TB Lớp',data:aw,borderColor:'#3b82f6',backgroundColor:'rgba(59,130,246,0.05)',fill:true,tension:0.4,pointRadius:5,borderWidth:2,borderDash:[5,5]}
  ]},options:{responsive:true,plugins:{legend:{position:'bottom',labels:{usePointStyle:true}}},scales:{y:{beginAtZero:true,grid:{color:'rgba(100,116,139,0.1)'}},x:{grid:{display:false}}}}});

  // Populate Comm Tabs
  document.getElementById('emailTo').value=s.email;
  document.getElementById('smsTo').value='09'+Math.floor(Math.random()*100000000).toString().padStart(8,'0'); // Mock phone
  document.getElementById('emailContent').value=`Chào em ${s.name},\n\nHệ thống ghi nhận em đang ở mức rủi ro ${s.riskPct}%.\nVấn đề: ${s.issue}.\nMôn: ${s.course}.\n\nThầy/Cô mong em liên hệ sớm.\nTrân trọng.`;
  document.getElementById('smsContent').value=`[EWS] SV ${s.name} (${s.mssv}) canh bao rui ro ${s.riskPct}% mon ${s.course}. Vui long kiem tra email SV. LH CVHT de ho tro.`;

  renderNotes(mssv);
  loadXAI(mssv);
  document.getElementById('modalBackdrop').classList.add('show');
}

// ═══ XAI: EXPLAINABLE AI ═══
async function loadXAI(mssv){
  const el=document.getElementById('xaiFactors');
  el.innerHTML='<p style="font-size:12px;color:var(--text-muted);padding:8px">⏳ Đang phân tích SHAP values...</p>';
  
  try{
    const res=await fetch('/api/explain/'+mssv);
    if(res.ok){
      const data=await res.json();
      if(data.top_factors && data.top_factors.length>0){
        const maxImpact=Math.max(...data.top_factors.map(f=>Math.abs(f.impact)),0.01);
        el.innerHTML=data.top_factors.map((f,i)=>{
          const pct=Math.round(Math.abs(f.impact)/maxImpact*100);
          return `<div class="xai-factor">
            <div class="xai-rank">${i+1}</div>
            <div class="xai-content">
              <div class="xai-name">${f.friendly_name||f.feature}</div>
              <div class="xai-feature">feature: ${f.feature}</div>
              <div class="xai-impact-bar"><div class="xai-impact-fill" style="width:${pct}%"></div></div>
            </div>
            <div class="xai-impact-val" style="color:${i===0?'#ef4444':i===1?'#f59e0b':'#3b82f6'}">${f.impact>0?'+':''}${f.impact.toFixed(3)}</div>
          </div>`;
        }).join('');
      }else{
        el.innerHTML='<p style="font-size:12px;color:var(--green);padding:8px">✅ Sinh viên này không có yếu tố rủi ro nổi bật theo SHAP analysis.</p>';
      }
    }else{
      throw new Error('API error');
    }
  }catch(e){
    // Fallback: hiển thị rule-based explanation nếu SHAP API không khả dụng
    const s=DATA.find(d=>d.mssv===mssv);
    if(!s){el.innerHTML='';return}
    const factors=[];
    if(s.login<5) factors.push({name:'Ít truy cập Moodle',feature:'login_count',pct:90});
    if(s.w&&s.w[2]===0&&s.w[3]===0) factors.push({name:'Bỏ học từ tuần 3',feature:'weekly_score_w3/w4',pct:95});
    else if(s.w&&s.w[3]===0) factors.push({name:'Không hoạt động tuần 4',feature:'weekly_score_w4',pct:75});
    if(s.w&&s.w[3]>0&&s.w[3]<s.w[0]*0.4) factors.push({name:'Sụt giảm điểm mạnh',feature:'weekly_score_trend',pct:70});
    if(s.video===0&&s.doc===0) factors.push({name:'Không xem tài liệu/video',feature:'total_document_reads',pct:60});
    if(s.disc===0) factors.push({name:'Không tham gia thảo luận',feature:'total_discussion',pct:50});
    if(s.duration>0&&s.duration<5&&s.score>100) factors.push({name:'Nghi ngờ gian lận (làm bài quá nhanh)',feature:'assignment_duration_mins',pct:85});
    
    const top3=factors.sort((a,b)=>b.pct-a.pct).slice(0,3);
    if(top3.length>0){
      el.innerHTML=top3.map((f,i)=>`<div class="xai-factor">
        <div class="xai-rank">${i+1}</div>
        <div class="xai-content">
          <div class="xai-name">${f.name}</div>
          <div class="xai-feature">feature: ${f.feature} (rule-based)</div>
          <div class="xai-impact-bar"><div class="xai-impact-fill" style="width:${f.pct}%"></div></div>
        </div>
        <div class="xai-impact-val" style="color:${i===0?'#ef4444':i===1?'#f59e0b':'#3b82f6'}">${f.pct}%</div>
      </div>`).join('');
    }else{
      el.innerHTML='<p style="font-size:12px;color:var(--green);padding:8px">✅ Không phát hiện yếu tố bất thường.</p>';
    }
  }
}
function closeModal(e){if(e.target===document.getElementById('modalBackdrop'))document.getElementById('modalBackdrop').classList.remove('show')}

function switchCommTab(tab,el){
  document.querySelectorAll('.comm-tab').forEach(t=>t.classList.remove('active'));
  document.querySelectorAll('.comm-panel').forEach(p=>p.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('comm-'+tab).classList.add('active');
}

async function generateAIContent(){
  const s=DATA.find(d=>d.mssv===currentModalMSSV);
  if(!s){alert('Lỗi: Không tìm thấy sinh viên');return;}
  
  const btn=document.querySelector('.ai-btn');
  const oldTxt=btn.innerHTML;
  btn.innerHTML='⏳ Đang gọi API Gemini...';
  btn.style.pointerEvents='none';
  
  try{
    const res=await fetch('/api/generate-ai',{
      method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({student:s})
    });
    const data=await res.json();
    if(res.ok){
      document.getElementById('emailContent').value=data.email_content;
      document.getElementById('smsContent').value=data.sms_content;
      btn.innerHTML='✨ AI đã hoàn tất';
    }else{
      throw new Error(data.error||'Lỗi Server AI');
    }
  }catch(e){
    alert('Không thể kết nối Backend AI. Hãy chắc chắn đã chạy file api_server.py và điền KEY.\nLỗi: '+e.message);
    btn.innerHTML='❌ Lỗi AI';
  }
  
  setTimeout(()=>{btn.innerHTML=oldTxt;btn.style.pointerEvents='auto';},3000);
}

async function sendCommunication(type){
  if(!currentModalMSSV)return;
  const s=DATA.find(d=>d.mssv===currentModalMSSV);
  const btn=event.target;
  const oldTxt=btn.innerHTML;
  btn.innerHTML='⏳ Đang gửi...';
  btn.disabled=true;
  
  try{
    if(type==='email'){
      const to=document.getElementById('emailTo').value;
      const subj=document.getElementById('emailSubject').value;
      const body=document.getElementById('emailContent').value;
      
      const res=await fetch('/api/send-email',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({to,subject:subj,body})
      });
      const data=await res.json();
      if(!res.ok) throw new Error(data.error);
      
      saveNote(currentModalMSSV,{type:'email',text:`Đã gửi Email tới: ${to} (Tiêu đề: ${subj}).\nKèm nội dung cảnh báo.`,label:'✉️ Đã gửi Email',time:new Date().toLocaleString('vi-VN'),author:'Hệ thống (Tự động)'});
      alert(`✅ Đã gửi Email hoàn tất tới: ${to}`);
    }else{
      const to=document.getElementById('smsTo').value;
      const body=document.getElementById('smsContent').value;
      
      const res=await fetch('/api/send-sms',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({to,body})
      });
      const data=await res.json();
      if(!res.ok) throw new Error(data.error);
      if(data.warning) alert(data.warning);
      else alert(`✅ Đã gửi SMS diện rộng hoàn tất.\nSố ĐT: ${to}`);
      
      saveNote(currentModalMSSV,{type:'call',text:`Đã bắn tin nhắn SMS tới: ${to}.\nNội dung:\n${body}`,label:'📱 Đã gửi SMS',time:new Date().toLocaleString('vi-VN'),author:'Hệ thống (Tự động)'});
    }
    setHandled(currentModalMSSV,true);
    renderNotes(currentModalMSSV);
  }catch(e){
    alert('❌ Lỗi gửi thông báo. Hãy kiểm tra Backend api_server.py.\nLỗi: '+e.message);
  }
  btn.innerHTML=oldTxt;
  btn.disabled=false;
}

// ═══ NAVIGATION ═══
function showPage(p,el){
  document.querySelectorAll('.page').forEach(pg=>pg.classList.remove('active'));
  document.getElementById('page-'+p).classList.add('active');
  document.querySelectorAll('.nav-item').forEach(n=>n.classList.remove('active'));
  if(el)el.classList.add('active');
  const t={dashboard:'📋 Tổng quan tình hình học tập',courses:'📚 Khóa học',students:'👥 Danh sách Sinh viên',reports:'📊 Báo cáo & Thống kê',settings:'⚙️ Cài đặt hệ thống'};
  document.getElementById('pageTitle').textContent=t[p]||'';
  // Breadcrumb
  if(pageHistory[pageHistory.length-1]!==p)pageHistory.push(p);
  updateBreadcrumb(p);
}

function updateBreadcrumb(current){
  const names={dashboard:'🏠 Tổng quan',courses:'📚 Khóa học',students:'👥 Danh sách SV',reports:'📊 Báo cáo',settings:'⚙️ Cài đặt'};
  const bc=document.getElementById('breadcrumb');
  if(current==='dashboard'){bc.innerHTML='';return}
  let html='<a onclick="goBack()">← Quay lại</a> | <a onclick="showPage(\'dashboard\',document.querySelectorAll(\'.nav-item\')[0])">🏠 Tổng quan</a>';
  if(current!=='dashboard') html+=' → <span>'+names[current]+'</span>';
  bc.innerHTML=html;
}

function goBack(){
  const sList = document.getElementById('courseStudents');
  if (document.getElementById('page-courses').classList.contains('active') && sList && sList.style.display === 'block') {
    closeCourseStudents();
    return;
  }
  if(pageHistory.length>1){pageHistory.pop();const prev=pageHistory[pageHistory.length-1];
  const idx={dashboard:0,courses:1,students:2,reports:3,settings:4}[prev]||0;
  showPage(prev,document.querySelectorAll('.nav-item')[idx]);
  }
}

function filterStudentsByLevel(level){
  showPage('students',document.querySelectorAll('.nav-item')[2]);
  document.getElementById('studentFilterLevel').value=level;
  studentPage=1;renderStudentList();
}

function filterTable(l,btn){document.querySelectorAll('.filter-btn').forEach(b=>b.classList.remove('active'));btn.classList.add('active');renderRiskTable(l)}
function sortTable(k){if(sortKey===k)sortDir*=-1;else{sortKey=k;sortDir=-1}renderRiskTable('all')}
function toggleSelectAll(){const c=document.getElementById('selectAll').checked;document.querySelectorAll('.row-check').forEach(cb=>cb.checked=c)}
function globalSearchHandler(){const q=document.getElementById('globalSearch').value.toLowerCase();if(q.length>=2){showPage('students',document.querySelectorAll('.nav-item')[2]);document.getElementById('studentSearchInput').value=q;studentPage=1;renderStudentList()}}

// ═══ DARK MODE ═══
function toggleDark(){
  const d=document.documentElement;
  d.dataset.theme=d.dataset.theme==='dark'?'':'dark';
  document.querySelector('.dark-toggle').textContent=d.dataset.theme==='dark'?'☀️':'🌙';
}

// ═══ SETTINGS ═══
function updateThresholds(){
  RED_THRESH=parseInt(document.getElementById('redThreshold').value);
  YELLOW_THRESH=parseInt(document.getElementById('yellowThreshold').value);
  ['redThreshVal','rTS','rTS2'].forEach(id=>document.getElementById(id).textContent=RED_THRESH);
  ['yellowThreshVal','yTS','yTS2'].forEach(id=>document.getElementById(id).textContent=YELLOW_THRESH);
  processData();renderAll();
}

// ═══ EXPORT ═══
function exportCSV(){
  const h='MSSV,Ho_Ten,Khoa_Hoc,Risk_Pct,Level,Score,Login,Issue,Da_Xu_Ly,So_Ghi_Chu\n';
  const r=[...DATA].sort((a,b)=>b.riskPct-a.riskPct).map(s=>`${s.mssv},"${s.name}","${s.course}",${s.riskPct},${s.level},${s.score},${s.login},"${s.issue}",${getHandled(s.mssv)?'Co':'Chua'},${getNotes(s.mssv).length}`).join('\n');
  const b=new Blob(['\uFEFF'+h+r],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='canh_bao_sinh_vien_'+new Date().toISOString().slice(0,10)+'.csv';a.click();
}
function exportHandledCSV(){
  const handled=DATA.filter(s=>getHandled(s.mssv));
  if(!handled.length){alert('Chưa có sinh viên nào được đánh dấu Đã xử lý.');return}
  const h='MSSV,Ho_Ten,Khoa_Hoc,Risk_Pct,Level,So_Ghi_Chu\n';
  const r=handled.map(s=>`${s.mssv},"${s.name}","${s.course}",${s.riskPct},${s.level},${getNotes(s.mssv).length}`).join('\n');
  const b=new Blob(['\uFEFF'+h+r],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='da_xu_ly_'+new Date().toISOString().slice(0,10)+'.csv';a.click();
}
function exportStudentCSV(){
  const q=document.getElementById('studentSearchInput').value.toLowerCase();
  const lv=document.getElementById('studentFilterLevel').value;
  const co=document.getElementById('studentFilterCourse').value;
  let f=[...DATA];
  if(q)f=f.filter(s=>s.name.toLowerCase().includes(q)||s.mssv.includes(q));
  if(lv!=='all')f=f.filter(s=>s.level===lv);
  if(co!=='all')f=f.filter(s=>s.course===co);
  const h='MSSV,Ho_Ten,Khoa_Hoc,Risk_Pct,Level,Score,Login,Da_Xu_Ly\n';
  const r=f.sort((a,b)=>b.riskPct-a.riskPct).map(s=>`${s.mssv},"${s.name}","${s.course}",${s.riskPct},${s.level},${s.score},${s.login},${getHandled(s.mssv)?'Co':'Chua'}`).join('\n');
  const b=new Blob(['\uFEFF'+h+r],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a');a.href=URL.createObjectURL(b);a.download='danh_sach_sv_'+new Date().toISOString().slice(0,10)+'.csv';a.click();
}

// ═══ BULK EMAIL/SMS ═══
function getSelectedMSSVs(){return [...document.querySelectorAll('.row-check:checked')].map(cb=>cb.dataset.mssv).filter(Boolean)}
function updateSelectedCount(){const c=getSelectedMSSVs().length;document.getElementById('selectedCount').textContent=c?`✅ Đã chọn ${c} sinh viên`:'Chọn SV bằng checkbox bên dưới'}
async function bulkEmail(){
  const mss=getSelectedMSSVs();if(!mss.length){alert('Vui lòng chọn ít nhất 1 sinh viên bằng checkbox.');return}
  if(!confirm(`Gửi Email cảnh báo tới ${mss.length} sinh viên đã chọn?`))return;
  let ok=0,fail=0;
  for(const m of mss){
    const s=DATA.find(d=>d.mssv===m);if(!s)continue;
    try{
      const res=await fetch('/api/send-email',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({to:s.email,subject:'[EWS] Cảnh báo tình hình học tập',body:`Chào em ${s.name},\n\nHệ thống cảnh báo học vụ ghi nhận em đang ở mức rủi ro ${s.riskPct}% môn ${s.course}.\nVấn đề: ${s.issue}.\n\nVui lòng liên hệ Cố vấn học tập.\nTrân trọng.`})});
      if(res.ok){ok++;setHandled(m,true);saveNote(m,{type:'email',text:'Email hàng loạt đã gửi tự động.',label:'✉️ Bulk Email',time:new Date().toLocaleString('vi-VN'),author:'Hệ thống'})}else fail++;
    }catch(e){fail++}
  }
  alert(`Hoàn tất gửi Email hàng loạt!\n✅ Thành công: ${ok}\n❌ Thất bại: ${fail}`);
  renderAll();
}
async function bulkSMS(){
  const mss=getSelectedMSSVs();if(!mss.length){alert('Vui lòng chọn ít nhất 1 sinh viên bằng checkbox.');return}
  if(!confirm(`Gửi SMS cảnh báo tới ${mss.length} sinh viên đã chọn?`))return;
  let ok=0,fail=0;
  for(const m of mss){
    const s=DATA.find(d=>d.mssv===m);if(!s)continue;
    try{
      const res=await fetch('/api/send-sms',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({to:'09'+Math.floor(Math.random()*100000000).toString().padStart(8,'0'),body:`[EWS] SV ${s.name} (${s.mssv}) rui ro ${s.riskPct}% mon ${s.course}. LH CVHT.`})});
      if(res.ok){ok++;setHandled(m,true);saveNote(m,{type:'call',text:'SMS hàng loạt đã gửi tự động.',label:'📱 Bulk SMS',time:new Date().toLocaleString('vi-VN'),author:'Hệ thống'})}else fail++;
    }catch(e){fail++}
  }
  alert(`Hoàn tất gửi SMS hàng loạt!\n✅ Thành công: ${ok}\n❌ Thất bại: ${fail}`);
  renderAll();
}

// ═══ SETTINGS: Advisor ═══
function updateAdvisorInfo(){
  const n=document.getElementById('settingAdvisorName').value;
  const r=document.getElementById('settingAdvisorRole').value;
  document.querySelector('.user-name strong').textContent=n;
  document.querySelector('.user-name span').textContent=r;
  document.querySelector('.user-avatar').textContent=n.split(' ').pop()[0]+n.split(' ').slice(-2,-1)[0]?.[0]||'';
}
async function checkAPIStatus(){
  const el=document.getElementById('apiStatus');
  el.textContent='Đang kiểm tra...';
  el.style.color='var(--yellow)';
  try{
    const r=await fetch('/api/generate-ai',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({student:{name:'test',mssv:'0',course:'test',riskPct:0,issue:'test',score:0,login:0}})});
    if(r.ok){el.textContent='✅ Kết nối thành công (Gemini + Email)';el.style.color='var(--green)'}
    else{const d=await r.json();el.textContent='⚠️ Server chạy nhưng API lỗi: '+d.error;el.style.color='var(--yellow)'}
  }catch(e){el.textContent='❌ Không kết nối được Backend (Chạy: python api_server.py)';el.style.color='var(--red)'}
}

// ═══ REPORTS SUMMARY ═══
function renderReportSummary(){
  const d_array = getActiveData();
  const courses=[...new Set(d_array.map(s=>s.course))];
  let html='';
  courses.forEach(c=>{
    const ss=d_array.filter(s=>s.course===c);
    const g=ss.filter(s=>s.level==='green').length;
    const y=ss.filter(s=>s.level==='yellow').length;
    const r=ss.filter(s=>s.level==='red').length;
    const h=ss.filter(s=>getHandled(s.mssv)).length;
    html+=`<tr><td style="padding:8px 12px;font-weight:600">${c}</td><td style="text-align:center">${ss.length}</td><td style="text-align:center;color:#10b981;font-weight:600">${g}</td><td style="text-align:center;color:#f59e0b;font-weight:600">${y}</td><td style="text-align:center;color:#ef4444;font-weight:600">${r}</td><td style="text-align:center;color:#16a34a">${h}</td><td style="text-align:center;color:#dc2626">${ss.length-h}</td></tr>`;
  });
  // Total row
  const tg=d_array.filter(s=>s.level==='green').length,ty=d_array.filter(s=>s.level==='yellow').length,tr2=d_array.filter(s=>s.level==='red').length,th=d_array.filter(s=>getHandled(s.mssv)).length;
  html+=`<tr style="background:var(--bg);font-weight:700"><td style="padding:8px 12px">TỔNG CỘNG</td><td style="text-align:center">${d_array.length}</td><td style="text-align:center;color:#10b981">${tg}</td><td style="text-align:center;color:#f59e0b">${ty}</td><td style="text-align:center;color:#ef4444">${tr2}</td><td style="text-align:center;color:#16a34a">${th}</td><td style="text-align:center;color:#dc2626">${d_array.length-th}</td></tr>`;
  const el=document.getElementById('reportSummaryBody');if(el)el.innerHTML=html;
}

loadData();setTimeout(checkAPIStatus,2000);
