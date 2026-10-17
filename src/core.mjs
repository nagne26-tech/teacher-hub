export const KEY='teacher-hub:data:v1';
export const empty=()=>({schemaVersion:1,externalApps:[],favoriteIds:[]});
export function validURL(value){try{return typeof value==='string'&&['http:','https:'].includes(new URL(value).protocol)}catch{return false}}
export function validate(data){
 if(!data||data.schemaVersion!==1||!Array.isArray(data.externalApps)||data.externalApps.length>200||!Array.isArray(data.favoriteIds))throw Error('지원하는 버전 1의 앱 목록 JSON이 필요합니다.');
 const ids=new Set(['class-timer','pdf-counter','diary','privacy-guard']);
 for(const a of data.externalApps){if(!a||typeof a.id!=='string'||!a.id||ids.has(a.id))throw Error('앱 ID가 중복되거나 올바르지 않습니다.');ids.add(a.id);
 for(const [key,max,required] of [['name',40,true],['description',200,false],['category',20,true]]){if(typeof a[key]!=='string'||a[key].length>max||(required&&!a[key].trim()))throw Error('앱 이름·설명·분류를 확인해주세요.');}
 if(!['idea','developing','ready'].includes(a.status)||(a.url!==null&&!validURL(a.url))||(a.status==='ready'&&!a.url)||![a.createdAt,a.updatedAt].every(x=>typeof x==='string'&&Number.isFinite(Date.parse(x))))throw Error('앱 상태·URL·날짜가 올바르지 않습니다.');
 }
 if(!data.favoriteIds.every(id=>typeof id==='string'&&ids.has(id))||new Set(data.favoriteIds).size!==data.favoriteIds.length)throw Error('즐겨찾기 목록이 올바르지 않습니다.');
 return {schemaVersion:1,externalApps:data.externalApps.map(a=>({id:a.id,name:a.name,description:a.description,category:a.category,url:a.url,status:a.status,createdAt:a.createdAt,updatedAt:a.updatedAt})),favoriteIds:[...data.favoriteIds]};
}
export function remaining(end,now=Date.now()){return Math.max(0,end-now)}
export function duration(minutes,seconds){const m=Number(minutes),s=Number(seconds);return Number.isInteger(m)&&Number.isInteger(s)&&m>=0&&m<=99&&s>=0&&s<=59&&(m*60+s)>0?(m*60+s)*1000:null}
export function clock(ms){const seconds=Math.ceil(ms/1000);return `${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}`}
