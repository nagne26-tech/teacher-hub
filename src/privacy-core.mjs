export const labels={rrn:'주민등록번호',phone:'전화번호',email:'이메일',student:'학번',name:'이름',custom:'직접 지정'};
export function detect(text, custom=''){
 const hits=[];const add=(type,start,end)=>{if(end>start)hits.push({type,start,end,value:text.slice(start,end)})};
 for(const [type,re] of [['rrn',/(?<!\d)\d{6}[\s-]?[1-8]\d{6}(?!\d)/g],['phone',/(?<!\d)(?:01[016789][\s.-]?\d{3,4}[\s.-]?\d{4}|0[2-6]\d?[\s.-]?\d{3,4}[\s.-]?\d{4})(?!\d)/g],['email',/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi]])for(const m of text.matchAll(re))add(type,m.index,m.index+m[0].length);
 for(const [type,re] of [['name',/(?:성명|이름|학생명|보호자명)\s*[:：=]?\s*([가-힣]{2,5})(?![가-힣])/g],['student',/(?:학번|학생번호|학적번호)\s*[:：=]?\s*(\d[\d -]{1,18}\d)/g]])for(const m of text.matchAll(re)){const start=m.index+m[0].lastIndexOf(m[1]);add(type,start,start+m[1].length)}
 for(const term of custom.split(/[\n,]/).map(s=>s.trim()).filter(Boolean)){let pos=0;while((pos=text.indexOf(term,pos))!==-1){add('custom',pos,pos+term.length);pos+=term.length}}
 return hits.sort((a,b)=>a.start-b.start||b.end-a.end).filter((h,i,a)=>!a.slice(0,i).some(p=>p.start===h.start&&p.end===h.end));
}
export function redact(text,hits){let out=text;for(const h of [...hits].sort((a,b)=>b.start-a.start)){out=out.slice(0,h.start)+'[삭제]'+out.slice(h.end)}return out}
export function columnType(value){const s=String(value??'').replace(/\s/g,'');if(/^(성명|이름|학생명|보호자명|name)$/i.test(s))return 'name';if(/^(학번|학생번호|학적번호|student_?id)$/i.test(s))return 'student';return null}
export function mergedRanges(hits){const out=[];for(const h of [...hits].sort((a,b)=>a.start-b.start)){const p=out.at(-1);if(p&&h.start<=p.end)p.end=Math.max(p.end,h.end);else out.push({start:h.start,end:h.end})}return out}
