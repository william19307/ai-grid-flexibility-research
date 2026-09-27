import fs from 'node:fs/promises';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const root=process.cwd(), out=`${root}/outputs/research/review_package_v1.8`;
const records=JSON.parse(await fs.readFile(`${root}/work/tmp/evidence_workbook_v18.json`,'utf8'));
const wb=Workbook.create();
for (const record of records) {
  const s=wb.worksheets.add(record.name), data=record.rows;
  s.showGridLines=false;
  s.getRangeByIndexes(0,0,data.length,data[0].length).values=data;
  const used=s.getUsedRange();
  used.format.font={name:'Arial',size:10};
  used.format.columnWidth=22;
  used.format.rowHeight=30;
  used.format.verticalAlignment='center';
  const header=s.getRangeByIndexes(0,0,1,data[0].length);
  header.format={fill:'#203B57',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:65};
  s.freezePanes.freezeRows(1);
  if(record.name==='Evidence gates'||record.name==='Provincial inputs'){
    used.format.wrapText=true;
    used.format.rowHeight=85;
    used.format.columnWidth=38;
    s.getRangeByIndexes(0,0,data.length,1).format.columnWidth=27;
  } else {
    s.getRangeByIndexes(1,0,data.length-1,data[0].length).setNumberFormat('0.000');
    s.getRangeByIndexes(0,0,data.length,1).format.columnWidth=52;
    if(record.name==='External power')s.getRangeByIndexes(0,7,data.length,1).format.columnWidth=25;
    for(let col=0;col<data[0].length;col++){
      if(['slack','jobs','gpu_power_limit_w_each','window_samples'].includes(data[0][col]))
        s.getRangeByIndexes(1,col,data.length-1,1).setNumberFormat('0');
    }
    if(record.name==='External power'){
      used.format.wrapText=true;
      used.format.rowHeight=72;
      s.getRangeByIndexes(0,7,data.length,1).format.columnWidth=55;
    }
  }
  s.tables.add(`A1:${String.fromCharCode(64+data[0].length)}${data.length}`,true,record.name.replaceAll(' ','')+'Table');
  const notes={
    'Evidence gates':'Review only. No new field observations or completed provincial held-out results.',
    'Conditional factorials':'Source: revision stage 07 certified_factorials.csv. Conditional GPU model; pct columns use 0–100; slack is hours. Not whole-node measurements.',
    'External power':'Source: MLCommons inference_results_v4.0 commit 343c3d2cb03f2ae02b1023a44e4a45ba4b8422ef; stage 38 corrected extraction. https://github.com/mlcommons/inference_results_v4.0',
    'Provincial inputs':'Source paths refer to the research repository outputs/research folder. Missing parameters remain unadmitted; this register is not a physical input dataset.'
  };
  s.getRangeByIndexes(data.length+1,0,1,1).values=[[notes[record.name]]];
}
wb.recalculate();
for (const record of records){
  const blob=await wb.render({sheetName:record.name,range:`A1:${record.name==='External power'?'G':record.name==='Conditional factorials'?'H':record.name==='Evidence gates'?'E':'D'}${Math.min(record.rows.length,8)}`,scale:1.5,format:'png'});
  await fs.writeFile(`${root}/work/tmp/v18_${record.name.replaceAll(' ','_')}.png`,new Uint8Array(await blob.arrayBuffer()));
  if(record.name==='External power'){
    const detail=await wb.render({sheetName:record.name,range:'H1:U5',scale:1,format:'png'});
    await fs.writeFile(`${root}/work/tmp/v18_power_detail.png`,new Uint8Array(await detail.arrayBuffer()));
  }
}
console.log((await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:10},summary:'Export check'})).ndjson);
const xlsx=await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(`${out}/supplementary_data_1_v1.8_review.xlsx`);
console.log('Exported four sheets:',records.map(r=>`${r.name}: ${r.rows.length-1} rows`).join('; '));
