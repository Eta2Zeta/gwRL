import fs from 'node:fs';
import vm from 'node:vm';
for(const path of process.argv.slice(2)) {
 const html=fs.readFileSync(path,'utf8'), script=html.match(/<script>([\s\S]*)<\/script>/)[1];
 const elements=new Map();
 const element=()=>({value:'0',textContent:'',children:[],append(x){this.children.push(x)},replaceChildren(x){this.children=[x]},insertRow(){const row=element();this.children.push(row);return row},insertCell(){const cell=element();this.children.push(cell);return cell}});
 const document={querySelector(selector){if(!elements.has(selector))elements.set(selector,element());return elements.get(selector)},createElement:element};
 const context=vm.createContext({document,structuredClone});
 vm.runInContext(script,context,{timeout:10000});
 const slider=elements.get('#position');
 for(const i of [0,1,Math.floor(slider.max/2),+slider.max]){slider.value=String(i);slider.oninput();if(elements.get('#count').textContent!==`${i} / ${slider.max}`)throw Error('Slider count differs');}
 elements.get('#prev').onclick();if(+slider.value!==+slider.max-1)throw Error('Previous button failed');elements.get('#next').onclick();
 const json=JSON.parse(html.slice(html.indexOf('const report=')+'const report='.length,html.indexOf(';const steps=')));
 const rows=elements.get('#board').children[0].children.length-1;
 if(rows!==Object.keys(json.final_snapshot.units).length)throw Error('Final unit board differs');
 console.log(`${path}: controls and final ${rows}-unit board passed`);
}
