// The classic dialogs stay intact. Direct mode mounts the same command form in a
// nonmodal dock, so both interfaces still call the existing geometry handlers.
import {setModelingText,setModelingAttribute} from './modeling-i18n.js';
const MODELING_DIALOGS=['height-dialog','transform-dialog','advanced-dialog','construction-dialog','feature-command-dialog','geometry-report-dialog','parametric-part-dialog','feature-graph-dialog','sketch-dialog','modeling-settings-dialog'];
const KEY='smlib-modeling-interaction-v1';

export function installModelingInteraction(){
 const modeSelect=document.getElementById('interaction-mode');
 const workspace=document.getElementById('direct-workspace');
 const panel=document.getElementById('direct-mouse-panel');
 const content=document.getElementById('direct-panel-content');
 const command=document.getElementById('direct-command-input');
 const feedback=document.getElementById('direct-command-feedback');
 const stack=[];
 let runCommand=null,pickWorldPoint=null,mode='classic',pickTarget=null;
 try{if(localStorage.getItem(KEY)==='direct')mode='direct';}catch{}
 const direct=()=>mode==='direct';
 function message(value,error=false){setModelingText(feedback,value);feedback.dataset.error=String(error);}
 function mounted(dialog){return stack.some(item=>item.dialog===dialog);}
 function restore(item){if(!item)return;for(const child of item.children)item.dialog.append(child);}
 function mount(item){for(const child of item.children)content.append(child);panel.hidden=false;enhance(content);}
 function show(dialog){
  if(mounted(dialog))return;
  const current=stack.at(-1);if(current)restore(current);
  const item={dialog,children:[...dialog.childNodes]};stack.push(item);mount(item);
  document.getElementById('direct-panel-close').focus();
 }
 function close(dialog){
  const index=stack.findIndex(item=>item.dialog===dialog);if(index<0)return false;
  const current=stack.at(-1),wasCurrent=current?.dialog===dialog;if(wasCurrent)restore(current);
  stack.splice(index,1);
  if(wasCurrent){content.replaceChildren();if(stack.length)mount(stack.at(-1));else panel.hidden=true;}
  dialog.dispatchEvent(new Event('close'));
  return true;
 }
 function closeAll(){while(stack.length)stack.at(-1).dialog.close();pickTarget=null;}
 function setMode(value){
  if(value!=='classic'&&value!=='direct')throw Error('未知建模操作方式');
  closeAll();mode=value;modeSelect.value=value;document.body.dataset.interactionMode=value;workspace.hidden=!direct();
  try{localStorage.setItem(KEY,value);}catch{}
  message(direct()?'鼠标操作可在画布和工具栏完成；命令行可独立输入对象编号和全部参数。':'');
  document.dispatchEvent(new CustomEvent('modeling-interaction-change',{detail:{mode:value}}));
 }
 for(const id of MODELING_DIALOGS){
  const dialog=document.getElementById(id);if(!dialog)continue;
  const nativeShow=dialog.showModal.bind(dialog),nativeClose=dialog.close.bind(dialog);
  dialog.showModal=function(){if(direct())show(dialog);else nativeShow();};
  dialog.close=function(value){if(!close(dialog))nativeClose(value);};
 }
 function step(input,direction){
  const current=Number(input.value),raw=Number(input.step),minimum=Number(input.min),maximum=Number(input.max);
  const amount=Number.isFinite(raw)&&raw>0?raw:Number.isFinite(current)&&Math.abs(current)<1?.1:1;
  const value=(Number.isFinite(current)?current:0)+direction*amount;
  input.value=String(Math.min(input.max!==''&&Number.isFinite(maximum)?maximum:Infinity,Math.max(input.min!==''&&Number.isFinite(minimum)?minimum:-Infinity,Number(value.toFixed(9)))));
  input.dispatchEvent(new Event('input',{bubbles:true}));input.dispatchEvent(new Event('change',{bubbles:true}));
 }
 function enhance(root){
  for(const input of root.querySelectorAll('input[type="number"]')){
   if(input.dataset.mouseEnhanced)continue;input.dataset.mouseEnhanced='true';
   for(const [direction,label]of [[-1,'−'],[1,'+']]){const button=document.createElement('button');button.type='button';button.className='mouse-step';button.textContent=label;setModelingAttribute(button,'title',direction<0?'鼠标减小参数':'鼠标增大参数');button.addEventListener('click',()=>step(input,direction));input.after(button);}
  }
  for(const input of root.querySelectorAll('input[data-field-type="vector"],input[data-field-type="uv"],textarea[data-field-type="points"],#profile-points,#sweep-path')){
   if(input.dataset.mousePickEnhanced)continue;input.dataset.mousePickEnhanced='true';
   const button=document.createElement('button');button.type='button';button.className='mouse-pick';setModelingText(button,'画布取点');
   button.addEventListener('click',()=>{pickTarget=input;message('在画布单击取点；Esc 取消取点。');});input.after(button);
   if(input.tagName==='TEXTAREA'){const clear=document.createElement('button');clear.type='button';clear.className='mouse-pick';setModelingText(clear,'清空点');clear.addEventListener('click',()=>{input.value='';input.dispatchEvent(new Event('input',{bubbles:true}));});button.after(clear);}
  }
  for(const input of root.querySelectorAll('input[data-field-type="list"],input[data-field-type="indices"]')){
   if(input.dataset.mouseListEnhanced)continue;input.dataset.mouseListEnhanced='true';
   for(const [label,action]of [['−',-1],['+',1],['追加',2],['删除末项',3]]){const button=document.createElement('button');button.type='button';button.className='mouse-step';setModelingText(button,label);button.addEventListener('click',()=>{const parts=input.value.split(/[,，\s]+/).filter(Boolean).map(Number);if(action===2)parts.push(parts.at(-1)??1);else if(action===3)parts.pop();else if(parts.length)parts[parts.length-1]+=action;input.value=parts.join(', ');input.dispatchEvent(new Event('input',{bubbles:true}));});input.after(button);}
  }
 }
 const canvas=document.querySelector('#viewport canvas');
 canvas.addEventListener('pointerdown',event=>{if(!pickTarget||event.button!==0)return;event.preventDefault();event.stopImmediatePropagation();},true);
 canvas.addEventListener('pointerup',event=>{
  if(!pickTarget||event.button!==0)return;event.preventDefault();event.stopImmediatePropagation();
  const point=pickWorldPoint?.(event);if(!point){message('该视角无法取到工作平面点，请调整视图。',true);return;}
  const input=pickTarget,xy=input.id==='profile-points'||input.dataset.fieldType==='uv',value=(xy?point.slice(0,2):point).map(v=>Number(v.toFixed(3))).join(', ');
  input.value=input.tagName==='TEXTAREA'&&input.value.trim()?input.value.trim()+'\n'+value:value;
  input.dispatchEvent(new Event('input',{bubbles:true}));pickTarget=null;message(`已取点 ${value}`);
 },true);
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&pickTarget){event.preventDefault();event.stopImmediatePropagation();pickTarget=null;message('已取消画布取点');}},true);
 document.getElementById('direct-panel-close').onclick=()=>stack.at(-1)?.dialog.close();
 content.addEventListener('click',event=>{if(stack.at(-1)?.dialog.id==='sketch-dialog'&&event.target.closest('button[aria-label="关闭"]')){event.preventDefault();stack.at(-1).dialog.close();}});
 modeSelect.onchange=()=>setMode(modeSelect.value);
 document.getElementById('direct-command-form').onsubmit=async event=>{
  event.preventDefault();const text=command.value.trim();if(!text)return;
  try{if(!runCommand)throw Error('命令行尚未就绪');const result=await runCommand(text);message(result||'命令已执行');}catch(error){message(error.message,true);}
 };
 setMode(mode);
 return {direct,setMode,message,command,feedback,closeAll,setCommandHandler:handler=>{runCommand=handler;},setPickWorldPoint:handler=>{pickWorldPoint=handler;}};
}
