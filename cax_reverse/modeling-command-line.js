// Plain text commands are data, never JavaScript or shell input.
function words(text){
 const result=[];let current='',quote=null;
 for(const char of text.trim()){
  if(quote){if(char===quote)quote=null;else current+=char;}
  else if(char==='"'||char==="'")quote=char;
  else if(/\s/.test(char)){if(current){result.push(current);current='';}}
  else current+=char;
 }
 if(quote)throw Error('命令行引号未闭合');
 if(current)result.push(current);
 return result;
}
function value(text){
 if(text==='true')return true;if(text==='false')return false;
 if(/^[-+]?(?:\d+\.?\d*|\.\d+)(?:e[-+]?\d+)?$/i.test(text)){const n=Number(text);if(!Number.isFinite(n))throw Error('数值超出范围');return n;}
 if(text.startsWith('[')||text.startsWith('{')){try{return JSON.parse(text);}catch{throw Error('JSON 参数格式无效');}}
 if(text.includes(';'))return text.split(';').map(part=>value(part));
 if(text.includes(','))return text.split(',').map(part=>value(part));
 return text;
}
export function parseModelingCommand(text){
 const tokens=words(text);if(!tokens.length)throw Error('请输入命令');
 const [verb,...rest]=tokens,positionals=[],named={};
 for(const token of rest){const index=token.indexOf('=');if(index<0){positionals.push(value(token));continue;}
  const key=token.slice(0,index),raw=token.slice(index+1);
  if(!/^[a-zA-Z][a-zA-Z0-9_-]*$/.test(key)||!raw||Object.hasOwn(named,key))throw Error('命令参数名称、值或重复项无效');
  named[key]=value(raw);
 }
 return {verb:verb.toLowerCase(),positionals,named};
}
