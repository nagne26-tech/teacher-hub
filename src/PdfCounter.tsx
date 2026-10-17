import React,{useEffect,useRef,useState} from 'react';
import {Link} from 'react-router-dom';
import * as pdfjs from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import {countText} from './pdf-count.mjs';
import './pdf.css';
pdfjs.GlobalWorkerOptions.workerSrc=workerUrl;
type Row={page:number;withSpaces:number;withoutSpaces:number};
export function PdfCounter(){
 const [rows,setRows]=useState<Row[]>([]),[name,setName]=useState(''),[busy,setBusy]=useState(false),[progress,setProgress]=useState(''),[error,setError]=useState('');
 const input=useRef<HTMLInputElement>(null),job=useRef<ReturnType<typeof pdfjs.getDocument>|null>(null),generation=useRef(0);
 function clear(){generation.current++;void job.current?.destroy();job.current=null;setRows([]);setName('');setError('');setProgress('');setBusy(false);if(input.current)input.current.value=''}
 useEffect(()=>()=>{generation.current++;void job.current?.destroy()},[]);
 async function read(file?:File){
  if(!file)return;clear();const run=generation.current;
  if(!file.name.toLowerCase().endsWith('.pdf')){setError('PDF 파일을 선택해주세요.');return}
  if(file.size>100*1024*1024){setError('100MB 이하의 PDF를 선택해주세요.');return}
  setName(file.name);setBusy(true);setProgress('PDF를 읽고 있어요.');
  try{
   const data=new Uint8Array(await file.arrayBuffer());if(run!==generation.current)return;
   const task=pdfjs.getDocument({data,useSystemFonts:true,disableFontFace:true,cMapUrl:`${import.meta.env.BASE_URL}pdf-assets/cmaps/`,cMapPacked:true,standardFontDataUrl:`${import.meta.env.BASE_URL}pdf-assets/standard_fonts/`,wasmUrl:`${import.meta.env.BASE_URL}pdf-assets/wasm/`});job.current=task;
   task.onPassword=()=>{setError('암호로 보호된 PDF입니다. 기기에서 암호를 해제한 뒤 다시 선택해주세요.');void task.destroy()};
   const doc=await task.promise;const next:Row[]=[];
   for(let n=1;n<=doc.numPages;n++){
    if(run!==generation.current)return;setProgress(`${doc.numPages}페이지 중 ${n}페이지 분석 중`);
    const page=await doc.getPage(n);const content=await page.getTextContent();
    const text=content.items.map(item=>'str' in item?item.str+(item.hasEOL?'\n':''):'').join('');
    next.push({page:n,...countText(text)});page.cleanup();
   }
   if(run!==generation.current)return;setRows(next);setProgress('분석이 완료되었습니다.');
  }catch(e){if(run===generation.current)setError(previous=>previous||(e instanceof Error&&e.name==='InvalidPDFException'?'손상되었거나 올바르지 않은 PDF입니다.':'PDF를 읽을 수 없습니다. 파일을 확인하거나 다른 PDF로 시도해주세요.'))}
  finally{if(run===generation.current){setBusy(false);await job.current?.destroy();job.current=null}}
 }
 const total=rows.reduce((a,r)=>({withSpaces:a.withSpaces+r.withSpaces,withoutSpaces:a.withoutSpaces+r.withoutSpaces}),{withSpaces:0,withoutSpaces:0});
 const blank=rows.filter(r=>r.withoutSpaces===0).length;
 return <main className="pdf-page"><Link to="/apps">← 내 앱으로</Link><div className="eyebrow">PRIVATE · ON YOUR DEVICE</div><h1>PDF 글자 수 세기.</h1><p className="pdf-intro">문서는 내 컴퓨터에 그대로.<br/>필요한 숫자만, 간단하게 확인하세요.</p><div className="privacy-badge">▣ PDF와 결과를 서버로 전송하거나 저장하지 않습니다.</div>
 <section className="pdf-drop" onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();void read(e.dataTransfer.files[0])}} aria-label="PDF 파일 선택"><span className="pdf-symbol">PDF</span><h2>PDF를 여기에 놓아주세요</h2><p>또는 컴퓨터에서 파일을 선택하세요 · PDF 1개, 최대 100MB</p><input ref={input} type="file" accept=".pdf,application/pdf" aria-label="PDF 파일" onChange={e=>void read(e.target.files?.[0])}/><p className="muted">다른 파일을 선택하면 이전 결과가 지워집니다.</p></section>
 {(name||busy)&&<div className="pdf-status"><strong>{name}</strong><button onClick={clear}>{busy?'분석 취소':'파일·결과 지우기'}</button></div>}<p role="status" aria-live="polite">{progress}</p>{error&&<p role="alert" className="error">{error}</p>}
 {rows.length>0&&<section aria-label="글자 수 분석 결과"><div className="pdf-metrics"><article><small>공백 포함</small><strong>{total.withSpaces.toLocaleString()}</strong><span>글자</span></article><article><small>공백 제외</small><strong>{total.withoutSpaces.toLocaleString()}</strong><span>글자</span></article><article><small>전체 페이지</small><strong>{rows.length.toLocaleString()}</strong><span>페이지</span></article></div>{blank>0&&<p className="warning">{blank}개 페이지에서 텍스트를 찾지 못했습니다. 스캔·이미지 페이지는 OCR 없이는 셀 수 없으며, 위 합계는 추출 가능한 텍스트만 포함합니다.</p>}<div className="pdf-table"><table><caption>페이지별 글자 수</caption><thead><tr><th>페이지</th><th>공백 포함</th><th>공백 제외</th></tr></thead><tbody>{rows.map(row=><tr key={row.page}><th>{row.page}</th><td>{row.withSpaces.toLocaleString()}</td><td>{row.withoutSpaces.toLocaleString()}</td></tr>)}</tbody></table></div></section>}
 <section className="pdf-explain"><h2>계산 기준과 개인정보</h2><p>한글·영문·숫자·문장부호를 포함하며, 화면상 한 글자(이모지 묶음 포함)를 한 글자로 셉니다. 줄바꿈은 제외하고, 공백 제외 값은 띄어쓰기·탭 등 모든 공백을 제외합니다.</p><p>PDF의 텍스트 저장 방식에 따라 띄어쓰기나 읽기 순서가 달라질 수 있습니다. 머리말·꼬리말·숨겨진 텍스트도 추출되면 포함됩니다. OCR은 제공하지 않습니다.</p><p>파일과 결과는 현재 탭의 메모리에서만 처리합니다. 파일·결과 지우기, 새로고침 또는 화면 이동 시 사라집니다. PDF 분석에 외부 API나 CDN을 사용하지 않습니다.</p></section></main>
}
